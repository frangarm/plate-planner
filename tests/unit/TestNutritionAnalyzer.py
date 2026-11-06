import pytest

import src.plateplanner.meal.nutrition.NutritionAnalyzer as na

@pytest.fixture
def analyzer():
    return na.NutritionAnalyzer(mealPlanner = None, recipeManager = None)

#Will test analyze nutrition
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
        analyzer.analyze_nutrition({"protein": 40}, {"protein": -1})

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