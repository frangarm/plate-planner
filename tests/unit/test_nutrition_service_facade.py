"""Unit tests for NutritionService written from contracts NS1 and NS2 of the SDD.

Every test cites the contract line it checks:

    pre     a pre-condition (@requires)
    post    a post-condition (@ensures)
    step    a step of the Algorithm Description

The tests use only what the contracts say. Where a contract leaves a value
open (the daily target numbers, for example) the test reads it from the result
instead of hard-coding it. NS1 and NS2 do not give a constructor, so the
service is built as NutritionService(storage, analyzer=None); that is the only
assumption about the interface besides analyze(plan_id, period="weekly").

Contract names used here: N1 is NutritionAnalyzer.calculate_nutrition(plan_id,
period) and N2 is NutritionAnalyzer.analyze_nutrition(totals, targets).
"""
from copy import deepcopy
from unittest.mock import Mock
import pytest
from data.DataStorageManager import StorageError
import plateplanner.meal.nutrition.NutritionService as ns
from test_recipe_service_facade import FakeStorage

NUTRIENTS = ("calories", "protein", "carbohydrates", "fat")
MONDAY, TUESDAY, WEDNESDAY = "2026-11-16", "2026-11-17", "2026-11-18"
PASTA = {"calories": 500, "protein": 20, "carbohydrates": 60, "fat": 10}

class CountingStorage(FakeStorage):
    def __init__(self):
        super().__init__()
        self.calls = []

    def get_record(self, record_type, record_id):
        self.calls.append((record_type, record_id))
        return super().get_record(record_type, record_id)

class ReadOnlyStorage(FakeStorage):
    def save_record(self, *args):
        raise AssertionError("the analysis must not write to storage")

    update_record = delete_record = save_record

def add_recipe(storage, nutrition=PASTA, servings=2):
    recipe = {"name": "Pasta", "servings": servings,
              "ingredients": [{"name": "Flour", "quantity": 300, "unit": "g"}]}
    if nutrition is not None:
        recipe["nutrition"] = nutrition
    return FakeStorage.save_record(storage, "recipe", recipe)

def meal(recipe_id, date=TUESDAY, servings=2):
    return {"date": date, "mealSlot": "dinner", "recipe_id": recipe_id, "servings": servings}

def add_plan(storage, meals):
    return FakeStorage.save_record(storage, "meal_plan", {"weekStart": MONDAY, "meals": meals})

def plan_of(storage, nutrition=PASTA, servings=2, planned=2):
    return add_plan(storage, [meal(add_recipe(storage, nutrition, servings), servings=planned)])

def mock_analyzer(totals, incomplete=False, statuses=None, period="weekly"):
    analyzer = Mock()
    analyzer.calculate_nutrition.return_value = {
        "period": period, "totals": totals, "incomplete": incomplete}
    analyzer.analyze_nutrition.return_value = statuses or {n: "Deficit" for n in NUTRIENTS}
    return analyzer

@pytest.fixture
def storage():
    return FakeStorage()

@pytest.fixture
def service(storage):
    return ns.NutritionService(storage)

def targets_of(service, storage, period):
    """The targets the service uses for a period, read from its own result."""
    return service.analyze(add_plan(storage, []), period)["targets"]

def test_ns1_pre_weekly_is_the_default_period(service, storage):
    plan_id = plan_of(storage)

    assert service.analyze(plan_id) == service.analyze(plan_id, "weekly")

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_post_result_contains_the_five_parts(service, storage, period):
    result = service.analyze(plan_of(storage), period)

    assert set(result) >= {"period", "totals", "incomplete", "targets", "comparisons"}

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_post_result_period_is_the_requested_period(service, storage, period):
    assert service.analyze(plan_of(storage), period)["period"] == period

def test_ns1_post_weekly_totals_are_one_set_for_the_whole_plan(service, storage):
    recipe_id = add_recipe(storage)
    plan_id = add_plan(storage, [meal(recipe_id, MONDAY), meal(recipe_id, TUESDAY, servings=1)])

    totals = service.analyze(plan_id, "weekly")["totals"]

    assert set(totals) == set(NUTRIENTS)  # nutrients, not dates
    assert totals == {"calories": 750, "protein": 30, "carbohydrates": 90, "fat": 15}

