import pytest
from data.DataStorageManager import (
    RECORD_TYPE_GROCERY_LIST,
    RECORD_TYPE_MEAL_PLAN,
    RECORD_TYPE_RECIPE,
    DataStorageManager,
    StorageError,
)
import plateplanner.management.recipe.RecipeService as rs
import plateplanner.meal.nutrition.NutritionService as ns

NUTRITION = {"calories": 500, "protein": 20, "carbohydrates": 60, "fat": 10}
WEEKLY_TARGETS = {"calories": 14000, "protein": 350, "carbohydrates": 1750, "fat": 490}
DAILY_TARGETS = {"calories": 2000, "protein": 50, "carbohydrates": 250, "fat": 70}
MONDAY, TUESDAY = "2026-11-16", "2026-11-17"


@pytest.fixture
def database_path(tmp_path):
    return str(tmp_path / "nutrition.db")

@pytest.fixture
def storage(database_path):
    database = DataStorageManager(database_path)
    yield database
    database.close()

@pytest.fixture
def service(storage):
    return ns.NutritionService(storage)

def save_recipe(storage, nutrition=NUTRITION, servings=2, name="Pasta"):
    recipe = {
        "name": name,
        "servings": servings,
        "ingredients": [{"name": "Flour", "quantity": 300, "unit": "g"}],
    }
    if nutrition is not None:
        recipe["nutrition"] = nutrition
    return storage.save_record(RECORD_TYPE_RECIPE, recipe)

def meal(recipe_id, date=TUESDAY, servings=2):
    return {"date": date, "mealSlot": "dinner", "recipe_id": recipe_id, "servings": servings}

def save_plan(storage, meals):
    plan_id = storage.save_record(
        RECORD_TYPE_MEAL_PLAN, {"weekStart": MONDAY, "meals": meals}
    )
    assert plan_id is not None  # the real storage checks that recipes exist
    return plan_id

def everything_saved(storage):
    return {
        kind: storage.get_all_records(kind)
        for kind in (RECORD_TYPE_RECIPE, RECORD_TYPE_MEAL_PLAN, RECORD_TYPE_GROCERY_LIST)
    }

def test_weekly_analysis_of_a_saved_plan(service, storage):
    recipe_id = save_recipe(storage)  # serves 2
    plan_id = save_plan(storage, [
        meal(recipe_id, MONDAY, servings=2), meal(recipe_id, TUESDAY, servings=1),
    ])

    result = service.analyze(plan_id, "weekly")

    assert result["totals"] == {"calories": 750, "protein": 30, "carbohydrates": 90, "fat": 15}
    assert result["targets"] == WEEKLY_TARGETS
    assert result["incomplete"] is False
    assert result["comparisons"] == {
        "Weekly total": {n: "Deficit" for n in NUTRITION}
    }

def test_daily_analysis_of_a_saved_plan(service, storage):
    recipe_id = save_recipe(storage)
    plan_id = save_plan(storage, [
        meal(recipe_id, MONDAY, servings=2), meal(recipe_id, TUESDAY, servings=1),
    ])

    result = service.analyze(plan_id, "daily")

    assert result["totals"][MONDAY] == NUTRITION
    assert result["totals"][TUESDAY] == {n: v / 2 for n, v in NUTRITION.items()}
    assert result["targets"] == DAILY_TARGETS
    assert result["comparisons"][MONDAY] == {n: "Deficit" for n in NUTRITION}

def test_excess_and_within_target_are_reported_from_real_data(service, storage):
    heavy = save_recipe(storage, {"calories": 15000, "protein": 350, "carbohydrates": 100, "fat": 490}, servings=1)
    plan_id = save_plan(storage, [meal(heavy, servings=1)])

    comparison = service.analyze(plan_id, "weekly")["comparisons"]["Weekly total"]

    assert comparison == {
        "calories": "Excess", "protein": "Within Target",
        "carbohydrates": "Deficit", "fat": "Within Target",
    }

def test_two_plans_are_analyzed_separately(service, storage):
    pasta = save_recipe(storage)
    soup = save_recipe(storage, {"calories": 100, "protein": 5, "carbohydrates": 10, "fat": 2}, name="Soup")
    first = save_plan(storage, [meal(pasta)])
    second = save_plan(storage, [meal(soup)])

    assert service.analyze(first)["totals"]["calories"] == 500
    assert service.analyze(second)["totals"]["calories"] == 100

def test_a_plan_with_no_meals_is_all_zeros(service, storage):
    result = service.analyze(save_plan(storage, []), "weekly")

    assert result["totals"] == {n: 0 for n in NUTRITION}
    assert result["incomplete"] is False

