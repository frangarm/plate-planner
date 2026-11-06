import pytest
import copy
import src.plateplanner.meal.nutrition.NutritionAnalyzer as na
from unittest.mock import Mock

@pytest.fixture
def analyzer():
    return na.NutritionAnalyzer(mealPlanner = None, recipeManager = None)

#Will test analyze_nutrition (N2)
def test_deficit(analyzer):
    result = analyzer.analyze_nutrition({"protein": 40}, {"protein": 50})
    assert result["protein"] == na.STATUS_DEFICIT

def test_excess(analyzer):
    result = analyzer.analyze_nutrition({"sodium": 3000}, {"sodium": 2300})
    assert result["sodium"] == na.STATUS_EXCESS

def test_within_target(analyzer):
    result = analyzer.analyze_nutrition({"fiber": 25}, {"fiber": 25})
    assert result["fiber"] == na.STATUS_WITHIN_TARGET
    
def test_multiple_nutrients(analyzer):
    result = analyzer.analyze_nutrition( {"protein": 40, "sodium": 3000}, {"protein": 50, "sodium": 2300})
    assert result == {"protein": na.STATUS_DEFICIT, "sodium": na.STATUS_EXCESS}

def test_invalid_input(analyzer):
    with pytest.raises(ValueError):
        analyzer.analyze_nutrition({"protein": 40}, {"protein": -1})

def test_labels_match(analyzer):
    assert na.STATUS_DEFICIT == "Deficit"
    assert na.STATUS_EXCESS == "Excess"
    assert na.STATUS_WITHIN_TARGET == "Within Target"

def test_zero_to_zero(analyzer):
    result = analyzer.analyze_nutrition({"sugar": 0}, {"sugar": 0})
    assert result["sugar"] == na.STATUS_WITHIN_TARGET

def test_zero_with_positive(analyzer):
    result = analyzer.analyze_nutrition({"sugar": 0}, {"sugar": 1})
    assert result["sugar"] == na.STATUS_DEFICIT

def test_decimal_values(analyzer):
    result = analyzer.analyze_nutrition({"sugar": 1.5}, {"sugar": 2.0})
    assert result["sugar"] == na.STATUS_DEFICIT

def test_no_target(analyzer):
    assert analyzer.analyze_nutrition({"protein": 40}, {}) == {}

def test_compare_multiple_to_one(analyzer):
    result = analyzer.analyze_nutrition({"protein": 40, "fat": 90}, {"protein": 50})
    assert result == {"protein": na.STATUS_DEFICIT}

def test_inputs_are_not_changed(analyzer):
    totals = {"protein": 40}
    targets = {"protein": 50}
    analyzer.analyze_nutrition(totals, targets)
    assert totals == {"protein": 40}
    assert targets == {"protein": 50}

def test_negative_target_is_rejected(analyzer):
    with pytest.raises(ValueError):
        analyzer.analyze_nutrition({"protein": 50}, {"protein": -10})

def test_target_nutrient_missing_from_totals_is_rejected(analyzer):
    with pytest.raises(ValueError):
        analyzer.analyze_nutrition({"protein": 40}, {"protein": 50, "fiber": 25})

@pytest.mark.parametrize("badTotals", [None, [], "protein", 5])
def test_nondict_totals(analyzer, badTotals):
    with pytest.raises(TypeError):
        analyzer.analyze_nutrition(badTotals, {"protein": 50})

@pytest.mark.parametrize( "badTargets", [None, [], "protein", 5])
def test_nondict_targets(analyzer, badTargets):
    with pytest.raises(TypeError):
        analyzer.analyze_nutrition({"protein": 50}, badTargets)

@pytest.mark.parametrize("badValues", ["40", None, True])
def test_bad_total_values(analyzer, badValues):
    with pytest.raises(TypeError):
        analyzer.analyze_nutrition({"protein": badValues}, {"protein": 50})

@pytest.mark.parametrize("badValues", ["40", None, True])
def test_bad_target_values(analyzer, badValues):
    with pytest.raises(TypeError):
        analyzer.analyze_nutrition({"protein": 50}, {"protein": badValues})


