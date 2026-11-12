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
    
    def __init__(self, meal_planner : MealPlanner, recipe_manager : RecipeManager):
            self.meal_planner = meal_planner
            self.recipe_manager = recipe_manager
    
    """
    Pre-Conditions:
        @requires plan_id > 0 
        @requires plan_id exists
        @requires period in {"daily", "weekly"}
    Post-Condition:
        @ensures \result contains nutritional totals for the selected period
        @ensures \forall nutrients in available nutrition information:
            total_nutrient = sum(recipe_nutrient * (planned_servings / recipe_servings))
        @ensures no planned meals => all nutritional totals == 0
    """
    def calculate_nutrition(self, plan_id: int, period: str) -> dict:

        self.check_calculation_request(plan_id, period)
        plan = self.meal_planner.get_meal_plan(plan_id)
        
        if plan is None:
            raise ValueError(f"meal plan {plan_id} does not exist")
        
        weekly_totals = {nutrient: 0 for nutrient in REQUIRED_NUTRIENTS}
        daily_totals = {}
        incomplete = False
 
        for meal in plan["meals"]:
            recipe = self.recipe_manager.get_recipe(meal["recipe_id"])
            if recipe is None:
                        raise ValueError(f"recipe {meal['recipe_id']} does not exist")
            nutrition = recipe.get("nutrition")
            if not isinstance(nutrition, dict):
                nutrition = {}
            if not self.has_required_nutrients(nutrition):
                incomplete = True
            scaled = self.scale_nutrition(nutrition, meal["servings"], recipe["servings"])
            self.add_nutrition(weekly_totals, scaled)
            self.add_nutrition(daily_totals.setdefault(meal["date"], {}), scaled)
 
        totals = daily_totals if period == PERIOD_DAILY else weekly_totals
        return {"period": period, "totals": totals, "incomplete": incomplete}
    
    def check_calculation_request(self, plan_id: int, period: str) -> None:
        if period not in VALID_PERIODS:
            raise ValueError(f"period must be one of {sorted(VALID_PERIODS)}")
        if plan_id < 1:
            raise ValueError("plan_id must be greater than 0")

    def has_required_nutrients(self, nutrition: dict) -> bool:
        return all(self.is_number(nutrition.get(nutrient)) for nutrient in REQUIRED_NUTRIENTS)
    
    def scale_nutrition(self, nutrition: dict, planned_servings: float,recipe_servings: float) -> dict:

        scale = planned_servings / recipe_servings
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
    def check_nutrition_data(self, nutrition_data: dict) -> bool: 
        if not isinstance(nutrition_data, dict):
            raise TypeError("nutrition_data must be a dict")
        return all(self.has_required_nutrients(nutrition) for nutrition in nutrition_data.values())
    
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
        analysis = {}

        self.validate_analysis_input(nutrition_totals, reference_targets)

        for nutrient, target in reference_targets.items():
            total = nutrition_totals[nutrient]
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
    def validate_analysis_input(self, nutrition_totals: dict, reference_targets: dict) -> None:

         if not isinstance(nutrition_totals, dict):
              raise TypeError("Nutrition Totals must be a dict")
         if not isinstance(reference_targets, dict):
              raise TypeError("Reference Targets must be a dict")

         for nutrient, target in reference_targets.items():
              if nutrient not in nutrition_totals:
                   raise ValueError(f"Nutrition Totals has no value for '{nutrient}'")
              if not self.is_number(nutrition_totals[nutrient]):
                   raise TypeError(f"Nutrition Totals must be a number")
              if not self.is_number(target):
                   raise TypeError(f"Reference Targets must be a number")
              if target < 0:
                   raise ValueError(f"Reference Targets must not be negative")
              
