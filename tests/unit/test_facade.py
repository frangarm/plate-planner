from copy import deepcopy

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