# Will test calculate_nutrition (N1)
MONDAY = "2026-11-02"
TUESDAY = "2026-11-03"
PLAN_ID = 1
OATMEAL_ID = 1
SALAD_ID = 2
STEW_ID = 3
CASSEROLE_ID = 4
NO_FAT_ID = 5
 
REQUIRED_NUTRIENTS = ("calories", "protein", "carbohydrates", "fat")

RECIPES = {
    OATMEAL_ID: {"name": "Oatmeal", "servings": 2, "nutrition": {"calories": 300, "protein": 10, "carbohydrates": 50, "fat": 6}},
    
    SALAD_ID: {"name": "Chicken Salad", "servings": 4, "nutrition": {"calories": 800, "protein": 60, "carbohydrates": 20, "fat": 40}},
    
    STEW_ID: {"name": "Lentil Stew", "servings": 4, "nutrition": {"calories": 600, "protein": 40, "carbohydrates": 90, "fat": 8, "fiber": 24}},
    
    CASSEROLE_ID: {"name": "Mystery Casserole", "servings": 2},
    
    NO_FAT_ID: {"name": "Plain Rice", "servings": 2, "nutrition": {"calories": 400, "protein": 8, "carbohydrates": 90}},
}

 # Helper Functions for calculate_nutrition tests
def make_meal(mealId, date, recipeId, servings):
    return {"mealId": mealId, "date": date, "mealSlot": "dinner", "recipeId": recipeId, "servings": servings}
 
def make_plan(*meals):
    return {"planId": PLAN_ID, "weekStart": MONDAY, "meals": list(meals)}
 
def build_analyzer(plan):
    recipes = copy.deepcopy(RECIPES)

    def fake_get_meal_plan(planId):
        if planId == plan["planId"]:
            return plan
        return None
 
    def fake_get_recipe(recipeId):
        return recipes.get(recipeId)
 
    planner = Mock()
    planner.get_meal_plan.side_effect = fake_get_meal_plan
    recipe_manager = Mock()
    recipe_manager.get_recipe.side_effect = fake_get_recipe
    return na.NutritionAnalyzer(planner, recipe_manager), planner, recipe_manager
 
def weekly_totals(*meals):
    analyzer, _, _ = build_analyzer(make_plan(*meals))
    return analyzer.calculate_nutrition(PLAN_ID, na.PERIOD_WEEKLY)["totals"]
 
def test_one_meal_scaled_to_half_the_recipe():
    totals = weekly_totals(make_meal(1, MONDAY, OATMEAL_ID, 1))      
    assert totals["calories"] == pytest.approx(150)
    assert totals["protein"] == pytest.approx(5)
 
def test_more_servings_than_recipe_scales_up():
    totals = weekly_totals(make_meal(1, MONDAY, OATMEAL_ID, 4))      
    assert totals["calories"] == pytest.approx(600)
 
def test_fractional_servings_are_scaled():
    totals = weekly_totals(make_meal(1, MONDAY, OATMEAL_ID, 0.5))
    assert totals["calories"] == pytest.approx(75)
 
def test_different_recipes_are_added_together():
    totals = weekly_totals(make_meal(1, MONDAY, OATMEAL_ID, 1),     
                           make_meal(2, TUESDAY, SALAD_ID, 2))      
    assert totals["calories"] == pytest.approx(550)
 
def test_daily_totals_are_grouped_by_date():
    analyzer, _, _ = build_analyzer(make_plan(make_meal(1, MONDAY, OATMEAL_ID, 1), make_meal(2, TUESDAY, SALAD_ID, 2)))
    totals = analyzer.calculate_nutrition(PLAN_ID, na.PERIOD_DAILY)["totals"]
    assert totals[MONDAY]["calories"] == pytest.approx(150)
    assert totals[TUESDAY]["calories"] == pytest.approx(400)

