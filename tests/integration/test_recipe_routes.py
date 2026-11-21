"""Integration tests for RecipeService with a real SQLite database.

RecipeService, RecipeManager (validation) and DataStorageManager all run for
real; only the database file is temporary. The unit tests in
tests/unit/test_facade.py use a fake storage instead.

Each test_iNN_ test follows the steps of the test case with the same number in
the Test Plan Report (Section 5), so a step in the report matches a line here:

    I06  Recipe Service saves and retrieves a valid recipe
    I07  Recipe Service rejects a recipe with zero servings
    I08  Recipe Service protects a recipe used in a saved meal plan
    I09  Recipe Service edits a saved recipe
    I10  Recipe Service reports missing recipes and storage failures
"""

import pytest

from data.DataStorageManager import (
    RECORD_TYPE_MEAL_PLAN,
    RECORD_TYPE_RECIPE,
    DataStorageManager,
    StorageError,
)
import plateplanner.management.recipe.RecipeService as rs

RICE = {"name": "Rice", "quantity": 1, "unit": "cup"}
NUTRITION = {"calories": 500, "protein": 20, "carbohydrates": 60, "fat": 10}

def rice_bowl(**changes):
    """The Rice Bowl recipe: 2 servings and 1 cup of rice."""
    return {"name": "Rice Bowl", "servings": 2, "ingredients": [dict(RICE)], **changes}

@pytest.fixture
def database_path(tmp_path):
    return str(tmp_path / "recipe_service_test.db")

@pytest.fixture
def storage(database_path):
    database = DataStorageManager(database_path)
    yield database
    database.close()

@pytest.fixture
def service(storage):
    return rs.RecipeService(storage)

def reopen(database_path):
    """Open the same database file again, as after the app is restarted."""
    database = DataStorageManager(database_path)
    return database, rs.RecipeService(database)

def weekly_plan_using(recipe_id):
    """A weekly meal plan with one dinner that uses the recipe."""
    return {
        "weekStart": "2026-11-16",
        "meals": [{
            "date": "2026-11-17", "mealSlot": "dinner",
            "recipe_id": recipe_id, "servings": 2,
        }],
    }

def test_i06_service_saves_and_retrieves_a_valid_recipe(service, storage, database_path):
    # Step 1: the starting state is empty.
    assert service.get_all() == []

    # Step 2: a valid recipe saves and comes back with a positive record_id.
    created = service.create(rice_bowl())
    assert created["record_id"] > 0

    # Step 3: get() returns the saved information.
    retrieved = service.get(created["record_id"])
    assert retrieved["name"] == "Rice Bowl"
    assert retrieved["servings"] == 2
    assert retrieved["ingredients"] == [{"name": "Rice", "quantity": 1, "unit": "cup"}]

    # Step 4: the service and Data Storage agree.
    assert service.get_all() == [storage.get_record(RECORD_TYPE_RECIPE, created["record_id"])]

    # Step 5: the recipe is still saved after the database is reopened.
    storage.close()
    reopened, reopened_service = reopen(database_path)
    try:
        assert reopened_service.get(created["record_id"]) == retrieved
    finally:
        reopened.close()

def test_i07_service_rejects_zero_servings_and_keeps_saved_recipes(service):
    saved_rice_bowl = service.create(rice_bowl())

    # Step 1: starting state is exactly the one valid recipe.
    assert service.get_all() == [saved_rice_bowl]

    # Step 2: zero servings is rejected and nothing is saved.
    with pytest.raises(rs.InvalidRecipeError):
        service.create(rice_bowl(name="Invalid Bowl", servings=0))

    # Step 3: rejection left the existing data alone.
    assert service.get_all() == [saved_rice_bowl]
    assert service.get(saved_rice_bowl["record_id"]) == saved_rice_bowl

    # Step 4: the corrected recipe is accepted with its own positive ID.
    corrected = service.create(rice_bowl(name="Invalid Bowl", servings=1))
    assert corrected["servings"] == 1
    assert corrected["record_id"] > 0
    assert corrected["record_id"] != saved_rice_bowl["record_id"]

    # Step 5: the final saved state.
    assert service.get(saved_rice_bowl["record_id"]) == saved_rice_bowl
    assert service.get(corrected["record_id"]) == corrected
    assert corrected["name"] == "Invalid Bowl"