def test_ns1_post_weekly_targets_are_seven_times_the_daily_targets(service, storage):
    daily = targets_of(service, storage, "daily")
    weekly = targets_of(service, storage, "weekly")

    assert set(daily) == set(NUTRIENTS)
    assert weekly == {nutrient: 7 * target for nutrient, target in daily.items()}

def test_ns1_post_weekly_comparisons_have_one_entry_called_weekly_total(service, storage):
    comparisons = service.analyze(plan_of(storage), "weekly")["comparisons"]

    assert list(comparisons) == ["Weekly total"]

def test_ns1_post_daily_totals_have_one_set_for_each_date_that_has_meals(service, storage):
    recipe_id = add_recipe(storage)
    plan_id = add_plan(storage, [meal(recipe_id, MONDAY), meal(recipe_id, WEDNESDAY, servings=1)])

    totals = service.analyze(plan_id, "daily")["totals"]

    assert set(totals) == {MONDAY, WEDNESDAY}  # Tuesday has no meals
    assert totals[MONDAY] == PASTA
    assert totals[WEDNESDAY] == {n: v / 2 for n, v in PASTA.items()}

def test_ns1_post_daily_comparisons_have_one_entry_for_each_of_those_dates(service, storage):
    recipe_id = add_recipe(storage)
    plan_id = add_plan(storage, [meal(recipe_id, MONDAY), meal(recipe_id, WEDNESDAY)])

    comparisons = service.analyze(plan_id, "daily")["comparisons"]

    assert set(comparisons) == {MONDAY, WEDNESDAY}

def test_ns1_post_daily_targets_are_the_daily_targets(service, storage):
    result = service.analyze(plan_of(storage), "daily")

    assert result["targets"] == targets_of(service, storage, "daily")
    assert set(result["targets"]) == set(NUTRIENTS)

def test_ns1_post_a_day_with_two_meals_has_both_in_its_total(service, storage):
    recipe_id = add_recipe(storage)
    plan_id = add_plan(storage, [meal(recipe_id, MONDAY), meal(recipe_id, MONDAY)])

    assert service.analyze(plan_id, "daily")["totals"] == {
        MONDAY: {n: 2 * v for n, v in PASTA.items()}}

@pytest.mark.parametrize("period", ["weekly", "daily"])
@pytest.mark.parametrize("difference, label", [
    (-1, "Deficit"), (0, "Within Target"), (1, "Excess"),
])
def test_ns1_post_each_total_is_compared_with_its_target(service, storage, period, difference, label):
    targets = targets_of(service, storage, period)
    nutrition = {n: targets[n] + difference for n in NUTRIENTS}
    plan_id = plan_of(storage, nutrition, servings=1, planned=1)
    group = "Weekly total" if period == "weekly" else TUESDAY

    comparison = service.analyze(plan_id, period)["comparisons"][group]

    assert comparison == {n: label for n in NUTRIENTS}

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_post_every_nutrient_is_compared_on_its_own(service, storage, period):
    targets = targets_of(service, storage, period)
    nutrition = {"calories": targets["calories"] - 1, "protein": targets["protein"],
                 "carbohydrates": targets["carbohydrates"] + 1, "fat": targets["fat"]}
    plan_id = plan_of(storage, nutrition, servings=1, planned=1)
    group = "Weekly total" if period == "weekly" else TUESDAY

    comparison = service.analyze(plan_id, period)["comparisons"][group]

    assert comparison == {"calories": "Deficit", "protein": "Within Target",
                          "carbohydrates": "Excess", "fat": "Within Target"}

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_post_incomplete_data_gives_no_comparisons(service, storage, period):
    result = service.analyze(plan_of(storage, nutrition=None), period)

    assert result["incomplete"] is True
    assert result["comparisons"] == {}

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_post_incomplete_is_false_for_complete_data(service, storage, period):
    assert service.analyze(plan_of(storage), period)["incomplete"] is False

