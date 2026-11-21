
"""Flask application for the Plate Planner web interface."""
from functools import wraps
from pathlib import Path
 
from flask import Flask, jsonify, render_template, request
 
from data.DataStorageManager import DataStorageManager, StorageError
from plateplanner.management.recipe.RecipeService import (
    InvalidRecipeError, RecipeInUseError, RecipeNotFoundError,
    RecipeService, ServiceError,
)
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
 
# HTTP status for each error RecipeService raises (InvalidRecipeError is 400).
RECIPE_ERROR_STATUS = {
    RecipeNotFoundError: 404,
    RecipeInUseError: 409,
}
 
 
def recipe_route(storage_error_message):
    """Give a recipe route a RecipeService and report errors as JSON.
 
    The decorated route receives a RecipeService as its first argument. The
    database is opened for the request and closed afterwards. An error that
    RecipeService raises is sent with its own message; a storage failure is
    logged and sent as storage_error_message.
    """
    def decorator(route):
        @wraps(route)
        def wrapper(*args, **kwargs):
            try:
                db = DataStorageManager(str(DATABASE_PATH))
                try:
                    return route(RecipeService(db), *args, **kwargs)
                finally:
                    db.close()
            except ServiceError as error:
                status = RECIPE_ERROR_STATUS.get(type(error), 400)
                return jsonify({"error": str(error)}), status
            except StorageError:
                app.logger.exception(storage_error_message)
                return jsonify({"error": storage_error_message}), 500
        return wrapper
    return decorator
 
 
def check_recipe_id(recipe_id):
    """Reject IDs that cannot belong to a saved recipe."""
    if recipe_id < 1:
        raise InvalidRecipeError("Invalid recipe ID.")
 
 
@app.route("/api/recipes", methods=["GET"])
@recipe_route("Unable to retrieve recipes.")
def get_recipes(service):
    """Retrieve all saved recipes."""
    return jsonify(service.get_all()), 200
 
 
@app.route("/api/recipes", methods=["POST"])
@recipe_route("Unable to save recipe.")
def save_recipe(service):
    """Validate and save a recipe."""
    if not request.is_json:
        raise InvalidRecipeError("Recipe data must be sent as JSON.")
 
    recipe = service.create(request.get_json(silent=True))
    return jsonify({
        "message": "Recipe saved successfully.",
        "recipe": recipe
    }), 201
 
 
@app.route("/api/recipes/<int:recipe_id>", methods=["PUT"])
@recipe_route("Unable to change recipe.")
def update_recipe(service, recipe_id):
    """Update a saved recipe."""
    check_recipe_id(recipe_id)
    recipe = service.update(recipe_id, request.get_json(silent=True))
    return jsonify({"message": "Recipe updated.", "recipe": recipe})
 
 
@app.route("/api/recipes/<int:recipe_id>", methods=["DELETE"])
@recipe_route("Unable to change recipe.")
def delete_recipe(service, recipe_id):
    """Delete a saved recipe."""
    check_recipe_id(recipe_id)
    service.delete(recipe_id)
    return jsonify({"message": "Recipe deleted."})
 
 
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