def test_i08_service_protects_a_recipe_used_in_a_meal_plan(service, storage, database_path):
    rice = service.create(rice_bowl())
    spare = service.create(rice_bowl(name="Spare Bowl"))
    plan_id = storage.save_record(RECORD_TYPE_MEAL_PLAN, weekly_plan_using(rice["record_id"]))

    # Step 1: the recipe is referenced by the saved plan.
    plan = storage.get_record(RECORD_TYPE_MEAL_PLAN, plan_id)
    assert plan["meals"][0]["recipe_id"] == rice["record_id"]
    assert plan["meals"][0]["mealSlot"] == "dinner"

    # Step 2: deleting the referenced recipe is refused.
    with pytest.raises(rs.RecipeInUseError):
        service.delete(rice["record_id"])

    # Step 3: both records are unchanged.
    assert service.get(rice["record_id"]) == rice
    assert storage.get_record(RECORD_TYPE_MEAL_PLAN, plan_id) == plan

    # Step 4: the protected relationship is still there after reopening.
    storage.close()
    reopened, reopened_service = reopen(database_path)
    try:
        assert reopened_service.get(rice["record_id"]) == rice
        assert reopened.get_record(RECORD_TYPE_MEAL_PLAN, plan_id) == plan

        # Step 5: an unreferenced recipe can be deleted, and then it is gone.
        reopened_service.delete(spare["record_id"])
        with pytest.raises(rs.RecipeNotFoundError):
            reopened_service.get(spare["record_id"])
        assert reopened_service.get(rice["record_id"]) == rice
        assert reopened.get_record(RECORD_TYPE_MEAL_PLAN, plan_id) == plan
    finally:
        reopened.close()

def test_i09_service_edits_a_saved_recipe(service, database_path, storage):
    # Step 1: a recipe is saved with nutrition information, which the recipe
    # form does not send when the recipe is edited.
    created = service.create(rice_bowl(nutrition=NUTRITION))
    recipe_id = created["record_id"]

    # Step 2: edit the name, servings and ingredients, as the form does.
    edit = {
        "name": "Veggie Rice Bowl",
        "servings": 4,
        "ingredients": [dict(RICE), {"name": "Broccoli", "quantity": 200, "unit": "g"}],
    }
    updated = service.update(recipe_id, edit)
    assert updated["record_id"] == recipe_id
    assert updated["name"] == "Veggie Rice Bowl"
    assert updated["servings"] == 4
    assert len(updated["ingredients"]) == 2

    # Step 3: the saved recipe matches, and the nutrition was not lost.
    assert service.get(recipe_id) == updated
    assert updated["nutrition"] == NUTRITION

    # Step 4: an invalid edit is rejected and the saved recipe is unchanged.
    with pytest.raises(rs.InvalidRecipeError):
        service.update(recipe_id, {**edit, "servings": 0})
    assert service.get(recipe_id) == updated

    # Step 5: the edited recipe is still saved after reopening the database.
    storage.close()
    reopened, reopened_service = reopen(database_path)
    try:
        assert reopened_service.get(recipe_id) == updated
        assert reopened_service.get_all() == [updated]
    finally:
        reopened.close()

def test_i10_service_reports_missing_recipes_and_storage_failures(service, storage, database_path):
    saved = service.create(rice_bowl())

    # Step 1: an unknown ID is reported by get().
    with pytest.raises(rs.RecipeNotFoundError):
        service.get(99)

    # Step 2: update() of an unknown ID is reported and creates nothing.
    with pytest.raises(rs.RecipeNotFoundError):
        service.update(99, rice_bowl(name="Ghost"))
    assert service.get_all() == [saved]

    # Step 3: delete() of an unknown ID, or of a recipe already deleted, is reported.
    with pytest.raises(rs.RecipeNotFoundError):
        service.delete(99)
    service.delete(saved["record_id"])
    with pytest.raises(rs.RecipeNotFoundError):
        service.delete(saved["record_id"])

    # Step 4: when the database cannot be used, every method raises StorageError,
    # and it is not wrapped in a service error.
    storage.close()
    calls = [
        lambda: service.create(rice_bowl()),
        lambda: service.get(1),
        lambda: service.get_all(),
        lambda: service.update(1, rice_bowl()),
        lambda: service.delete(1),
    ]
    for call in calls:
        with pytest.raises(StorageError) as raised:
            call()
        assert not isinstance(raised.value, rs.ServiceError)

    # Step 5: the failures changed nothing that was saved.
    reopened, reopened_service = reopen(database_path)
    try:
        assert reopened_service.get_all() == []
    finally:
        reopened.close()

def test_real_storage_reads_missing_records_as_none_and_changes_nothing(storage):
    assert storage.get_record(RECORD_TYPE_RECIPE, 99) is None
    assert storage.update_record(RECORD_TYPE_RECIPE, 99, {"name": "x"}) is False
    assert storage.delete_record(RECORD_TYPE_RECIPE, 99) is False
    assert storage.get_all_records(RECORD_TYPE_RECIPE) == []

def test_real_storage_refuses_to_delete_a_recipe_a_plan_uses(storage):
    recipe_id = storage.save_record(RECORD_TYPE_RECIPE, rice_bowl())
    storage.save_record(RECORD_TYPE_MEAL_PLAN, weekly_plan_using(recipe_id))

    assert storage.delete_record(RECORD_TYPE_RECIPE, recipe_id) is False
    assert storage.get_record(RECORD_TYPE_RECIPE, recipe_id) is not None

@pytest.mark.parametrize("bad_id", [0, -1, True])
def test_real_storage_rejects_ids_below_one_with_value_error(storage, bad_id):
    # RecipeService does not check IDs itself, so a caller must not pass one
    # below 1. The recipe routes do this check (check_recipe_id in app.py).
    with pytest.raises(ValueError):
        storage.get_record(RECORD_TYPE_RECIPE, bad_id)