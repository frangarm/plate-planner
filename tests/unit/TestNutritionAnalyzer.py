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
    assert result["sodiium"] == na.STATUS_EXCESS

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
    result = analyzer.analyze_nutrition({"sugar": 1}, {"sugar": 0})
    assert result["sugar"] == na.STATUS_DEFICIT

def test_decimal_values(analyzer):
    result = analyzer.analyze_nutrition({"sugar": 1.5}, {"sugar": 2.0})
    assert result["sugar"] == na.STATUS_DEFICIT

def test_no_target(analyzer):
    assert analyzer.analyze_nutrition({"protein": 40}, {}) == {}

