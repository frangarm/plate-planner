import pytest

import plateplanner.meal.nutrition.NutritionAnalyzer as na

@pytest.fixture
def analyzer():
    return na.NutritionAnalyzer(mealPlanner = None, recipeManager = None)


def test_below_deficit(analyzer):
    result = analyzer.analyzeNutrition({"protein": 40}, {"protein": 50})
    assert result["protein"] == na.STATUS_DEFICIT


