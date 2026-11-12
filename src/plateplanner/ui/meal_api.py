
"""Flask API for Plate Planner meal planning."""

from datetime import date, timedelta
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from data.DataStorageManager import DataStorageManager, StorageError
from plateplanner.meal.planning.MealPlanner import MealPlanner


meal_api = Blueprint("meal_api", __name__)

# Use the same SQLite database as Recipe Management.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "plateplanner_demo.db"


class RecipeLookup:
    """Allow MealPlanner to retrieve recipes from SQLite."""

    def __init__(self, database):
        """Store the database connection."""
        self.database = database

    def get_recipe(self, recipe_id):
        """Find a saved recipe using its ID."""
        return self.database.get_record("recipe", recipe_id)


def open_database():
    """Open the shared SQLite database."""
    return DataStorageManager(str(DATABASE_PATH))


@meal_api.route("/api/meal-plans", methods=["GET"])
def get_meal_plans():
    """Retrieve all saved meal plans."""
    try:
        db = open_database()

        try:
            plans = db.get_all_records("meal_plan")
            return jsonify(plans), 200
        finally:
            db.close()

    except StorageError:
        current_app.logger.exception("Unable to load meal plans")
        return jsonify({
            "error": "Unable to retrieve meal plans."
        }), 500


@meal_api.route("/api/meal-plans", methods=["POST"])
def create_meal_plan():
    """Create and save a weekly meal plan."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid meal plan information."
        }), 400

    week_start = data.get("weekStart")

    # Use the existing MealPlanner class for validation.
    planner = MealPlanner()

    if planner.create_meal_plan(week_start) is None:
        return jsonify({
            "error": "Enter a valid starting date."
        }), 400

    plan = {
        "weekStart": week_start,
        "meals": []
    }

    try:
        db = open_database()

        try:
            plan_id = db.save_record("meal_plan", plan)

            if plan_id is None:
                return jsonify({
                    "error": "Could not save the meal plan."
                }), 400

            saved_plan = db.get_record("meal_plan", plan_id)
            return jsonify(saved_plan), 201

        finally:
            db.close()

    except StorageError:
        current_app.logger.exception("Unable to create meal plan")
        return jsonify({
            "error": "Unable to save meal plan."
        }), 500


@meal_api.route("/api/meal-plans/<int:plan_id>", methods=["GET"])
def get_meal_plan(plan_id):
    """Retrieve one saved meal plan."""
    if plan_id < 1:
        return jsonify({"error": "Invalid plan ID."}), 400

    try:
        db = open_database()

        try:
            plan = db.get_record("meal_plan", plan_id)
        finally:
            db.close()

        if plan is None:
            return jsonify({
                "error": "Meal plan not found."
            }), 404

        return jsonify(plan), 200

    except StorageError:
        current_app.logger.exception("Unable to retrieve meal plan")
        return jsonify({
            "error": "Unable to retrieve meal plan."
        }), 500


@meal_api.route("/api/meal-plans/<int:plan_id>/meals", methods=["POST"])
@meal_api.route(
    "/api/meal-plans/<int:plan_id>/meals/<int:meal_index>",
    methods=["PUT", "DELETE"],
)
def change_meal(plan_id, meal_index=None):
    """Add, edit or remove a meal in a saved weekly plan."""
    if plan_id < 1:
        return jsonify({"error": "Invalid plan ID."}), 400

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid meal information."}), 400

    try:
        db = open_database()
        try:
            with db.write_transaction():
                plan = db.get_record("meal_plan", plan_id)
                if plan is None:
                    return jsonify({"error": "Meal plan not found."}), 404

                meals = plan.get("meals", [])
                if meal_index is not None and (
                    meal_index >= len(meals)
                    or meals[meal_index] != payload.get("original")
                ):
                    return jsonify({
                        "error": "This meal changed. Refresh the plan and try again."
                    }), 409

                if request.method == "DELETE":
                    del meals[meal_index]
                else:
                    meal_data = payload if meal_index is None else payload.get("meal")
                    planner = MealPlanner(recipe_manager=RecipeLookup(db))
                    if not planner.validate_meal(meal_data):
                        return jsonify({"error": "Invalid meal or recipe information."}), 400

                    start = date.fromisoformat(plan["weekStart"])
                    meal_date = date.fromisoformat(meal_data["date"])
                    if not start <= meal_date <= start + timedelta(days=6):
                        return jsonify({"error": "Meal must be within the selected week."}), 400

                    meal = {
                        "date": meal_data["date"],
                        "mealSlot": meal_data["mealSlot"],
                        "recipe_id": meal_data["recipeId"],
                        "servings": meal_data["servings"],
                    }
                    if meal_index is None:
                        meals.append(meal)
                    else:
                        meals[meal_index] = {**meals[meal_index], **meal}

                plan["meals"] = meals
                del plan["record_id"]
                if not db.update_record("meal_plan", plan_id, plan):
                    return jsonify({"error": "Could not save meal changes."}), 400
                return jsonify({**plan, "record_id": plan_id}), 200
        finally:
            db.close()
    except (StorageError, ValueError, TypeError):
        current_app.logger.exception("Unable to save meal changes")
        return jsonify({"error": "Unable to save meal changes."}), 500
