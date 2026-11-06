from plateplanner.meal.planning.MealPlanner import MealPlanner
from plateplanner.management.recipe.RecipeManager import RecipeManager

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
VALID_PERIODS = frozenset({PERIOD_DAILY, PERIOD_WEEKLY})
STATUS_DEFICIT = "Deficit"
STATUS_EXCESS = "Excess"
STATUS_WITHIN_TARGET = "Within Target"

class NutritionAnalyzer:
    
    def __init__(self, mealPlanner : MealPlanner, recipeManager : RecipeManager):
            self.mealPlanner = mealPlanner
            self.recipeManager = recipeManager
    
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
    def calculate_nutrition(self, planId: int, period: str) -> dict:

        raise NotImplementedError
    
    """
    Pre-conditions: 
        @requires nutrition_totals != None 
        @requires reference_targets != None 
        @requires type(nutrition_totals) == dict 
        @requires type(reference_targets) == dict 
        @requires \forall nutrient being compared: 
            nutrient exists in nutrition_totals 
            nutrient exists in reference_targets 
            reference_targets[nutrient] >= 0 
        @requires nutrition_totals and reference_targets use the same time period 
    Post-conditions: 
        @ensures \forall nutrient being compared: 
        nutrition_totals[nutrient] < reference_targets[nutrient] 
            => \result[nutrient] == "Deficit"
        nutrition_totals[nutrient] > reference_targets[nutrient] 
            => \result[nutrient] == "Excess" 
        nutrition_totals[nutrient] == reference_targets[nutrient] 
            => \result[nutrient] == "Within Target" 
    """
    def analyze_nutrition(self, nutrition_totals: dict, reference_targets: dict) -> dict:
        
        results = {}

        for nutrient, total in nutrition_totals.items():
            if nutrient not in reference_targets:
                continue

            target = reference_targets[nutrient]
            if target < 0:
                raise ValueError(f"Target for {nutrient} must be non-negative")

            if total < target:
                results[nutrient] = STATUS_DEFICIT
            elif total > target:
                results[nutrient] = STATUS_EXCESS
            else:
                results[nutrient] = STATUS_WITHIN_TARGET

        return results