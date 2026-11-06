import pytest

from plateplanner.management.recipe.RecipeManager import RecipeManager


@pytest.fixture
def recipe():
    return {
        "name": "Rice Bowl",
        "servings": 2,
        "ingredients": [{"name": "Rice", "quantity": 1, "unit": "cup"}],
    }


def test_u01_accepts_valid_recipe(recipe):
    assert RecipeManager().validate_recipe(recipe) is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", ""), ("servings", 0), ("servings", -1), ("ingredients", [])],
)
def test_u01_rejects_invalid_recipe(recipe, field, value):
    recipe[field] = value
    assert RecipeManager().validate_recipe(recipe) is False


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", ""), ("quantity", 0), ("quantity", -1), ("unit", "")],
)
def test_u01_rejects_invalid_ingredient(recipe, field, value):
    recipe["ingredients"][0][field] = value
    assert RecipeManager().validate_recipe(recipe) is False