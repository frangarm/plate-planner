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
    def analyze_nutrition(self, nutritionTotals: dict, referenceTargets: dict) -> dict:
        analysis = {}

        self.validate_analysis_input(nutritionTotals, referenceTargets)

        for nutrient, target in referenceTargets.items():
            total = nutritionTotals[nutrient]
            if total < target:
                analysis[nutrient] = STATUS_DEFICIT
            elif total > target:
                 analysis[nutrient] =  STATUS_EXCESS
            else:
                analysis[nutrient] = STATUS_WITHIN_TARGET
        
        return analysis

    # Helper function, makes sure the input is a number (either an integer or floating point)
    @staticmethod
    def is_number(value: object) -> bool:
         return isinstance(value, (int, float)) and not isinstance(value, bool)

    # Helper function, enforces the @requires clauses of analyze_nutrition
    def validate_analysis_input(self, nutritionTotals: dict, referenceTargets: dict) -> None:

         if not isinstance(nutritionTotals, dict):
              raise TypeError("Nutrition Totals must be a dict")
         if not isinstance(referenceTargets, dict):
              raise TypeError("Reference Targers must be a dict")

         for nutrient, target in referenceTargets.items():
              if nutrient not in nutritionTotals:
                   raise ValueError(f"Nutrition Totals has no value for '{nutrient}'")
              if not self.is_number(nutritionTotals[nutrient]):
                   raise TypeError(f"Nutrition Totals must be a number")
              if not self.is_number(target):
                   raise TypeError(f"Reference Targets must be a number")
              if target < 0:
                   raise ValueError(f"Reference Targets must not be negative")
              
