from plateplanner.meal.nutrition.planning import MealPlanner
from plateplanner.management.recipe import RecipeManager

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
VALID_PERIODS = frozenset({PERIOD_DAILY, PERIOD_WEEKLY})
STATUS_DEFICIT = "Deficit"
STATUS_EXCESS = "Excess"
STATUS_WITHIN_TARGET = "Within Target"

class NutritionAnalyzer:
    """
    Pre-Conditions:
        @requires plan_id > 0 
        @requires plain_id exists
        @requires period in {"daily", "weekly"}
    Post-Condition:
        @ensures \result contains nutritional totals for the selected period
        @ensures \forall nutrings in available nutrition information:
            totalNutrient = sum(recipeNutrient * (plannedServings / recipeServings))
        @ensures no planned meals => all nutrional totals == 0
    """

    def __init__(self, mealPlanner : MealPlanner, recipeManager : RecipeManager):
            self.mealPlanner = mealPlanner
            self.recipeManager = recipeManager


    def calculate_nutrition(self, planId: int, period: str) -> dict:

        raise NotImplementedError