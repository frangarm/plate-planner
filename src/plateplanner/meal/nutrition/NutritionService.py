from plateplanner.meal.nutrition.NutritionAnalyzer import (
    NutritionAnalyzer,
    PERIOD_DAILY,
    PERIOD_WEEKLY,
    VALID_PERIODS,
)
 
DAYS_IN_WEEK = 7
DAILY_TARGETS = {"calories": 2000, "protein": 50, "carbohydrates": 250, "fat": 70}
WEEKLY_TOTAL_LABEL = "Weekly total"

class NutritionServiceError(Exception):
    """Base class of the errors this service reports (NS2).
 
    @ensures every NutritionServiceError carries a message that can be shown
             to the user (no technical details)
    """
 
class InvalidAnalysisRequestError(NutritionServiceError):
    """The plan ID or period is invalid, or Nutrition Analyzer rejected the request."""
 
class MealPlanNotFoundError(NutritionServiceError):
    """No meal plan has the requested ID."""
 
class _StorageLookup:
    """Adapter: lets Nutrition Analyzer read meal plans and recipes from storage.
    Both methods return the stored record, or None when there is none, which
    is what Nutrition Analyzer expects from its meal planner and recipe lookup.
    """
    def __init__(self, storage):
        self._storage = storage
 
    def get_meal_plan(self, plan_id):
        return self._storage.get_record("meal_plan", plan_id)
 
    def get_recipe(self, recipe_id):
        return self._storage.get_record("recipe", recipe_id)

class NutritionService:
    """Facade: one call analyzes the nutrition of a saved meal plan."""
    def __init__(self, storage, analyzer=None):
        """
        storage:  DataStorageManager-like object (get_record by type and ID)
        analyzer: object with calculate_nutrition(plan_id, period) and
                  analyze_nutrition(totals, targets). Without one, a
                  NutritionAnalyzer that reads from storage is used.
        """
        self._storage = storage
        lookup = _StorageLookup(storage)
        self._analyzer = analyzer or NutritionAnalyzer(
            meal_planner=lookup, recipe_manager=lookup
        )
 
    def analyze(self, plan_id, period=PERIOD_WEEKLY):
        """Analyze the nutrition of a saved meal plan (NS1) and report problems (NS2).
 
        Pre-conditions (NS1):
            @requires type(plan_id) == int and plan_id > 0
            @requires plan_id exists
            @requires period in {"daily", "weekly"}
 
        Post-conditions (NS1):
            @ensures \\result contains period, totals, incomplete, targets and
                     comparisons
            @ensures \\result["period"] == period
            @ensures period == "weekly" =>
                     \\result["totals"] holds one set of totals for the plan,
                     \\result["targets"] are the weekly targets (7 x the daily
                     targets) and \\result["comparisons"] has one entry,
                     "Weekly total"
            @ensures period == "daily" =>
                     \\result["totals"] holds one set of totals for each date
                     that has meals, \\result["targets"] are the daily targets
                     and \\result["comparisons"] has one entry for each of
                     those dates
            @ensures \\forall nutrient that has a total:
                     total < target  => comparison == "Deficit"
                     total > target  => comparison == "Excess"
                     total == target => comparison == "Within Target"
            @ensures \\result["incomplete"] == True => \\result["comparisons"] == {}
            @ensures no planned meals => weekly totals are all 0
            @ensures the saved meal plan and recipes are unchanged
 
        Post-conditions (NS2, what happens when the analysis cannot be done):
            @ensures type(plan_id) != int or plan_id < 1 or
                     period not in {"daily", "weekly"} =>
                     InvalidAnalysisRequestError is raised before storage is read
            @ensures plan_id does not exist => MealPlanNotFoundError is raised
            @ensures the meal plan uses a recipe that does not exist (or Nutrition
                     Analyzer raises ValueError) =>
                     InvalidAnalysisRequestError is raised with the analyzer's
                     message
            @ensures storage fails => StorageError is raised and is not wrapped
                     in a NutritionServiceError
            @ensures nothing is written to storage
            Any other error, such as a TypeError, shows a programming mistake and
            is not caught.
        """
        if type(plan_id) is not int or plan_id < 1:
            raise InvalidAnalysisRequestError("Select a valid meal plan.")
        if period not in VALID_PERIODS:
            raise InvalidAnalysisRequestError("Select a valid analysis period.")
 
        if self._storage.get_record("meal_plan", plan_id) is None:
            raise MealPlanNotFoundError("Meal plan not found.")
 
        try:
            result = dict(self._analyzer.calculate_nutrition(plan_id, period))
            result["period"] = period
            
            if period == PERIOD_DAILY:
                targets = dict(DAILY_TARGETS)
                groups = result["totals"]  
            else:
                targets = {name: value * DAYS_IN_WEEK for name, value in DAILY_TARGETS.items()}
                groups = {WEEKLY_TOTAL_LABEL: result["totals"]}
            result["targets"] = targets
 
            result["comparisons"] = {}
            if not result["incomplete"]:
                for label in sorted(groups):
                    totals = groups[label]
                    wanted = {name: value for name, value in targets.items() if name in totals}
                    result["comparisons"][label] = self._analyzer.analyze_nutrition(totals, wanted)
        except ValueError as error:
            raise InvalidAnalysisRequestError(str(error)) from error
 
        return result