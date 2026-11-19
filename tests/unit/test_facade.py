from copy import deepcopy
from unittest.mock import Mock
import pytest
from data.DataStorageManager import StorageError
import plateplanner.management.recipe.RecipeService as rs

GOOD_RECIPE = {
    "name": "Pasta",
    "servings": 2,
    "ingredients": [{"name": "Flour", "quantity": 300, "unit": "g"}],
}

class FakeStorage:
    """In-memory stand-in for DataStorageManager (same return-value semantics).
    save -> new id (or None), update/delete -> bool, missing reads -> None.
    Failure switches let tests simulate StorageError on each operation.
    """

    def __init__(self):
        self._records = {}
        self._next_id = {}
        self.save_fails = False
        self.save_returns_none = False
        self.read_fails = False
        self.update_fails = False
        self.in_use_recipe_ids = frozenset()

    def save_record(self, record_type, record_data):
        if self.save_fails:
            raise StorageError("simulated storage failure")
        if self.save_returns_none:
            return None
        record_id = self._next_id.get(record_type, 0) + 1
        self._next_id[record_type] = record_id
        self._records[(record_type, record_id)] = deepcopy(record_data)
        return record_id

    def get_record(self, record_type, record_id):
        if self.read_fails:
            raise StorageError("simulated storage failure")
        data = self._records.get((record_type, record_id))
        if data is None:
            return None
        return {**deepcopy(data), "record_id": record_id}

    def get_all_records(self, record_type):
        if self.read_fails:
            raise StorageError("simulated storage failure")
        ids = sorted(k[1] for k in self._records if k[0] == record_type)
        return [self.get_record(record_type, i) for i in ids]

    def update_record(self, record_type, record_id, record_data):
        if self.update_fails:
            raise StorageError("simulated storage failure")
        if (record_type, record_id) not in self._records:
            return False
        self._records[(record_type, record_id)] = deepcopy(record_data)
        return True

    def delete_record(self, record_type, record_id):
        if (record_type, record_id) not in self._records:
            return False
        if record_type == "recipe" and record_id in self.in_use_recipe_ids:
            return False
        del self._records[(record_type, record_id)]
        return True

@pytest.fixture
def storage():
    return FakeStorage()

@pytest.fixture
def service(storage):
    return rs.RecipeService(storage)

@pytest.mark.parametrize("error", [rs.InvalidRecipeError, rs.RecipeNotFoundError, rs.RecipeInUseError])
def test_domain_errors_share_a_service_error_base(error):
    assert issubclass(error, rs.ServiceError)

def test_storage_error_is_not_wrapped_in_a_service_error():
    assert not issubclass(StorageError, rs.ServiceError)
    
def test_create_saves_and_returns_recipe_with_id(service):
    saved = service.create(GOOD_RECIPE)

    assert saved["record_id"] == 1
    assert saved["name"] == "Pasta"
    assert saved["servings"] == 2

def test_create_ids_increase_across_recipes(service):
    first = service.create(GOOD_RECIPE)
    second = service.create({**GOOD_RECIPE, "name": "Stew"})

    assert second["record_id"] == first["record_id"] + 1

def test_create_does_not_mutate_the_callers_dict(service):
    recipe = deepcopy(GOOD_RECIPE)

    service.create(recipe)

    assert recipe == GOOD_RECIPE

@pytest.mark.parametrize("bad_recipe", [
    None,
    {},
    {**GOOD_RECIPE, "name": "   "},
    {**GOOD_RECIPE, "servings": -1},
    {**GOOD_RECIPE, "servings": True},
    {**GOOD_RECIPE, "ingredients": []},
    {**GOOD_RECIPE, "ingredients": [{"name": "Flour", "quantity": 0, "unit": "g"}]},
    {**GOOD_RECIPE, "ingredients": [{"name": "Flour", "quantity": 100}]},
])
def test_create_rejects_invalid_recipes_without_storing(service, storage, bad_recipe):
    with pytest.raises(rs.InvalidRecipeError):
        service.create(bad_recipe)

    assert storage.get_all_records("recipe") == []

NUTRITION = {"calories": 500, "protein": 20, "carbohydrates": 60, "fat": 10}
 
class VanishingStorage(FakeStorage):
    def update_record(self, record_type, record_id, record_data):
        return False
 
def stored_body(storage, recipe_id):
    return storage._records[("recipe", recipe_id)]
 
def new_recipe(service, **changes):
    return service.create({**GOOD_RECIPE, **changes})
 
def test_create_returns_what_was_stored(service, storage):
    saved = service.create(GOOD_RECIPE)
    assert storage.get_record("recipe", saved["record_id"]) == saved
 
def test_create_keeps_fields_beyond_the_required_ones(service):
    saved = service.create({**GOOD_RECIPE, "nutrition": NUTRITION})
    assert saved["nutrition"] == NUTRITION

