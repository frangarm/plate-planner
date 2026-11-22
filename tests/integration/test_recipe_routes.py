import pytest
from plateplanner.ui import app as app_module
from plateplanner.ui import grocery_api, meal_api

WEEK_START = "2026-11-16"
MEAL_DATE = "2026-11-17"
NUTRITION = {"calories": 500, "protein": 20, "carbohydrates": 60, "fat": 10}

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client that uses an empty temporary database."""
    database_path = tmp_path / "recipe_routes_test.db"
    for module in (app_module, meal_api, grocery_api):
        monkeypatch.setattr(module, "DATABASE_PATH", database_path)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()

@pytest.fixture
def broken_client(tmp_path, monkeypatch):
    """Flask test client whose database file cannot be opened."""
    missing = tmp_path / "missing_folder" / "recipes.db"
    for module in (app_module, meal_api, grocery_api):
        monkeypatch.setattr(module, "DATABASE_PATH", missing)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()

def recipe_data(name="Rice Bowl", servings=2, **extra):
    """Return a valid recipe as the recipe form sends it."""
    return {
        "name": name,
        "servings": servings,
        "ingredients": [{"name": "Rice", "quantity": 1, "unit": "cup"}],
        **extra,
    }

def save(client, **kwargs):
    """Save a recipe through the API and return the saved recipe."""
    response = client.post("/api/recipes", json=recipe_data(**kwargs))
    assert response.status_code == 201
    return response.get_json()["recipe"]

def use_in_plan(client, recipe_id):
    """Create a weekly plan with one meal that uses the recipe."""
    plan = client.post("/api/meal-plans", json={"weekStart": WEEK_START})
    assert plan.status_code == 201
    plan_id = plan.get_json()["record_id"]
    meal = client.post(f"/api/meal-plans/{plan_id}/meals", json={
        "date": MEAL_DATE, "mealSlot": "dinner",
        "recipeId": recipe_id, "servings": 2,
    })
    assert meal.status_code == 200
    return plan_id

def error_of(response):
    return response.get_json()["error"]

def test_i11_get_recipes_is_an_empty_list_at_first(client):
    response = client.get("/api/recipes")

    assert response.status_code == 200
    assert response.get_json() == []

def test_i11_get_recipes_lists_every_saved_recipe_in_id_order(client):
    saved = [save(client, name=name) for name in ("Rice Bowl", "Stew", "Soup")]

    response = client.get("/api/recipes")

    assert response.status_code == 200
    assert response.get_json() == saved
    assert [r["record_id"] for r in response.get_json()] == [1, 2, 3]

def test_i11_post_recipe_saves_it_and_returns_201(client):
    response = client.post("/api/recipes", json=recipe_data())
    body = response.get_json()

    assert response.status_code == 201
    assert body["message"] == "Recipe saved successfully."
    assert body["recipe"] == {
        "record_id": 1, "name": "Rice Bowl", "servings": 2,
        "ingredients": [{"name": "Rice", "quantity": 1, "unit": "cup"}],
    }

def test_i11_post_recipe_can_be_read_back_from_the_list(client):
    saved = save(client)

    assert client.get("/api/recipes").get_json() == [saved]

def test_i11_post_recipe_keeps_fields_beyond_the_required_ones(client):
    saved = save(client, nutrition=NUTRITION)

    assert saved["nutrition"] == NUTRITION

def test_i11_post_recipe_gives_each_recipe_its_own_id(client):
    first = save(client, name="Rice Bowl")
    second = save(client, name="Stew")

    assert second["record_id"] == first["record_id"] + 1

def test_i11_post_recipe_needs_a_json_request(client):
    response = client.post("/api/recipes", data="name=Rice Bowl")

    assert response.status_code == 400
    assert error_of(response) == "Recipe data must be sent as JSON."
    assert client.get("/api/recipes").get_json() == []

@pytest.mark.parametrize("bad_recipe", [
    {},
    [],
    "Rice Bowl",
    {**recipe_data(), "name": ""},
    {**recipe_data(), "name": "   "},
    {**recipe_data(), "servings": 0},
    {**recipe_data(), "servings": -1},
    {**recipe_data(), "servings": True},
    {**recipe_data(), "ingredients": []},
    {**recipe_data(), "ingredients": [{"name": "Rice", "quantity": 0, "unit": "cup"}]},
    {**recipe_data(), "ingredients": [{"name": "Rice", "quantity": 1}]},
])
def test_i11_post_recipe_rejects_an_invalid_recipe_and_saves_nothing(client, bad_recipe):
    response = client.post("/api/recipes", json=bad_recipe)

    assert response.status_code == 400
    assert error_of(response) == "Invalid recipe information."
    assert client.get("/api/recipes").get_json() == []

def test_i11_post_recipe_rejects_a_json_null_body(client):
    # json=None in the test client sends no body at all, so send the text null.
    response = client.post("/api/recipes", data="null", content_type="application/json")

    assert response.status_code == 400
    assert error_of(response) == "Invalid recipe information."

def test_i12_put_recipe_changes_the_edited_fields(client):
    saved = save(client)

    response = client.put(
        f"/api/recipes/{saved['record_id']}", json=recipe_data(name="Better Bowl", servings=4)
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["message"] == "Recipe updated."
    assert body["recipe"]["record_id"] == saved["record_id"]
    assert body["recipe"]["name"] == "Better Bowl"
    assert body["recipe"]["servings"] == 4

def test_i12_put_recipe_is_saved(client):
    saved = save(client)

    client.put(f"/api/recipes/{saved['record_id']}", json=recipe_data(name="Better Bowl"))

    assert client.get("/api/recipes").get_json()[0]["name"] == "Better Bowl"

def test_i12_put_recipe_keeps_the_nutrition_the_recipe_form_does_not_send(client):
    saved = save(client, nutrition=NUTRITION)

    response = client.put(f"/api/recipes/{saved['record_id']}", json=recipe_data(name="Better Bowl"))

    assert response.get_json()["recipe"]["nutrition"] == NUTRITION
    assert client.get("/api/recipes").get_json()[0]["nutrition"] == NUTRITION

def test_i12_put_recipe_changes_only_the_chosen_recipe(client):
    first = save(client, name="Rice Bowl")
    second = save(client, name="Stew")

    client.put(f"/api/recipes/{first['record_id']}", json=recipe_data(name="Better Bowl"))

    assert client.get("/api/recipes").get_json()[1] == second

@pytest.mark.parametrize("bad_recipe", [
    None,
    {},
    {**recipe_data(), "name": ""},
    {**recipe_data(), "servings": 0},
    {**recipe_data(), "ingredients": []},
])
def test_i12_put_recipe_rejects_an_invalid_recipe_and_keeps_the_saved_one(client, bad_recipe):
    saved = save(client)

    response = client.put(f"/api/recipes/{saved['record_id']}", json=bad_recipe)

    assert response.status_code == 400
    assert error_of(response) == "Invalid recipe information."
    assert client.get("/api/recipes").get_json() == [saved]

def test_i12_put_recipe_reports_an_invalid_recipe_before_a_missing_one(client):
    response = client.put("/api/recipes/99", json={})

    assert response.status_code == 400
    assert error_of(response) == "Invalid recipe information."

def test_i12_put_unknown_recipe_is_404_and_creates_nothing(client):
    response = client.put("/api/recipes/99", json=recipe_data())

    assert response.status_code == 404
    assert error_of(response) == "Recipe not found."
    assert client.get("/api/recipes").get_json() == []

def test_i12_put_recipe_id_zero_is_rejected(client):
    response = client.put("/api/recipes/0", json=recipe_data())

    assert response.status_code == 400
    assert error_of(response) == "Invalid recipe ID."

def test_i12_delete_recipe_removes_it(client):
    saved = save(client)

    response = client.delete(f"/api/recipes/{saved['record_id']}")

    assert response.status_code == 200
    assert response.get_json() == {"message": "Recipe deleted."}
    assert client.get("/api/recipes").get_json() == []

def test_i12_delete_recipe_removes_only_the_chosen_recipe(client):
    first = save(client, name="Rice Bowl")
    second = save(client, name="Stew")

    client.delete(f"/api/recipes/{first['record_id']}")

    assert client.get("/api/recipes").get_json() == [second]

def test_i12_delete_unknown_recipe_is_404(client):
    response = client.delete("/api/recipes/99")

    assert response.status_code == 404
    assert error_of(response) == "Recipe not found."

def test_i12_delete_the_same_recipe_twice_is_404_the_second_time(client):
    saved = save(client)
    assert client.delete(f"/api/recipes/{saved['record_id']}").status_code == 200

    response = client.delete(f"/api/recipes/{saved['record_id']}")

    assert response.status_code == 404
    assert error_of(response) == "Recipe not found."

def test_i12_delete_recipe_id_zero_is_rejected(client):
    response = client.delete("/api/recipes/0")

    assert response.status_code == 400
    assert error_of(response) == "Invalid recipe ID."

def test_i12_delete_recipe_used_in_a_meal_plan_is_409_and_keeps_it(client):
    saved = save(client)
    use_in_plan(client, saved["record_id"])

    response = client.delete(f"/api/recipes/{saved['record_id']}")

    assert response.status_code == 409
    assert error_of(response) == "This recipe is used in a saved meal plan."
    assert client.get("/api/recipes").get_json() == [saved]

def test_i12_delete_recipe_used_in_a_plan_leaves_the_plan_unchanged(client):
    saved = save(client)
    plan_id = use_in_plan(client, saved["record_id"])
    before = client.get(f"/api/meal-plans/{plan_id}").get_json()

    client.delete(f"/api/recipes/{saved['record_id']}")

    assert client.get(f"/api/meal-plans/{plan_id}").get_json() == before

def test_i12_delete_recipe_is_allowed_once_the_meal_is_removed_from_the_plan(client):
    saved = save(client)
    plan_id = use_in_plan(client, saved["record_id"])
    meal = client.get(f"/api/meal-plans/{plan_id}").get_json()["meals"][0]
    assert client.delete(f"/api/recipes/{saved['record_id']}").status_code == 409

    client.delete(f"/api/meal-plans/{plan_id}/meals/0", json={"original": meal})

    assert client.delete(f"/api/recipes/{saved['record_id']}").status_code == 200

def test_i12_delete_recipe_not_used_by_a_plan_is_allowed_while_another_is_protected(client):
    used = save(client, name="Rice Bowl")
    spare = save(client, name="Spare Bowl")
    use_in_plan(client, used["record_id"])

    assert client.delete(f"/api/recipes/{spare['record_id']}").status_code == 200
    assert client.delete(f"/api/recipes/{used['record_id']}").status_code == 409
    assert client.get("/api/recipes").get_json() == [used]

def test_i12_a_recipe_can_be_created_listed_edited_and_deleted(client):
    saved = save(client, nutrition=NUTRITION)
    recipe_id = saved["record_id"]
    assert client.get("/api/recipes").get_json() == [saved]

    edited = client.put(f"/api/recipes/{recipe_id}", json=recipe_data(name="Better Bowl"))
    assert edited.status_code == 200
    assert client.get("/api/recipes").get_json()[0]["name"] == "Better Bowl"
    assert client.get("/api/recipes").get_json()[0]["nutrition"] == NUTRITION

    assert client.delete(f"/api/recipes/{recipe_id}").status_code == 200
    assert client.get("/api/recipes").get_json() == []

def test_i13_get_recipes_reports_a_database_failure(broken_client):
    response = broken_client.get("/api/recipes")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unable to retrieve recipes."}

def test_i13_post_recipe_reports_a_database_failure(broken_client):
    response = broken_client.post("/api/recipes", json=recipe_data())

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unable to save recipe."}

@pytest.mark.parametrize("method", ["put", "delete"])
def test_i13_changing_a_recipe_reports_a_database_failure(broken_client, method):
    response = getattr(broken_client, method)("/api/recipes/1", json=recipe_data())

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unable to change recipe."}

def test_i13_a_database_failure_message_has_no_technical_details(broken_client):
    text = broken_client.get("/api/recipes").get_data(as_text=True)

    assert "missing_folder" not in text
    assert "Traceback" not in text
    assert "sqlite" not in text.lower()

def test_i13_every_recipe_request_closes_the_database_it_opened(client, monkeypatch):
    opened, closed = [], []
    real_class = app_module.DataStorageManager

    class WatchedStorage(real_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            opened.append(self)

        def close(self):
            closed.append(self)
            super().close()

    monkeypatch.setattr(app_module, "DataStorageManager", WatchedStorage)
    saved = save(client)

    client.get("/api/recipes")                                              # success
    client.post("/api/recipes", json={})                                    # invalid recipe
    client.post("/api/recipes", data="not json")                            # not JSON
    client.put("/api/recipes/99", json=recipe_data())                       # unknown recipe
    client.put("/api/recipes/0", json=recipe_data())                        # invalid ID
    client.delete(f"/api/recipes/{saved['record_id']}")                     # success
    client.delete(f"/api/recipes/{saved['record_id']}")                     # already deleted

    assert opened
    assert len(closed) == len(opened)