def test_a_recipe_without_nutrition_makes_the_analysis_incomplete(service, storage):
    plan_id = save_plan(storage, [meal(save_recipe(storage, nutrition=None))])

    result = service.analyze(plan_id, "weekly")

    assert result["incomplete"] is True
    assert result["comparisons"] == {}

def test_the_analysis_is_the_same_after_reconnecting(database_path):
    first = DataStorageManager(database_path)
    plan_id = save_plan(first, [meal(save_recipe(first))])
    before = ns.NutritionService(first).analyze(plan_id, "daily")
    first.close()

    second = DataStorageManager(database_path)
    try:
        assert ns.NutritionService(second).analyze(plan_id, "daily") == before
    finally:
        second.close()
        
def test_an_unknown_plan_is_not_found(service):
    with pytest.raises(ns.MealPlanNotFoundError):
        service.analyze(42, "weekly")

def test_a_recipe_id_is_not_mistaken_for_a_plan_id(service, storage):
    save_recipe(storage)  # recipe 1 exists, plan 1 does not

    with pytest.raises(ns.MealPlanNotFoundError):
        service.analyze(1, "weekly")

@pytest.mark.parametrize("plan_id", [0, -3, True])
def test_a_bad_plan_id_is_an_invalid_request_not_a_value_error_from_storage(service, plan_id):
    with pytest.raises(ns.InvalidAnalysisRequestError):
        service.analyze(plan_id, "weekly")

def test_an_unknown_period_is_an_invalid_request(service, storage):
    plan_id = save_plan(storage, [meal(save_recipe(storage))])

    with pytest.raises(ns.InvalidAnalysisRequestError):
        service.analyze(plan_id, "monthly")

def test_a_closed_database_raises_storage_error_not_a_service_error(service, storage):
    plan_id = save_plan(storage, [meal(save_recipe(storage))])
    storage.close()

    with pytest.raises(StorageError) as raised:
        service.analyze(plan_id, "weekly")

    assert not isinstance(raised.value, ns.NutritionServiceError)

def test_analysis_changes_nothing_in_the_database(service, storage):
    plan_id = save_plan(storage, [meal(save_recipe(storage))])
    before = everything_saved(storage)

    service.analyze(plan_id, "weekly")
    service.analyze(plan_id, "daily")

    assert everything_saved(storage) == before

GOOD_RECIPE = {
    "name": "Pasta",
    "servings": 2,
    "ingredients": [{"name": "Flour", "quantity": 300, "unit": "g"}],
}

def test_a_recipe_made_with_the_recipe_service_is_analyzed(storage):
    recipes = rs.RecipeService(storage)
    recipe_id = recipes.create({**GOOD_RECIPE, "nutrition": NUTRITION})["record_id"]
    plan_id = save_plan(storage, [meal(recipe_id)])

    result = ns.NutritionService(storage).analyze(plan_id, "weekly")

    assert result["totals"] == NUTRITION

def test_editing_a_recipes_name_does_not_lose_its_nutrition(storage):
    recipes = rs.RecipeService(storage)
    recipe_id = recipes.create({**GOOD_RECIPE, "nutrition": NUTRITION})["record_id"]
    plan_id = save_plan(storage, [meal(recipe_id)])

    recipes.update(recipe_id, {**GOOD_RECIPE, "name": "Better pasta"})

    result = ns.NutritionService(storage).analyze(plan_id, "weekly")
    assert result["totals"] == NUTRITION
    assert result["incomplete"] is False

def test_changing_a_recipes_nutrition_changes_the_next_analysis(storage):
    recipes = rs.RecipeService(storage)
    recipe_id = recipes.create({**GOOD_RECIPE, "nutrition": NUTRITION})["record_id"]
    plan_id = save_plan(storage, [meal(recipe_id)])
    nutrition = ns.NutritionService(storage)
    assert nutrition.analyze(plan_id)["totals"]["calories"] == 500

    recipes.update(recipe_id, {**GOOD_RECIPE, "nutrition": {**NUTRITION, "calories": 900}})

    assert nutrition.analyze(plan_id)["totals"]["calories"] == 900

def test_a_recipe_in_a_plan_cannot_be_deleted_so_the_analysis_keeps_working(storage):
    recipes = rs.RecipeService(storage)
    recipe_id = recipes.create({**GOOD_RECIPE, "nutrition": NUTRITION})["record_id"]
    plan_id = save_plan(storage, [meal(recipe_id)])

    with pytest.raises(rs.RecipeInUseError):
        recipes.delete(recipe_id)

    assert ns.NutritionService(storage).analyze(plan_id)["totals"] == NUTRITION