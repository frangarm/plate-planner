

from datetime import datetime, timedelta
from copy import deepcopy
import math


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

    # Contract M1: Retrieve a Weekly Meal Plan
    def get_meal_plan(self, plan_id: int) -> dict | None:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return None

        return deepcopy(self.meal_plans[plan_id])

    # Contract M1: Retrieve All Weekly Meal Plans
    def get_all_meal_plans(self) -> list:

        return deepcopy(list(self.meal_plans.values()))

    # Contract M1: Delete a Weekly Meal Plan
    def delete_meal_plan(self, plan_id: int) -> bool:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return False

        # Delete the meal plan
        del self.meal_plans[plan_id]

        return True

    # Contract M1: Validate Selected Recipes and Servings
    def validate_meal(self, meal_data: dict) -> bool:

        if not isinstance(meal_data, dict):
            return False

        required_fields = [
            "date",
            "mealSlot",
            "recipeId",
            "servings"
        ]

        # Check required fields
        for field in required_fields:
            if field not in meal_data:
                return False

        # Check serving amount
        servings = meal_data["servings"]

        if (not isinstance(servings, (int, float))
                or isinstance(servings, bool)
                or not math.isfinite(servings)
                or servings <= 0):
            return False

        # Check meal slot
        valid_slots = [
            "breakfast",
            "lunch",
            "dinner",
            "snack"
        ]

        if meal_data["mealSlot"] not in valid_slots:
            return False

        # Check date
        try:
            datetime.strptime(meal_data["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            return False

        # Check that the recipe ID is valid
        recipe_id = meal_data["recipeId"]

        if (not isinstance(recipe_id, int)
                or isinstance(recipe_id, bool)
                or recipe_id <= 0):
            return False

        # Check that the recipe manager exists
        if self.recipe_manager is None:
            return False

        # Check that the recipe exists
        if self.recipe_manager.get_recipe(recipe_id) is None:
            return False

        return True

    # Contract M1: Validate Meal Date
    def validate_meal_date(
        self, plan_id: int, meal_date: str
    ) -> bool:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return False

        # Check that the meal date is valid
        try:
            week_start = datetime.strptime(
                self.meal_plans[plan_id]["weekStart"],
                "%Y-%m-%d"
            )

            date = datetime.strptime(
                meal_date,
                "%Y-%m-%d"
            )

        except (ValueError, TypeError):
            return False

        # Calculate the end of the week
        week_end = week_start + timedelta(days=7)

        # Check that the meal belongs to the selected week
        return week_start <= date < week_end

    # Contract M1: Add a Meal to a Weekly Meal Plan
    def add_meal(
        self, plan_id: int, meal_data: dict
    ) -> bool:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return False

        # Validate the meal information
        if not self.validate_meal(meal_data):
            return False

        # Check that the meal belongs to the selected week
        if not self.validate_meal_date(
            plan_id, meal_data["date"]
        ):
            return False

        # Convert recipeId to recipe_id for database compatibility
        meal = {
            "date": meal_data["date"],
            "mealSlot": meal_data["mealSlot"],
            "recipe_id": meal_data["recipeId"],
            "servings": meal_data["servings"]
        }

        # Add the meal to the weekly plan
        self.meal_plans[plan_id]["meals"].append(meal)

        return True

    # Contract M1: Remove a Meal From a Weekly Meal Plan
    def remove_meal(
        self, plan_id: int, meal_index: int
    ) -> bool:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return False

        meals = self.meal_plans[plan_id]["meals"]

        # Check that the meal index is valid
        if (not isinstance(meal_index, int)
                or isinstance(meal_index, bool)
                or meal_index < 0
                or meal_index >= len(meals)):
            return False

        # Remove the selected meal
        meals.pop(meal_index)

        return True

    # Contract M1: Update a Meal in a Weekly Meal Plan
    def update_meal(
        self,
        plan_id: int,
        meal_index: int,
        meal_data: dict
    ) -> bool:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return False

        meals = self.meal_plans[plan_id]["meals"]

        # Check that the meal index is valid
        if (not isinstance(meal_index, int)
                or isinstance(meal_index, bool)
                or meal_index < 0
                or meal_index >= len(meals)):
            return False

        # Validate the updated meal information
        if not self.validate_meal(meal_data):
            return False

        # Check that the new date belongs to the selected week
        if not self.validate_meal_date(
            plan_id, meal_data["date"]
        ):
            return False

        # Convert recipeId to recipe_id
        updated_meal = {
            "date": meal_data["date"],
            "mealSlot": meal_data["mealSlot"],
            "recipe_id": meal_data["recipeId"],
            "servings": meal_data["servings"]
        }

        # Update the selected meal
        meals[meal_index] = updated_meal

        return True

    # Contract M1: Retrieve Meals for a Specific Date
    def get_meals_by_date(
        self, plan_id: int, date: str
    ) -> list:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return []

        # Check that the date is valid
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except (ValueError, TypeError):
            return []

        # Retrieve meals scheduled for the selected date
        meals = self.meal_plans[plan_id]["meals"]

        matching_meals = [
            meal for meal in meals
            if meal["date"] == date
        ]

        return deepcopy(matching_meals)

    # Contract M1: Update a Weekly Meal Plan
    def update_meal_plan(
        self, plan_id: int, week_start: str
    ) -> bool:

        # Check if the meal plan exists
        if plan_id not in self.meal_plans:
            return False

        # Check that the new starting date is valid
        try:
            start_date = datetime.strptime(
                week_start, "%Y-%m-%d"
            )
        except (ValueError, TypeError):
            return False

        # Calculate the end of the new week
        week_end = start_date + timedelta(days=7)

        # Check that existing meals fit within the new week
        meals = self.meal_plans[plan_id]["meals"]

        for meal in meals:
            meal_date = datetime.strptime(
                meal["date"], "%Y-%m-%d"
            )

            if not start_date <= meal_date < week_end:
                return False

        # Update the weekly meal plan
        self.meal_plans[plan_id]["weekStart"] = week_start

        return True