def test_ns1_step_incomplete_totals_from_n1_are_not_compared(storage):
    analyzer = mock_analyzer(PASTA, incomplete=True)

    result = ns.NutritionService(storage, analyzer).analyze(plan_of(storage), "weekly")

    analyzer.analyze_nutrition.assert_not_called()
    assert result["incomplete"] is True
    assert result["comparisons"] == {}

def test_ns1_post_a_plan_without_meals_has_all_weekly_totals_zero(service, storage):
    totals = service.analyze(add_plan(storage, []), "weekly")["totals"]

    assert totals == {n: 0 for n in NUTRIENTS}

def test_ns1_post_a_plan_without_meals_has_no_daily_groups(service, storage):
    result = service.analyze(add_plan(storage, []), "daily")

    assert result["totals"] == {}
    assert result["comparisons"] == {}

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_post_the_saved_records_are_unchanged(period):
    storage = ReadOnlyStorage()  # fails the test on any write
    plan_id = plan_of(storage)
    before = deepcopy(storage._records)

    ns.NutritionService(storage).analyze(plan_id, period)

    assert storage._records == before

def test_ns1_step_the_meal_plan_is_retrieved_from_storage_by_its_id():
    storage = CountingStorage()
    plan_id = plan_of(storage)
    storage.calls.clear()

    ns.NutritionService(storage, mock_analyzer(PASTA)).analyze(plan_id, "weekly")

    assert ("meal_plan", plan_id) in storage.calls

@pytest.mark.parametrize("period", ["weekly", "daily"])
def test_ns1_step_n1_is_asked_once_for_the_plan_and_period(storage, period):
    plan_id = plan_of(storage)
    analyzer = mock_analyzer({MONDAY: PASTA} if period == "daily" else PASTA, period=period)

    ns.NutritionService(storage, analyzer).analyze(plan_id, period)

    analyzer.calculate_nutrition.assert_called_once_with(plan_id, period)

def test_ns1_step_the_totals_from_n1_are_returned_unchanged(storage):
    totals = {"calories": 123, "protein": 4, "carbohydrates": 5, "fat": 6}

    result = ns.NutritionService(storage, mock_analyzer(totals)).analyze(plan_of(storage), "weekly")

    assert result["totals"] == totals

def test_ns1_step_weekly_totals_go_to_n2_once_as_one_group(storage):
    plan_id = plan_of(storage)
    analyzer = mock_analyzer(PASTA, statuses={n: "Excess" for n in NUTRIENTS})
    service = ns.NutritionService(storage, analyzer)

    result = service.analyze(plan_id, "weekly")

    analyzer.analyze_nutrition.assert_called_once()
    assert analyzer.analyze_nutrition.call_args.args[0] == PASTA
    assert result["comparisons"] == {"Weekly total": {n: "Excess" for n in NUTRIENTS}}

def test_ns1_step_daily_totals_go_to_n2_once_for_each_date_in_date_order(storage):
    plan_id = plan_of(storage)
    per_day = {MONDAY: PASTA, TUESDAY: {**PASTA, "calories": 900}}
    analyzer = mock_analyzer(per_day, period="daily")

    result = ns.NutritionService(storage, analyzer).analyze(plan_id, "daily")

    sent = [call.args[0] for call in analyzer.analyze_nutrition.call_args_list]
    assert sent == [per_day[MONDAY], per_day[TUESDAY]]
    assert set(result["comparisons"]) == {MONDAY, TUESDAY}

def test_ns1_step_n2_gets_the_targets_of_the_period(storage):
    plan_id = plan_of(storage)
    weekly = mock_analyzer(PASTA)
    daily = mock_analyzer({MONDAY: PASTA}, period="daily")

    weekly_result = ns.NutritionService(storage, weekly).analyze(plan_id, "weekly")
    daily_result = ns.NutritionService(storage, daily).analyze(plan_id, "daily")

    assert weekly.analyze_nutrition.call_args.args[1] == weekly_result["targets"]
    assert daily.analyze_nutrition.call_args.args[1] == daily_result["targets"]

