from plateplanner.meal.planning.MealPlanner import MealPlanner
from plateplanner.management.recipe.RecipeManager import RecipeManager

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
VALID_PERIODS = frozenset({PERIOD_DAILY, PERIOD_WEEKLY})
STATUS_DEFICIT = "Deficit"
STATUS_EXCESS = "Excess"
STATUS_WITHIN_TARGET = "Within Target"
REQUIRED_NUTRIENTS = ("calories", "protein", "carbohydrates", "fat")

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

        self.check_calculation_request(planId, period)
        plan = self.mealPlanner.get_meal_plan(planId)
        if plan is None:
            raise ValueError(f"meal plan {planId} does not exist")
 
        weeklyTotals = {nutrient: 0 for nutrient in REQUIRED_NUTRIENTS}
        dailyTotals = {}
        incomplete = False
 
        for meal in plan["meals"]:
            recipe = self.recipeManager.get_recipe(meal["recipeId"])
            nutrition = recipe.get("nutrition") or {}
            if not self.has_required_nutrients(nutrition):
                incomplete = True
            scaled = self.scale_nutrition(nutrition, meal["servings"], recipe["servings"])
            self.add_nutrition(weeklyTotals, scaled)
            self.add_nutrition(dailyTotals.setdefault(meal["date"], {}), scaled)
 
        totals = dailyTotals if period == PERIOD_DAILY else weeklyTotals
        return {"period": period, "totals": totals, "incomplete": incomplete}
    
    def check_calculation_request(self, plan_id: int, period: str) -> None:
        if period not in VALID_PERIODS:
            raise ValueError(f"period must be one of {sorted(VALID_PERIODS)}")
        if plan_id < 1:
            raise ValueError("planId must be greater than 0")

    def has_required_nutrients(self, nutrition: dict) -> bool:
        return all(self.is_number(nutrition.get(nutrient)) for nutrient in REQUIRED_NUTRIENTS)
    
    def scale_nutrition(self, nutrition: dict, plannedServings: float,recipeServings: float) -> dict:

        scale = plannedServings / recipeServings
        return {nutrient: value * scale for nutrient, value in nutrition.items() if self.is_number(value)}
 
    def add_nutrition(self, totals: dict, additions: dict) -> None:
        for nutrient, value in additions.items(): totals[nutrient] = totals.get(nutrient, 0) + value

    """
        Pre-conditions: 
            @requires nutrition_data != None 
            @requires type(nutrition_data) == dict 

        Post-conditions: 
            @ensures \result == True iff all required nutrition information is available 
            @ensures \result == False iff at least one required nutritional value is missing 
    """
    def check_nutrition_data(self, nutritionData: dict) -> bool: 
        if not isinstance(nutritionData, dict):
            raise TypeError("nutritionData must be a dict")
        return all(self.has_required_nutrients(nutrition) for nutrition in nutritionData.values())
    
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
              
