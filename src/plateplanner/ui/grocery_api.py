
"""Flask API connecting grocery lists to SQLite storage."""

from math import isfinite
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from data.DataStorageManager import DataStorageManager, StorageError
from plateplanner.management.grocery.GroceryListManager import GroceryListManager


grocery_api = Blueprint("grocery_api", __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "plateplanner_demo.db"


def open_database():
    """Open the development SQLite database."""
    return DataStorageManager(str(DATABASE_PATH))


def find_list(db, plan_id):
    """Find the saved grocery list belonging to a meal plan."""
    for grocery_list in db.get_all_records("grocery_list"):
        if grocery_list.get("plan_id") == plan_id:
            return grocery_list
    return None


def valid_quantity(value):
    """Check that a quantity is a positive finite number."""
    return (
            type(value) in (int, float)
            and isfinite(value)
            and value > 0
    )


def validate_items(items):
    """Validate and normalize grocery items before saving."""
    if not isinstance(items, list):
        return None

    cleaned = []

    for item in items:
        if not isinstance(item, dict):
            return None

        name = item.get("name")
        unit = item.get("unit")
        quantity = item.get("quantity")
        purchased = item.get("purchased", False)

        if not isinstance(name, str) or not name.strip():
            return None

        if not isinstance(unit, str) or not unit.strip():
            return None

        if not valid_quantity(quantity):
            return None

        if not isinstance(purchased, bool):
            return None

        cleaned.append({
            "name": name.strip(),
            "quantity": quantity,
            "unit": unit.strip(),
            "purchased": purchased
        })

    return cleaned


@grocery_api.route("/api/grocery-lists", methods=["GET"])
def get_grocery_lists():
    """Return grocery lists saved in SQLite."""
    try:
        db = open_database()
        try:
            lists = db.get_all_records("grocery_list")
            return jsonify(lists), 200
        finally:
            db.close()

    except StorageError:
        current_app.logger.exception("Unable to load grocery lists")
        return jsonify({"error": "Unable to load grocery lists."}), 500


@grocery_api.route("/api/grocery-lists", methods=["POST"])
def generate_grocery_list():
    """Generate a grocery list from a saved meal plan."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request."}), 400

    plan_id = data.get("planId")

    if type(plan_id) is not int or plan_id < 1:
        return jsonify({"error": "Select a valid meal plan."}), 400

    try:
        db = open_database()

        try:
            plan = db.get_record("meal_plan", plan_id)

            if plan is None:
                return jsonify({"error": "Meal plan not found."}), 404

            if not plan.get("meals"):
                return jsonify({
                    "error": "Add meals before generating a grocery list."
                }), 400

            # Keep an existing list so saved edits are not lost.
            existing = find_list(db, plan_id)

            if existing is not None:
                return jsonify(existing), 200

            # Use the team's GroceryListManager.
            manager = GroceryListManager(
                get_meal_plan=lambda pid: db.get_record("meal_plan", pid),
                get_recipe=lambda rid: db.get_record("recipe", rid)
            )

            try:
                ingredients = manager.gather_ingredients(plan_id)
                combined = manager.combine_ingredients(ingredients)
            except (ValueError, TypeError, KeyError, ZeroDivisionError):
                current_app.logger.exception("Grocery generation failed")
                return jsonify({
                    "error": "Could not generate ingredients from this plan."
                }), 400

            items = [
                {
                    **ingredient,
                    "purchased": False
                }
                for ingredient in combined
            ]

            saved_data = {
                "plan_id": plan_id,
                "items": items
            }

            list_id = db.save_record("grocery_list", saved_data)
            saved_list = db.get_record("grocery_list", list_id)

            return jsonify(saved_list), 201

        finally:
            db.close()

    except StorageError:
        current_app.logger.exception("Unable to generate grocery list")
        return jsonify({"error": "Unable to save grocery list."}), 500


@grocery_api.route(
    "/api/grocery-lists/<int:list_id>",
    methods=["PUT"]
)
def update_grocery_list(list_id):
    """Save changes to quantities, items, and purchased status."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request."}), 400

    items = validate_items(data.get("items"))

    if items is None:
        return jsonify({"error": "Invalid grocery items."}), 400

    try:
        db = open_database()

        try:
            existing = db.get_record("grocery_list", list_id)

            if existing is None:
                return jsonify({"error": "Grocery list not found."}), 404

            updated_data = {
                "plan_id": existing["plan_id"],
                "items": items
            }

            if not db.update_record(
                    "grocery_list", list_id, updated_data
            ):
                return jsonify({
                    "error": "Unable to update grocery list."
                }), 400

            updated = db.get_record("grocery_list", list_id)
            return jsonify(updated), 200

        finally:
            db.close()

    except StorageError:
        current_app.logger.exception("Unable to update grocery list")
        return jsonify({"error": "Unable to save changes."}), 500