def test_ns1_step_only_nutrients_that_have_a_total_are_compared(storage):
    plan_id = plan_of(storage)
    partial = {"calories": 500, "protein": 20}  # no carbohydrates, no fat
    analyzer = mock_analyzer(partial, statuses={"calories": "Deficit", "protein": "Deficit"})

    result = ns.NutritionService(storage, analyzer).analyze(plan_id, "weekly")

    sent_targets = analyzer.analyze_nutrition.call_args.args[1]
    assert set(sent_targets) == {"calories", "protein"}
    assert set(result["targets"]) == set(NUTRIENTS)  # the result keeps all targets

def test_ns1_step_the_comparisons_are_what_n2_answered(storage):
    plan_id = plan_of(storage)
    statuses = {"calories": "Excess", "protein": "Deficit",
                "carbohydrates": "Within Target", "fat": "Excess"}

    result = ns.NutritionService(storage, mock_analyzer(PASTA, statuses=statuses)).analyze(plan_id)

    assert result["comparisons"]["Weekly total"] == statuses

def test_ns1_step_the_result_is_a_new_object_each_time(service, storage):
    plan_id = plan_of(storage)
    first = service.analyze(plan_id, "daily")

    first["targets"]["calories"] = -1
    first["totals"][TUESDAY]["calories"] = -1

    second = service.analyze(plan_id, "daily")
    assert second["targets"]["calories"] != -1
    assert second["totals"][TUESDAY]["calories"] == 500

BAD_PLAN_IDS = [0, -1, True, "1", None, 1.5]
BAD_PERIODS = ["monthly", "", None, "Weekly", "DAILY", 7]

def test_ns2_the_two_errors_are_service_errors_and_differ_from_each_other():
    assert issubclass(ns.InvalidAnalysisRequestError, ns.NutritionServiceError)
    assert issubclass(ns.MealPlanNotFoundError, ns.NutritionServiceError)
    assert not issubclass(ns.InvalidAnalysisRequestError, ns.MealPlanNotFoundError)
    assert not issubclass(ns.MealPlanNotFoundError, ns.InvalidAnalysisRequestError)

@pytest.mark.parametrize("plan_id", BAD_PLAN_IDS)
def test_ns2_post_an_invalid_plan_id_is_rejected_before_storage_is_read(plan_id):
    storage = CountingStorage()
    plan_of(storage)
    storage.calls.clear()

    with pytest.raises(ns.InvalidAnalysisRequestError):
        ns.NutritionService(storage).analyze(plan_id, "weekly")

    assert storage.calls == []

@pytest.mark.parametrize("period", BAD_PERIODS)
def test_ns2_post_an_invalid_period_is_rejected_before_storage_is_read(period):
    storage = CountingStorage()
    plan_id = plan_of(storage)
    storage.calls.clear()

    with pytest.raises(ns.InvalidAnalysisRequestError):
        ns.NutritionService(storage).analyze(plan_id, period)

    assert storage.calls == []

def test_ns2_step_an_invalid_request_is_reported_before_a_missing_plan(service):
    # plan 99 does not exist, but the period is checked first (step 1)
    with pytest.raises(ns.InvalidAnalysisRequestError):
        service.analyze(99, "monthly")

@pytest.mark.parametrize("request_", [
    {"plan_id": 0, "period": "weekly"},
    {"plan_id": 1, "period": "monthly"},
    {"plan_id": 99, "period": "weekly"},
])
def test_ns2_step_n1_is_not_asked_for_a_rejected_request(storage, request_):
    analyzer = mock_analyzer(PASTA)

    with pytest.raises(ns.NutritionServiceError):
        ns.NutritionService(storage, analyzer).analyze(**request_)

    analyzer.calculate_nutrition.assert_not_called()

def test_ns2_post_a_plan_that_does_not_exist_is_not_found(service):
    with pytest.raises(ns.MealPlanNotFoundError):
        service.analyze(99, "weekly")

def test_ns2_post_a_plan_that_does_not_exist_is_not_found_for_daily_too(service):
    with pytest.raises(ns.MealPlanNotFoundError):
        service.analyze(99, "daily")

def test_ns2_post_a_saved_recipe_with_that_id_does_not_make_the_plan_exist(service, storage):
    add_recipe(storage)  # recipe 1 exists, meal plan 1 does not

    with pytest.raises(ns.MealPlanNotFoundError):
        service.analyze(1, "weekly")