def test_create_checks_the_recipe_before_it_touches_storage(service, storage):
    storage.save_fails = True
    with pytest.raises(rs.InvalidRecipeError):
        service.create({})
 
def test_create_lets_a_storage_failure_through_unchanged(service, storage):
    storage.save_fails = True
 
    with pytest.raises(StorageError):
        service.create(GOOD_RECIPE)
 
    assert storage.get_all_records("recipe") == []
    
def test_create_decision_storage_returning_no_id_is_an_invalid_recipe(service, storage):
    storage.save_returns_none = True
 
    with pytest.raises(rs.InvalidRecipeError):
        service.create(GOOD_RECIPE)

def test_get_returns_the_saved_recipe_with_its_id(service):
    saved = service.create(GOOD_RECIPE)
 
    assert service.get(saved["record_id"]) == saved

def test_get_finds_each_recipe_by_its_own_id(service):
    pasta = new_recipe(service, name="Pasta")
    stew = new_recipe(service, name="Stew")
 
    assert service.get(pasta["record_id"])["name"] == "Pasta"
    assert service.get(stew["record_id"])["name"] == "Stew"

def test_get_raises_not_found_for_an_unknown_id(service):
    with pytest.raises(rs.RecipeNotFoundError):
        service.get(99)
 
def test_get_does_not_find_a_recipe_by_the_id_of_another_record_type(service, storage):
    storage.save_record("meal_plan", {"weekStart": "2026-11-16", "meals": []})
 
    with pytest.raises(rs.RecipeNotFoundError):
        service.get(1)
 
def test_get_lets_a_storage_failure_through_unchanged(service, storage):
    service.create(GOOD_RECIPE)
    storage.read_fails = True
 
    with pytest.raises(StorageError):
        service.get(1)
    
def test_get_all_is_an_empty_list_when_nothing_is_saved(service):
    assert service.get_all() == []
 
def test_get_all_returns_every_recipe_in_id_order(service):
    saved = [new_recipe(service, name=name) for name in ("Pasta", "Stew", "Soup")]
 
    assert service.get_all() == saved
    assert [r["record_id"] for r in service.get_all()] == [1, 2, 3]
 
def test_get_all_returns_a_list(service):
    new_recipe(service)
 
    assert isinstance(service.get_all(), list)
 
def test_get_all_lets_a_storage_failure_through_unchanged(service, storage):
    storage.read_fails = True
 
    with pytest.raises(StorageError):
        service.get_all()

def test_update_replaces_the_edited_fields_and_returns_the_recipe(service, storage):
    saved = service.create(GOOD_RECIPE)
 
    updated = service.update(
        saved["record_id"], {**GOOD_RECIPE, "name": "Stew", "servings": 4}
    )
 
    assert updated["record_id"] == saved["record_id"]
    assert updated["name"] == "Stew"
    assert updated["servings"] == 4
    assert storage.get_record("recipe", saved["record_id"]) == updated
 
def test_update_decision_keeps_fields_the_edit_form_does_not_send(service):
    saved = service.create({**GOOD_RECIPE, "nutrition": NUTRITION})
 
    updated = service.update(saved["record_id"], {**GOOD_RECIPE, "name": "Stew"})
 
    assert updated["nutrition"] == NUTRITION

def test_update_does_not_write_the_record_id_into_the_stored_data(service, storage):
    saved = service.create(GOOD_RECIPE)
 
    service.update(saved["record_id"], {**GOOD_RECIPE, "name": "Stew"})
 
    assert "record_id" not in stored_body(storage, saved["record_id"])
 
def test_update_does_not_change_which_recipes_exist(service):
    first = new_recipe(service, name="Pasta")
    new_recipe(service, name="Stew")
 
    service.update(first["record_id"], {**GOOD_RECIPE, "name": "Better pasta"})
 
    assert [r["record_id"] for r in service.get_all()] == [1, 2]
    assert service.get(2)["name"] == "Stew"
 
def test_update_does_not_mutate_the_callers_dict(service):
    saved = service.create(GOOD_RECIPE)
    edit = {**GOOD_RECIPE, "name": "Stew"}
    before = deepcopy(edit)
 
    service.update(saved["record_id"], edit)
 
    assert edit == before

@pytest.mark.parametrize("bad_recipe", [
    None,
    {},
    {**GOOD_RECIPE, "name": ""},
    {**GOOD_RECIPE, "servings": 0},
    {**GOOD_RECIPE, "ingredients": []},
])
def test_update_rejects_invalid_recipes_and_leaves_the_stored_one_alone(
    service, bad_recipe
):
    saved = service.create(GOOD_RECIPE)
 
    with pytest.raises(rs.InvalidRecipeError):
        service.update(saved["record_id"], bad_recipe)
 
    assert service.get(saved["record_id"]) == saved
 
def test_update_decision_checks_the_recipe_before_looking_it_up(service):
    with pytest.raises(rs.InvalidRecipeError):
        service.update(99, {})
 
