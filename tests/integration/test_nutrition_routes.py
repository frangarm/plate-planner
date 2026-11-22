import pytest
from plateplanner.ui import app as app_module
from plateplanner.ui import grocery_api, meal_api

WEEK_START = "2026-11-16"
TUESDAY = "2026-11-17"
WEDNESDAY = "2026-11-18"
NUTRITION = {"calories": 500, "protein": 20, "carbohydrates": 60, "fat": 10}
WEEKLY_TARGETS = {"calories": 14000, "protein": 350, "carbohydrates": 1750, "fat": 490}
DAILY_TARGETS = {"calories": 2000, "protein": 50, "carbohydrates": 250, "fat": 70}
BAD_REQUEST = "Select a valid plan and analysis period."

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client that uses an empty temporary database."""
    database_path = tmp_path / "nutrition_routes_test.db"
    for module in (app_module, meal_api, grocery_api):
        monkeypatch.setattr(module, "DATABASE_PATH", database_path)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()

@pytest.fixture
def broken_client(tmp_path, monkeypatch):
    """Flask test client whose database file cannot be opened."""
    missing = tmp_path / "missing_folder" / "nutrition.db"
    for module in (app_module, meal_api, grocery_api):
        monkeypatch.setattr(module, "DATABASE_PATH", missing)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()

def save_recipe(client, nutrition=NUTRITION, servings=2, name="Rice Bowl"):
    """Save a recipe (500 calories per 2 servings by default); return its ID."""
    data = {
        "name": name,
        "servings": servings,
        "ingredients": [{"name": "Rice", "quantity": 1, "unit": "cup"}],
    }
    if nutrition is not None:
        data["nutrition"] = nutrition
    response = client.post("/api/recipes", json=data)
    assert response.status_code == 201
    return response.get_json()["recipe"]["record_id"]

def new_plan(client):
    response = client.post("/api/meal-plans", json={"weekStart": WEEK_START})
    assert response.status_code == 201
    return response.get_json()["record_id"]

def add_meal(client, plan_id, recipe_id, date=TUESDAY, slot="dinner", servings=2):
    response = client.post(f"/api/meal-plans/{plan_id}/meals", json={
        "date": date, "mealSlot": slot,
        "recipeId": recipe_id, "servings": servings,
    })
    assert response.status_code == 200

def plan_with_meals(client, meals, **recipe_kwargs):
    """Create a plan holding (date, slot, servings) meals of one recipe."""
    recipe_id = save_recipe(client, **recipe_kwargs)
    plan_id = new_plan(client)
    for date, slot, servings in meals:
        add_meal(client, plan_id, recipe_id, date, slot, servings)
    return plan_id

def analysis(client, plan_id, period=None):
    url = f"/api/meal-plans/{plan_id}/nutrition"
    if period is not None:
        url += f"?period={period}"
    return client.get(url)

def error_of(response):
    return response.get_json()["error"]

def test_i17_weekly_is_the_default_period(client):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 2)])

    response = analysis(client, plan_id)

    assert response.status_code == 200
    assert response.get_json()["period"] == "weekly"

def test_i17_weekly_result_has_the_totals_targets_and_one_comparison(client):
    plan_id = plan_with_meals(
        client, [(TUESDAY, "dinner", 2), (TUESDAY, "lunch", 4), (WEDNESDAY, "dinner", 1)]
    )

    response = analysis(client, plan_id, "weekly")

    assert response.status_code == 200
    assert response.get_json() == {
        "period": "weekly",
        "incomplete": False,
        "totals": {"calories": 1750, "protein": 70, "carbohydrates": 210, "fat": 35},
        "targets": WEEKLY_TARGETS,
        "comparisons": {
            "Weekly total": {
                "calories": "Deficit", "protein": "Deficit",
                "carbohydrates": "Deficit", "fat": "Deficit",
            },
        },
    }

def test_i17_daily_result_has_totals_and_comparison_for_each_day_with_meals(client):
    plan_id = plan_with_meals(
        client, [(TUESDAY, "dinner", 2), (TUESDAY, "lunch", 4), (WEDNESDAY, "dinner", 1)]
    )

    response = analysis(client, plan_id, "daily")

    body = response.get_json()
    assert response.status_code == 200
    assert body["period"] == "daily"
    assert body["incomplete"] is False
    assert body["targets"] == DAILY_TARGETS
    assert body["totals"] == {
        TUESDAY: {"calories": 1500, "protein": 60, "carbohydrates": 180, "fat": 30},
        WEDNESDAY: {"calories": 250, "protein": 10, "carbohydrates": 30, "fat": 5},
    }
    assert body["comparisons"] == {
        TUESDAY: {
            "calories": "Deficit", "protein": "Excess",
            "carbohydrates": "Deficit", "fat": "Deficit",
        },
        WEDNESDAY: {
            "calories": "Deficit", "protein": "Deficit",
            "carbohydrates": "Deficit", "fat": "Deficit",
        },
    }

@pytest.mark.parametrize("servings, status", [
    (1, "Deficit"),
    (8, "Within Target"),  
    (9, "Excess"),
])
def test_i17_daily_calories_are_compared_with_the_daily_target(client, servings, status):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", servings)])

    body = analysis(client, plan_id, "daily").get_json()

    assert body["comparisons"][TUESDAY]["calories"] == status

@pytest.mark.parametrize("servings, status", [
    (55, "Deficit"),
    (56, "Within Target"),   
    (57, "Excess"),
])
def test_i17_weekly_calories_are_compared_with_the_weekly_target(client, servings, status):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", servings)])

    body = analysis(client, plan_id, "weekly").get_json()

    assert body["comparisons"]["Weekly total"]["calories"] == status

def test_i17_an_empty_plan_has_zero_totals_and_no_daily_results(client):
    plan_id = new_plan(client)

    weekly = analysis(client, plan_id, "weekly").get_json()
    daily = analysis(client, plan_id, "daily").get_json()

    assert weekly["totals"] == {"calories": 0, "protein": 0, "carbohydrates": 0, "fat": 0}
    assert set(weekly["comparisons"]) == {"Weekly total"}
    assert daily["totals"] == {}
    assert daily["comparisons"] == {}

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_i17_a_recipe_without_nutrition_makes_the_result_incomplete(client, period):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 2)], nutrition=None)

    response = analysis(client, plan_id, period)

    body = response.get_json()
    assert response.status_code == 200
    assert body["incomplete"] is True
    assert body["comparisons"] == {}
    assert body["targets"] == (WEEKLY_TARGETS if period == "weekly" else DAILY_TARGETS)

def test_i17_each_plan_is_analyzed_on_its_own(client):
    recipe_id = save_recipe(client)
    first, second = new_plan(client), new_plan(client)
    add_meal(client, first, recipe_id, servings=2)
    add_meal(client, second, recipe_id, servings=6)

    first_totals = analysis(client, first).get_json()["totals"]
    second_totals = analysis(client, second).get_json()["totals"]

    assert first_totals["calories"] == 500
    assert second_totals["calories"] == 1500

def test_i17_analyzing_does_not_change_the_saved_data(client):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 2)])
    plans_before = client.get("/api/meal-plans").get_json()
    recipes_before = client.get("/api/recipes").get_json()

    analysis(client, plan_id, "weekly")
    analysis(client, plan_id, "daily")

    assert client.get("/api/meal-plans").get_json() == plans_before
    assert client.get("/api/recipes").get_json() == recipes_before

def test_i17_the_same_request_gives_the_same_answer_twice(client):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 3)])

    assert analysis(client, plan_id, "daily").get_json() == analysis(client, plan_id, "daily").get_json()

def test_i17_a_new_meal_shows_up_in_the_next_analysis(client):
    recipe_id = save_recipe(client)
    plan_id = new_plan(client)
    add_meal(client, plan_id, recipe_id, servings=2)
    before = analysis(client, plan_id).get_json()["totals"]["calories"]

    add_meal(client, plan_id, recipe_id, date=WEDNESDAY, servings=2)

    assert before == 500
    assert analysis(client, plan_id).get_json()["totals"]["calories"] == 1000

def test_i18_an_unknown_plan_is_404(client):
    response = analysis(client, 999)

    assert response.status_code == 404
    assert response.get_json() == {"error": "Meal plan not found."}

def test_i18_a_recipe_id_is_not_taken_for_a_plan_id(client):
    recipe_id = save_recipe(client) 

    response = analysis(client, recipe_id)

    assert response.status_code == 404
    assert error_of(response) == "Meal plan not found."

def test_i18_plan_id_0_is_400(client):
    response = analysis(client, 0)

    assert response.status_code == 400
    assert response.get_json() == {"error": BAD_REQUEST}

def test_i18_a_negative_plan_id_is_not_found(client):
    assert analysis(client, -1).status_code == 404

@pytest.mark.parametrize("period", ["monthly", "Weekly", "DAILY", "", "week", "1"])
def test_i18_an_unknown_period_is_400(client, period):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 2)])

    response = analysis(client, plan_id, period)

    assert response.status_code == 400
    assert response.get_json() == {"error": BAD_REQUEST}

def test_i18_the_period_is_checked_before_the_plan_is_looked_up(client):
    response = analysis(client, 999, "monthly")

    assert response.status_code == 400
    assert error_of(response) == BAD_REQUEST

def test_i18_the_page_can_tell_every_failure_from_a_result(client):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 2)])

    failures = [analysis(client, 999), analysis(client, 0), analysis(client, plan_id, "monthly")]

    for response in failures:
        assert set(response.get_json()) == {"error"}
    assert "error" not in analysis(client, plan_id).get_json()

@pytest.mark.parametrize("period", [None, "weekly", "daily"])
def test_i18_a_database_failure_is_500_with_a_fixed_message(broken_client, period):
    response = analysis(broken_client, 1, period)

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unable to calculate nutrition."}

def test_i18_the_database_is_not_changed_by_a_failed_request(client):
    plan_id = plan_with_meals(client, [(TUESDAY, "dinner", 2)])
    before = client.get("/api/meal-plans").get_json()

    analysis(client, 999)
    analysis(client, plan_id, "monthly")

    assert client.get("/api/meal-plans").get_json() == before