def test_ns2_post_a_plan_that_uses_a_missing_recipe_is_an_invalid_request(service, storage):
    plan_id = add_plan(storage, [meal(recipe_id=404)])

    with pytest.raises(ns.InvalidAnalysisRequestError) as raised:
        service.analyze(plan_id, "weekly")

    assert str(raised.value).strip()

def test_ns2_post_a_value_error_from_n1_becomes_an_invalid_request_with_its_message(storage):
    plan_id = plan_of(storage)
    analyzer = mock_analyzer(PASTA)
    analyzer.calculate_nutrition.side_effect = ValueError("recipe 7 does not exist")

    with pytest.raises(ns.InvalidAnalysisRequestError) as raised:
        ns.NutritionService(storage, analyzer).analyze(plan_id, "weekly")

    assert str(raised.value) == "recipe 7 does not exist"

def test_ns2_post_a_value_error_from_n2_becomes_an_invalid_request_too(storage):
    plan_id = plan_of(storage)
    analyzer = mock_analyzer(PASTA)
    analyzer.analyze_nutrition.side_effect = ValueError("bad totals")

    with pytest.raises(ns.InvalidAnalysisRequestError) as raised:
        ns.NutritionService(storage, analyzer).analyze(plan_id, "weekly")

    assert str(raised.value) == "bad totals"

def test_ns2_post_a_storage_failure_reaches_the_caller_as_a_storage_error(service, storage):
    plan_id = plan_of(storage)
    storage.read_fails = True

    with pytest.raises(StorageError) as raised:
        service.analyze(plan_id, "weekly")

    assert not isinstance(raised.value, ns.NutritionServiceError)

def test_ns2_post_a_storage_error_inside_the_analyzer_is_not_wrapped_either(storage):
    plan_id = plan_of(storage)
    failure = StorageError("database is locked")
    analyzer = mock_analyzer(PASTA)
    analyzer.calculate_nutrition.side_effect = failure

    with pytest.raises(StorageError) as raised:
        ns.NutritionService(storage, analyzer).analyze(plan_id, "weekly")

    assert raised.value is failure

@pytest.mark.parametrize("error", [TypeError("bug"), KeyError("bug"), AttributeError("bug")])
def test_ns2_step_other_errors_are_not_converted_into_service_errors(storage, error):
    plan_id = plan_of(storage)
    analyzer = mock_analyzer(PASTA)
    analyzer.calculate_nutrition.side_effect = error

    with pytest.raises(type(error)):
        ns.NutritionService(storage, analyzer).analyze(plan_id, "weekly")


def failing_requests():
    storage = FakeStorage()
    plan_id = plan_of(storage)
    missing_recipe_plan = add_plan(storage, [meal(recipe_id=404)])
    service = ns.NutritionService(storage)
    return [
        lambda: service.analyze(0),
        lambda: service.analyze(plan_id, "monthly"),
        lambda: service.analyze(99),
        lambda: service.analyze(missing_recipe_plan),
    ]
    
@pytest.mark.parametrize("attempt", range(4))
def test_ns2_post_every_service_error_carries_a_message_for_the_user(attempt):
    with pytest.raises(ns.NutritionServiceError) as raised:
        failing_requests()[attempt]()

    message = str(raised.value)
    assert message.strip()
    assert "Traceback" not in message and "File \"" not in message

@pytest.mark.parametrize("attempt", range(4))
def test_ns2_post_a_failed_analysis_writes_nothing(attempt):
    storage = ReadOnlyStorage()
    plan_id = plan_of(storage)
    missing_recipe_plan = add_plan(storage, [meal(recipe_id=404)])
    service = ns.NutritionService(storage)
    attempts = [
        lambda: service.analyze(0),
        lambda: service.analyze(plan_id, "monthly"),
        lambda: service.analyze(99),
        lambda: service.analyze(missing_recipe_plan),
    ]
    before = deepcopy(storage._records)

    with pytest.raises(ns.NutritionServiceError):
        attempts[attempt]()

    assert storage._records == before