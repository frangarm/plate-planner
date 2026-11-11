
/**
 * Plate Planner weekly meal planning UI.
 * Connects the page to the Flask API.
 */

document.addEventListener("DOMContentLoaded", () => {
    const weekStart = document.getElementById("week-start");
    const createButton = document.getElementById("create-plan");
    const planSelect = document.getElementById("existing-plan-select");

    const recipeSelect = document.getElementById("recipe-select");
    const addMealButton = document.getElementById("save-meal");
    const addMealForm = document.getElementById("add-meal-form");

    const planStatus = document.querySelector(
        "#plan-settings .planner-help-text"
    );
    const mealStatus = document.querySelector(
        "#add-meal-section .planner-help-text"
    );
    const scheduleStatus = document.querySelector(".planner-status");

    let recipes = [];
    let plans = [];
    let selectedPlan = null;

    /**
     * Send an API request and return its JSON response.
     */
    async function apiRequest(url, options = {}) {
        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Request failed.");
        }

        return result;
    }

    /**
     * Load recipes saved in the SQLite database.
     */
    async function loadRecipes() {
        recipes = await apiRequest("/api/recipes");

        recipeSelect.replaceChildren();

        if (recipes.length === 0) {
            recipeSelect.add(new Option("No recipes saved", ""));
            recipeSelect.disabled = true;
            mealStatus.textContent = "Add a recipe before planning meals.";
            return;
        }

        recipeSelect.add(new Option("Select a recipe", ""));

        for (const recipe of recipes) {
            recipeSelect.add(
                new Option(recipe.name, String(recipe.record_id))
            );
        }

        recipeSelect.disabled = false;
    }

    /**
     * Load all saved plans and select one to display.
     */
    async function loadPlans(preferredId = null) {
        plans = await apiRequest("/api/meal-plans");

        planSelect.replaceChildren();
        planSelect.add(new Option("Select a saved plan", ""));

        for (const plan of plans) {
            planSelect.add(
                new Option(
                    `Week of ${plan.weekStart}`,
                    String(plan.record_id)
                )
            );
        }

        const lastId = preferredId ||
            Number(localStorage.getItem("platePlannerPlanId"));

        selectedPlan = plans.find(
            plan => plan.record_id === lastId
        ) || plans[plans.length - 1] || null;

        if (selectedPlan) {
            planSelect.value = String(selectedPlan.record_id);
            localStorage.setItem(
                "platePlannerPlanId",
                String(selectedPlan.record_id)
            );
        }

        renderPlan();
    }

    /**
     * Return a YYYY-MM-DD date a given number of days
     * after the start of the selected week.
     */
    function dateForDay(dayIndex) {
        const day = new Date(
            `${selectedPlan.weekStart}T00:00:00Z`
        );

        day.setUTCDate(day.getUTCDate() + dayIndex);

        return day;
    }

    /**
     * Display meals in the seven-day calendar.
     */
    function renderPlan() {
        addMealButton.disabled = !selectedPlan || recipes.length === 0;

        if (!selectedPlan) {
            scheduleStatus.textContent = "No Plan Selected";
            planStatus.textContent = "Create a weekly meal plan to begin.";
            document.querySelectorAll(".planner-meal p").forEach(p => {
                p.textContent = "No meal planned";
            });
            return;
        }

        scheduleStatus.textContent =
            `Week of ${selectedPlan.weekStart}`;

        planStatus.textContent = "Meal plan loaded.";

        const cards = document.querySelectorAll(".planner-day-card");

        cards.forEach((card, index) => {
            const day = dateForDay(index);
            const dateText = day.toISOString().slice(0, 10);

            const dayName = day.toLocaleDateString("en-US", {
                weekday: "long",
                timeZone: "UTC"
            });

            card.querySelector("h3").textContent = dayName;

            card.querySelectorAll(".planner-meal").forEach(section => {
                const slot = section.querySelector(
                    ".planner-meal-label"
                ).textContent.trim().toLowerCase();

                const matchingMeals = selectedPlan.meals.filter(
                    meal => meal.date === dateText &&
                        meal.mealSlot === slot
                );

                const descriptions = matchingMeals.map(meal => {
                    const recipe = recipes.find(
                        item => item.record_id === meal.recipe_id
                    );

                    const name = recipe ? recipe.name : "Unknown Recipe";
                    return `${name} (${meal.servings} servings)`;
                });

                section.querySelector("p").textContent =
                    descriptions.length
                        ? descriptions.join(", ")
                        : "No meal planned";
            });
        });
    }

    /**
     * Create a new weekly meal plan.
     */
    createButton.addEventListener("click", async () => {
        if (!weekStart.value) {
            planStatus.textContent = "Select a starting date.";
            return;
        }

        createButton.disabled = true;

        try {
            const plan = await apiRequest("/api/meal-plans", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    weekStart: weekStart.value
                })
            });

            await loadPlans(plan.record_id);
            planStatus.textContent = "Weekly meal plan created!";

        } catch (error) {
            planStatus.textContent = error.message;
        } finally {
            createButton.disabled = false;
        }
    });

    /**
     * Switch between previously saved meal plans.
     */
    planSelect.addEventListener("change", () => {
        selectedPlan = plans.find(
            plan => String(plan.record_id) === planSelect.value
        ) || null;

        if (selectedPlan) {
            localStorage.setItem(
                "platePlannerPlanId",
                String(selectedPlan.record_id)
            );
        } else {
            localStorage.removeItem("platePlannerPlanId");
        }

        renderPlan();
    });

    /**
     * Validate and add a meal to the selected plan.
     */
    addMealButton.addEventListener("click", async () => {
        if (!selectedPlan || !addMealForm.reportValidity()) {
            return;
        }

        const meal = {
            date: document.getElementById("meal-date").value,
            mealSlot: document.getElementById("meal-slot").value,
            recipeId: Number(recipeSelect.value),
            servings: Number(
                document.getElementById("meal-servings").value
            )
        };

        addMealButton.disabled = true;

        try {
            const updated = await apiRequest(
                `/api/meal-plans/${selectedPlan.record_id}/meals`,
                {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(meal)
                }
            );

            selectedPlan = updated;

            plans = plans.map(plan =>
                plan.record_id === updated.record_id
                    ? updated
                    : plan
            );

            renderPlan();
            mealStatus.textContent = "Meal added successfully!";

        } catch (error) {
            mealStatus.textContent = error.message;
        } finally {
            addMealButton.disabled =
                !selectedPlan || recipes.length === 0;
        }
    });

    /**
     * Load recipes and meal plans when the page opens.
     */
    async function initialize() {
        try {
            await loadRecipes();
            await loadPlans();
        } catch (error) {
            console.error(error);
            planStatus.textContent =
                "Unable to load meal planning information.";
        }
    }

    initialize();
});
