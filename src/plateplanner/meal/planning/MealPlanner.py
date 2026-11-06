
from datetime import datetime


class MealPlanner:

    def __init__(self, recipe_manager=None):
        self.recipe_manager = recipe_manager
        self.meal_plans = {}
        self.next_plan_id = 1

    # Contract M1: Maintain Weekly Meal Plans
    def create_meal_plan(self, week_start: str) -> int | None:

        # Check that the date is valid
        try:
            datetime.strptime(week_start, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

        # Assign an ID to the new meal plan
        plan_id = self.next_plan_id
        self.next_plan_id += 1

        # Create an empty weekly meal plan
        self.meal_plans[plan_id] = {
            "planId": plan_id,
            "weekStart": week_start,
            "meals": []
        }

        return plan_id

    # Contract M1: Validate selected recipes and servings
    def validate_meal(self, meal_data: dict) -> bool:

        if not isinstance(meal_data, dict):
            return False

        required_fields = ["date", "mealSlot", "recipeId", "servings"]

        # Check required fields
        for field in required_fields:
            if field not in meal_data:
                return False

        # Check serving amount
        servings = meal_data["servings"]

        if (not isinstance(servings, (int, float))
                or isinstance(servings, bool)
                or not 0 < servings < float("inf")):
            return False

        # Check meal slot
        valid_slots = ["breakfast", "lunch", "dinner", "snack"]

        if meal_data["mealSlot"] not in valid_slots:
            return False

        # Check date
        try:
            datetime.strptime(meal_data["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            return False

        # Check that the recipe exists
        recipe_id = meal_data["recipeId"]

        if not isinstance(recipe_id, int) or isinstance(recipe_id, bool) or recipe_id <= 0:
            return False

        if self.recipe_manager is None:
            return False

        if self.recipe_manager.get_recipe(recipe_id) is None:
            return False

        return True