def test_update_raises_not_found_for_an_unknown_id_and_creates_nothing(service):
    with pytest.raises(rs.RecipeNotFoundError):
        service.update(99, GOOD_RECIPE)
 
    assert service.get_all() == []
 
def test_update_raises_not_found_when_the_recipe_vanishes_during_the_update():
    storage = VanishingStorage()
    service = rs.RecipeService(storage)
    saved = service.create(GOOD_RECIPE)
 
    with pytest.raises(rs.RecipeNotFoundError):
        service.update(saved["record_id"], {**GOOD_RECIPE, "name": "Stew"})
 
def test_update_lets_a_storage_failure_through_and_keeps_the_old_recipe(
    service, storage
):
    saved = service.create(GOOD_RECIPE)
    storage.update_fails = True
 
    with pytest.raises(StorageError):
        service.update(saved["record_id"], {**GOOD_RECIPE, "name": "Stew"})
 
    storage.update_fails = False
    assert service.get(saved["record_id"]) == saved
 
def test_update_lets_a_read_failure_through_unchanged(service, storage):
    saved = service.create(GOOD_RECIPE)
    storage.read_fails = True
 
    with pytest.raises(StorageError):
        service.update(saved["record_id"], GOOD_RECIPE)
 
def test_delete_removes_the_recipe(service):
    saved = service.create(GOOD_RECIPE)
 
    service.delete(saved["record_id"])
 
    assert service.get_all() == []
    with pytest.raises(rs.RecipeNotFoundError):
        service.get(saved["record_id"])
 
def test_delete_removes_only_the_chosen_recipe(service):
    first = new_recipe(service, name="Pasta")
    second = new_recipe(service, name="Stew")
 
    service.delete(first["record_id"])
 
    assert service.get_all() == [second]
 
def test_delete_raises_not_found_for_an_unknown_id(service):
    with pytest.raises(rs.RecipeNotFoundError):
        service.delete(99)
 
def test_delete_twice_raises_not_found_the_second_time(service):
    saved = service.create(GOOD_RECIPE)
    service.delete(saved["record_id"])
 
    with pytest.raises(rs.RecipeNotFoundError):
        service.delete(saved["record_id"])
 
def test_delete_refuses_a_recipe_that_a_meal_plan_uses(service, storage):
    saved = service.create(GOOD_RECIPE)
    storage.in_use_recipe_ids = frozenset({saved["record_id"]})
 
    with pytest.raises(rs.RecipeInUseError):
        service.delete(saved["record_id"])
 
    assert service.get(saved["record_id"]) == saved
 
def test_delete_in_use_blocks_only_that_recipe(service, storage):
    used = new_recipe(service, name="Pasta")
    unused = new_recipe(service, name="Stew")
    storage.in_use_recipe_ids = frozenset({used["record_id"]})
 
    service.delete(unused["record_id"])
 
    assert service.get_all() == [used]
 
def test_delete_lets_a_storage_failure_through_unchanged(service, storage):
    saved = service.create(GOOD_RECIPE)
    storage.read_fails = True
 
    with pytest.raises(StorageError):
        service.delete(saved["record_id"])

def make_validator(answer):
    validator = Mock()
    validator.validate_recipe.return_value = answer
    return validator
 
def test_create_asks_the_validator_about_the_recipe(storage):
    validator = make_validator(True)
 
    rs.RecipeService(storage, validator).create(GOOD_RECIPE)
 
    validator.validate_recipe.assert_called_once_with(GOOD_RECIPE)
 
def test_create_rejects_what_the_validator_rejects_without_storing(storage):
    service = rs.RecipeService(storage, make_validator(False))
 
    with pytest.raises(rs.InvalidRecipeError):
        service.create(GOOD_RECIPE)
 
    assert storage.get_all_records("recipe") == []
 
def test_a_given_validator_replaces_the_built_in_rules(storage):
    service = rs.RecipeService(storage, make_validator(True))
 
    saved = service.create({"name": "Not a full recipe"})
 
    assert saved["name"] == "Not a full recipe"
 
def test_update_asks_the_validator_and_rejects_what_it_rejects(storage):
    service = rs.RecipeService(storage)
    saved = service.create(GOOD_RECIPE)
    strict = make_validator(False)
 
    with pytest.raises(rs.InvalidRecipeError):
        rs.RecipeService(storage, strict).update(saved["record_id"], GOOD_RECIPE)
 
    strict.validate_recipe.assert_called_once_with(GOOD_RECIPE)
    assert service.get(saved["record_id"]) == saved

def test_every_service_error_carries_a_message(service, storage):
    saved = service.create(GOOD_RECIPE)
    storage.in_use_recipe_ids = frozenset({saved["record_id"]})
    attempts = [
        lambda: service.create({}),
        lambda: service.get(99),
        lambda: service.delete(saved["record_id"]),
    ]
 
    for attempt in attempts:
        with pytest.raises(rs.ServiceError) as raised:
            attempt()
        assert str(raised.value).strip()
 