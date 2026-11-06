from plateplanner.management.grocery.GroceryListManager import GroceryListManager


def test_u03_combines_rice_in_the_same_unit():
    ingredients = [
        {"name": "Rice", "quantity": 0.5, "unit": "cup"},
        {"name": "Rice", "quantity": 1.5, "unit": "cup"},
        {"name": "Rice", "quantity": 100, "unit": "g"},
    ]

    result = GroceryListManager().combine_ingredients(ingredients)

    assert result == [
        {"name": "Rice", "quantity": 2, "unit": "cup"},
        {"name": "Rice", "quantity": 100, "unit": "g"},
    ]


def test_u03_combines_grams_and_kilograms():
    ingredients = [
        {"name": "Rice", "quantity": 500, "unit": "g"},
        {"name": "Rice", "quantity": 1, "unit": "kg"},
    ]

    result = GroceryListManager().combine_ingredients(ingredients)

    assert result == [{"name": "Rice", "quantity": 1500, "unit": "g"}]


def test_gather_ingredients_scales_planned_servings():
    manager = GroceryListManager(
        get_meal_plan=lambda plan_id: {
            "meals": [
                {"recipe_id": 1, "servings": 1},
                {"recipe_id": 1, "servings": 3},
            ]
        },
        get_recipe=lambda recipe_id: {
            "servings": 2,
            "ingredients": [{"name": "Rice", "quantity": 1, "unit": "cup"}],
        },
    )

    assert manager.gather_ingredients(1) == [
        {"name": "Rice", "quantity": 0.5, "unit": "cup"},
        {"name": "Rice", "quantity": 1.5, "unit": "cup"},
    ]