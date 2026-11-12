
"""Flask application for the Plate Planner web interface."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from data.DataStorageManager import DataStorageManager, StorageError
from plateplanner.management.recipe.RecipeManager import RecipeManager
from plateplanner.ui.grocery_api import grocery_api
from plateplanner.ui.meal_api import RecipeLookup, meal_api
from plateplanner.meal.nutrition.NutritionAnalyzer import (
    NutritionAnalyzer, PERIOD_DAILY, VALID_PERIODS,
)


app = Flask(__name__)
app.register_blueprint(grocery_api)
app.register_blueprint(meal_api)

# Local SQLite database used for development and testing.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "plateplanner_demo.db"

recipe_manager = RecipeManager()


# -------------------------
# Page Routes
# -------------------------

@app.route("/")
def home():
    """Display the Plate Planner dashboard."""
    return render_template("index.html")


@app.route("/recipes")
def recipes():
    """Display the recipe management page."""
    return render_template("recipes.html")


@app.route("/meal-planner")
def meal_planner():
    """Display the weekly meal planning page."""
    return render_template("meal-planner.html")


@app.route("/grocery-list")
def grocery_list():
    """Display the grocery list page."""
    return render_template("grocery-list.html")


@app.route("/nutrition")
def nutrition():
    """Display the nutrition analysis page."""
    return render_template("nutrition.html")


class NutritionLookup(RecipeLookup):
    def get_meal_plan(self, plan_id):
        return self.database.get_record("meal_plan", plan_id)


@app.get("/api/meal-plans/<int:plan_id>/nutrition")
def get_nutrition(plan_id):
    """Calculate nutrition from a saved weekly plan."""
    period = request.args.get("period", "weekly")
    if plan_id < 1 or period not in VALID_PERIODS:
        return jsonify({"error": "Select a valid plan and analysis period."}), 400

    try:
        db = DataStorageManager(str(DATABASE_PATH))
        try:
            lookup = NutritionLookup(db)
            if lookup.get_meal_plan(plan_id) is None:
                return jsonify({"error": "Meal plan not found."}), 404
            analyzer = NutritionAnalyzer(lookup, lookup)
            result = analyzer.calculate_nutrition(plan_id, period)
            daily_targets = {"calories": 2000, "protein": 50, "carbohydrates": 250, "fat": 70}
            if period == PERIOD_DAILY:
                groups = result["totals"]
                targets = daily_targets
            else:
                groups = {"Weekly total": result["totals"]}
                targets = {nutrient: value * 7 for nutrient, value in daily_targets.items()}

            result["targets"] = targets
            result["comparisons"] = {}
            if not result["incomplete"]:
                for label, totals in groups.items():
                    available_targets = {
                        nutrient: target for nutrient, target in targets.items()
                        if nutrient in totals
                    }
                    result["comparisons"][label] = analyzer.analyze_nutrition(
                        totals, available_targets
                    )
            return jsonify(result)
        finally:
            db.close()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except StorageError:
        app.logger.exception("Unable to calculate nutrition")
        return jsonify({"error": "Unable to calculate nutrition."}), 500


# -------------------------
# Recipe API
# -------------------------

@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """Retrieve all recipes stored in the SQLite database."""
    try:
        db = DataStorageManager(str(DATABASE_PATH))

        try:
            saved_recipes = db.get_all_records("recipe")
        finally:
            db.close()

        return jsonify(saved_recipes), 200

    except StorageError:
        app.logger.exception("Unable to retrieve recipes")
        return jsonify({
            "error": "Unable to retrieve recipes."
        }), 500


@app.route("/api/recipes", methods=["POST"])
def save_recipe():
    """Validate and save a recipe to the SQLite database."""
    if not request.is_json:
        return jsonify({
            "error": "Recipe data must be sent as JSON."
        }), 400

    recipe_data = request.get_json(silent=True)

    # Use the existing RecipeManager for validation.
    if not recipe_manager.validate_recipe(recipe_data):
        return jsonify({
            "error": "Invalid recipe information."
        }), 400

    try:
        db = DataStorageManager(str(DATABASE_PATH))

        try:
            recipe_id = db.save_record("recipe", recipe_data)

            if recipe_id is None:
                return jsonify({
                    "error": "Recipe could not be saved."
                }), 400

            saved_recipe = db.get_record("recipe", recipe_id)
        finally:
            db.close()

        return jsonify({
            "message": "Recipe saved successfully.",
            "recipe": saved_recipe
        }), 201

    except StorageError:
        app.logger.exception("Unable to save recipe")
        return jsonify({
            "error": "Unable to save recipe."
        }), 500


@app.route("/api/recipes/<int:recipe_id>", methods=["PUT", "DELETE"])
def change_recipe(recipe_id):
    """Update or delete a saved recipe."""
    if recipe_id < 1:
        return jsonify({"error": "Invalid recipe ID."}), 400

    if request.method == "PUT":
        recipe_data = request.get_json(silent=True)
        if not recipe_manager.validate_recipe(recipe_data):
            return jsonify({"error": "Invalid recipe information."}), 400

    try:
        db = DataStorageManager(str(DATABASE_PATH))
        try:
            existing = db.get_record("recipe", recipe_id)
            if existing is None:
                return jsonify({"error": "Recipe not found."}), 404

            if request.method == "DELETE":
                if db.delete_record("recipe", recipe_id):
                    return jsonify({"message": "Recipe deleted."})
                if db.get_record("recipe", recipe_id) is None:
                    return jsonify({"error": "Recipe not found."}), 404
                return jsonify({"error": "This recipe is used in a saved meal plan."}), 409

            # Preserve stored fields that the recipe form does not edit.
            existing.update(recipe_data)
            existing.pop("record_id", None)
            if not db.update_record("recipe", recipe_id, existing):
                return jsonify({"error": "Recipe not found."}), 404
            return jsonify({
                "message": "Recipe updated.",
                "recipe": db.get_record("recipe", recipe_id),
            })
        finally:
            db.close()
    except StorageError:
        app.logger.exception("Unable to change recipe")
        return jsonify({"error": "Unable to change recipe."}), 500


# -------------------------
# Connection Test
# -------------------------

@app.route("/api/test")
def test_connection():
    """Test communication between the frontend and backend."""
    return jsonify({
        "message": "Successfully connected to backend"
    })


if __name__ == "__main__":
    app.run(debug=True)