def test_weekly_totals_are_zero_when_no_meals_are_planned():
    totals = weekly_totals()
    for nutrient in REQUIRED_NUTRIENTS:
        assert totals[nutrient] == 0
 
def test_daily_totals_are_empty_when_no_meals_are_planned():
    analyzer, _, _ = build_analyzer(make_plan())
    assert analyzer.calculate_nutrition(PLAN_ID, na.PERIOD_DAILY)["totals"] == {}
 
def test_complete_nutrition_data_is_not_marked_incomplete():
    analyzer, _, _ = build_analyzer(make_plan(make_meal(1, MONDAY, OATMEAL_ID, 1)))
    assert analyzer.calculate_nutrition(PLAN_ID, na.PERIOD_WEEKLY)["incomplete"] is False
 
def test_recipe_without_nutrition_marks_result_incomplete():
    analyzer, _, _ = build_analyzer(make_plan(make_meal(1, MONDAY, CASSEROLE_ID, 1)))
    assert analyzer.calculate_nutrition(PLAN_ID, na.PERIOD_WEEKLY)["incomplete"] is True
 
def test_meals_with_data_are_still_totaled_when_another_meal_is_missing_data():
    totals = weekly_totals(make_meal(1, MONDAY, OATMEAL_ID, 1), make_meal(2, MONDAY, CASSEROLE_ID, 1))
    assert totals["calories"] == pytest.approx(150)

@pytest.mark.parametrize("bad_plan_id", [0, -1])
def test_plan_id_below_one_is_rejected(bad_plan_id):
    analyzer, _, _ = build_analyzer(make_plan())
    with pytest.raises(ValueError):
        analyzer.calculate_nutrition(bad_plan_id, na.PERIOD_WEEKLY)
 
def test_plan_that_does_not_exist_is_rejected():
    analyzer, _, _ = build_analyzer(make_plan())
    with pytest.raises(ValueError):
        analyzer.calculate_nutrition(99, na.PERIOD_WEEKLY)
 
@pytest.mark.parametrize("bad_period", ["monthly", "", None])
def test_period_outside_daily_and_weekly_is_rejected(bad_period):
    analyzer, _, _ = build_analyzer(make_plan())
    with pytest.raises(ValueError):
        analyzer.calculate_nutrition(PLAN_ID, bad_period)
        
def test_meal_plan_and_every_planned_recipe_are_requested():
    analyzer, planner, recipe_manager = build_analyzer(make_plan( make_meal(1, MONDAY, OATMEAL_ID, 1), make_meal(2, TUESDAY, SALAD_ID, 2)))
    analyzer.calculate_nutrition(PLAN_ID, na.PERIOD_WEEKLY)
    planner.get_meal_plan.assert_called_with(PLAN_ID)
    requested_ids = {call.args[0] for call in recipe_manager.get_recipe.call_args_list}
    assert requested_ids == {OATMEAL_ID, SALAD_ID}

# Tests for check_nutrition_data (N1)

def make_complete_nutrition():
    return {"calories": 300, "protein": 10, "carbohydrates": 50, "fat": 6}
 
@pytest.fixture
def analyzer():
    return na.NutritionAnalyzer(mealPlanner=None, recipeManager=None)
 
def test_all_required_values_present_is_true(analyzer):
    assert analyzer.check_nutrition_data({1: make_complete_nutrition()}) is True
 
def test_one_missing_required_value_is_false(analyzer):
    entry = make_complete_nutrition()
    del entry["fat"]
    assert analyzer.check_nutrition_data({1: make_complete_nutrition(), 2: entry}) is False
 
def test_zero_counts_as_an_available_value(analyzer):
    entry = make_complete_nutrition()
    entry["fat"] = 0
    assert analyzer.check_nutrition_data({1: entry}) is True
 
@pytest.mark.parametrize("bad_data", [None, [], "calories", 5])
def test_nutrition_data_that_is_not_a_dict_is_rejected(analyzer, bad_data):
    with pytest.raises(TypeError):
        analyzer.check_nutrition_data(bad_data)
