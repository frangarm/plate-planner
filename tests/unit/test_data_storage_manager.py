import pytest
import data.DataStorageManager as dsm

RECIPE = "recipe"
MEAL_PLAN = "meal_plan"
GROCERY_LIST =  "grocery_list"

# Helpers, will build the data that will be used.
def make_recipe(name="Rice Bowl"):
    return {"name": name, "servings": 2,
            "ingredients": [{"name": "Rice", "quantity": 1, "unit": "cup"}]}
 
 
def make_plan(*recipe_ids):
    meals = [{"date": "2026-11-02", "meal_slot": "dinner", "recipe_id": recipe_id, "servings": 1}
             for recipe_id in recipe_ids]
    return {"week_start": "2026-11-02", "meals": meals}
 
 
def make_grocery_list():
    return {"items": [{"name": "Rice", "quantity": 2, "unit": "cup", "purchased": False}]}
 
 
@pytest.fixture
def storage():
    return dsm.DataStorageManager(":memory:")

# D1: Save Record tests

def test_saved_recipe_has_positive_id_stored(storage):
    record_id = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    assert record_id is not None and record_id > 0
    assert storage.get_record(RECIPE, record_id)["name"] == "Rice Bowl"

def test_every_record_type_is_stored(storage):
    recipe_id = storage.save_record(RECIPE, make_recipe())
    assert storage.save_record(MEAL_PLAN, make_plan(recipe_id)) is not None
    assert storage.save_record(GROCERY_LIST, make_grocery_list()) is not None

def test_each_saved_record_type_gets_own_id(storage):
    first = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    second = storage.save_record(RECIPE, make_recipe("Oatmeal"))
    assert first != second

def test_meal_plan_with_missing_recipe_not_stored(storage):
    assert storage.save_record(MEAL_PLAN, make_plan(99)) is None
    assert storage.get_all_records(MEAL_PLAN) == []

def test_unknown_record_type_rejected(storage):
    with pytest.raises(ValueError):
        storage.save_record("shopping_cart", make_recipe())

@pytest.mark.parametrize("bad_data", [None, [], "recipe", 5])
def test_record_data_that_is_not_dict_rejected(storage, bad_data):
    with pytest.raises(TypeError):
        storage.save_record(RECIPE, bad_data)

