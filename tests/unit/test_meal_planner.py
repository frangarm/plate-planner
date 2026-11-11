
"""Unit tests for U02 - Meal Input Validation."""

from unittest.mock import Mock

import pytest

from plateplanner.meal.planning.MealPlanner import MealPlanner


@pytest.fixture
def valid_meal():
    """Create a valid meal to use in the tests."""
    return {
        "date": "2026-11-09",
        "mealSlot": "dinner",
        "recipeId": 1,
        "servings": 2,
    }


@pytest.fixture
def planner():
    """Create a MealPlanner with a sample recipe."""
    recipe_manager = Mock()

    # Recipe 1 exists. Other recipe IDs do not.
    recipe_manager.get_recipe.side_effect = lambda recipe_id: (
        {"name": "Rice Bowl", "servings": 2}
        if recipe_id == 1 else None
    )

    return MealPlanner(recipe_manager=recipe_manager)


def test_u02_accepts_valid_meal(planner, valid_meal):
    """Check that a meal with valid information is accepted."""
    assert planner.validate_meal(valid_meal) is True


@pytest.mark.parametrize(
    "field",
    ["date", "mealSlot", "recipeId", "servings"],
)
def test_u02_rejects_missing_fields(planner, valid_meal, field):
    """Check that missing required information is rejected."""
    del valid_meal[field]

    assert planner.validate_meal(valid_meal) is False


@pytest.mark.parametrize(
    "date",
    ["", "11/09/2026", "2026-02-30", None],
)
def test_u02_rejects_invalid_dates(planner, valid_meal, date):
    """Check that invalid dates are rejected."""
    valid_meal["date"] = date

    assert planner.validate_meal(valid_meal) is False


@pytest.mark.parametrize(
    "slot",
    ["brunch", "Dinner", "", None],
)
def test_u02_rejects_invalid_meal_slots(planner, valid_meal, slot):
    """Check that unsupported meal slots are rejected."""
    valid_meal["mealSlot"] = slot

    assert planner.validate_meal(valid_meal) is False


@pytest.mark.parametrize(
    "servings",
    [0, -1, "2", None, True, float("inf"), float("nan")],
)
def test_u02_rejects_invalid_servings(
        planner, valid_meal, servings
):
    """Check that invalid serving amounts are rejected."""
    valid_meal["servings"] = servings

    assert planner.validate_meal(valid_meal) is False


@pytest.mark.parametrize(
    "recipe_id",
    [0, -1, "1", None, True, 1.0],
)
def test_u02_rejects_invalid_recipe_ids(
        planner, valid_meal, recipe_id
):
    """Check that invalid recipe IDs are rejected."""
    valid_meal["recipeId"] = recipe_id

    assert planner.validate_meal(valid_meal) is False


def test_u02_rejects_missing_recipe(planner, valid_meal):
    """Check that a meal cannot use a nonexistent recipe."""
    valid_meal["recipeId"] = 99

    assert planner.validate_meal(valid_meal) is False


def test_u02_accepts_fractional_servings(planner, valid_meal):
    """Check that positive fractional servings are accepted."""
    valid_meal["servings"] = 0.5

    assert planner.validate_meal(valid_meal) is True


def test_u02_rejects_missing_recipe_manager(valid_meal):
    """Check that validation fails without a recipe manager."""
    planner = MealPlanner()

    assert planner.validate_meal(valid_meal) is False
