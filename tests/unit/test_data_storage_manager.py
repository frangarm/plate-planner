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

# D1: save_record tests
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

# D1: validate_relationships tests
def test_meal_plan_with_saved_recipes_has_valid_relationships(storage):
    first = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    second = storage.save_record(RECIPE, make_recipe("Oatmeal"))
    assert storage.validate_relationships(MEAL_PLAN, make_plan(first, second)) is True

def test_meal_plan_with_a_missing_recipe_has_invalid_relationships(storage):
    saved = storage.save_record(RECIPE, make_recipe())
    assert storage.validate_relationships(MEAL_PLAN, make_plan(saved, 99)) is False

def test_record_that_refers_to_nothing_has_valid_relationships(storage):
    assert storage.validate_relationships(RECIPE, make_recipe()) is True
    assert storage.validate_relationships(MEAL_PLAN, make_plan()) is True

def test_validate_relationships_does_not_change_the_database(storage):
    storage.validate_relationships(MEAL_PLAN, make_plan(99))
    storage.validate_relationships(RECIPE, make_recipe())
    assert storage.get_all_records(RECIPE) == []
    assert storage.get_all_records(MEAL_PLAN) == []

def test_validate_relationships_rejects_bad_arguments(storage):
    with pytest.raises(ValueError):
        storage.validate_relationships("shopping_cart", make_recipe())
    with pytest.raises(TypeError):
        storage.validate_relationships(RECIPE, None)

@pytest.mark.parametrize("bad_id", [0, -1])
def test_record_id_below_one_is_rejected(storage, bad_id):
    with pytest.raises(ValueError):
        storage.update_record(RECIPE, bad_id, make_recipe())
    with pytest.raises(ValueError):
        storage.delete_record(RECIPE, bad_id)
    
# D2: get_records and get_all_records tests 
def test_saved_record_is_returned_with_its_id_and_nested_data(storage):
    record_id = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    record = storage.get_record(RECIPE, record_id)
    assert record["record_id"] == record_id
    assert record["servings"] == 2
    assert record["ingredients"] == [{"name": "Rice", "quantity": 1, "unit": "cup"}]

def test_record_that_does_not_exist_gives_none(storage):
    assert storage.get_record(RECIPE, 99) is None 

def test_records_of_other_types_are_not_returned(storage):
    recipe_id = storage.save_record(RECIPE, make_recipe())
    list_id = storage.save_record(GROCERY_LIST, make_grocery_list())
    assert storage.get_record(MEAL_PLAN, recipe_id) is None
    assert [record["record_id"] for record in storage.get_all_records(GROCERY_LIST)] == [list_id]
 
def test_no_saved_records_gives_an_empty_list(storage):
    assert storage.get_all_records(RECIPE) == []
 
def test_all_saved_records_of_the_type_are_returned(storage):
    first = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    second = storage.save_record(RECIPE, make_recipe("Oatmeal"))
    storage.save_record(GROCERY_LIST, make_grocery_list())
    records = storage.get_all_records(RECIPE)
    assert {record["record_id"] for record in records} == {first, second}
 
def test_reading_does_not_change_the_stored_record(storage):
    record_id = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    storage.get_record(RECIPE, record_id)["name"] = "Changed"
    storage.get_all_records(RECIPE)[0]["name"] = "Changed"
    assert storage.get_record(RECIPE, record_id)["name"] == "Rice Bowl"
 
def test_unknown_record_type_is_rejected(storage):
    with pytest.raises(ValueError):
        storage.get_record("shopping_cart", 1)
    with pytest.raises(ValueError):
        storage.get_all_records("shopping_cart")
 
@pytest.mark.parametrize("bad_id", [0, -1])
def test_record_id_below_one_is_rejected(storage, bad_id):
    with pytest.raises(ValueError):
        storage.get_record(RECIPE, bad_id)
 
# D1: update_record tests
def test_update_replaces_the_stored_information(storage):
    record_id = storage.save_record(RECIPE, make_recipe("Rice Bowl"))
    assert storage.update_record(RECIPE, record_id, make_recipe("Veggie Rice Bowl")) is True
    assert storage.get_record(RECIPE, record_id)["name"] == "Veggie Rice Bowl"
 
def test_update_that_breaks_a_relationship_leaves_the_record_unchanged(storage):
    recipe_id = storage.save_record(RECIPE, make_recipe())
    plan_id = storage.save_record(MEAL_PLAN, make_plan(recipe_id))
    assert storage.update_record(MEAL_PLAN, plan_id, make_plan(99)) is False
    assert storage.get_record(MEAL_PLAN, plan_id)["meals"][0]["recipe_id"] == recipe_id

def test_update_of_a_record_that_does_not_exist_is_refused(storage):
    assert storage.update_record(RECIPE, 99, make_recipe()) is False
    assert storage.get_all_records(RECIPE) == []

# D1: delete_record tests
def test_deleted_record_no_longer_exists(storage):
    record_id = storage.save_record(RECIPE, make_recipe())
    assert storage.delete_record(RECIPE, record_id) is True
    assert storage.get_record(RECIPE, record_id) is None

def test_delete_of_a_record_that_does_not_exist_is_refused(storage):
    assert storage.delete_record(RECIPE, 99) is False
 
def test_recipe_used_by_a_saved_meal_plan_is_not_deleted(storage):
    recipe_id = storage.save_record(RECIPE, make_recipe())
    storage.save_record(MEAL_PLAN, make_plan(recipe_id))
    assert storage.delete_record(RECIPE, recipe_id) is False
    assert storage.get_record(RECIPE, recipe_id) is not None

def test_recipe_can_be_deleted_once_its_meal_plan_is_deleted(storage):
    recipe_id = storage.save_record(RECIPE, make_recipe())
    plan_id = storage.save_record(MEAL_PLAN, make_plan(recipe_id))
    assert storage.delete_record(MEAL_PLAN, plan_id) is True
    assert storage.delete_record(RECIPE, recipe_id) is True

# Additional tests
def test_records_are_still_there_after_reopening_the_database(tmp_path):
    db_file = str(tmp_path / "plateplanner.db")
    first_session = dsm.DataStorageManager(db_file)
    recipe_id = first_session.save_record(RECIPE, make_recipe("Rice Bowl"))
    plan_id = first_session.save_record(MEAL_PLAN, make_plan(recipe_id))
    second_session = dsm.DataStorageManager(db_file)
    
    assert second_session.get_record(RECIPE, recipe_id)["name"] == "Rice Bowl"
    assert second_session.get_record(MEAL_PLAN, plan_id)["meals"][0]["recipe_id"] == recipe_id
    
def test_database_that_cannot_be_opened_is_reported(tmp_path):
    missing_folder = str(tmp_path / "no_such_folder" / "plateplanner.db")
    with pytest.raises(dsm.StorageError):
        dsm.DataStorageManager(missing_folder)
