
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
    let editing = null;
    let saving = false;
    const mealDate = document.getElementById("meal-date");
    const mealSlot = document.getElementById("meal-slot");
    const mealServings = document.getElementById("meal-servings");
    const cancelEdit = document.createElement("button");
    cancelEdit.type = "button";
    cancelEdit.className = "btn btn-secondary";
    cancelEdit.textContent = "Cancel Edit";
    cancelEdit.hidden = true;
    addMealButton.after(cancelEdit);

    function resetEdit() {
        editing = null;
        addMealForm.reset();
        addMealButton.textContent = "Add Meal";
        cancelEdit.hidden = true;
    }

    cancelEdit.addEventListener("click", () => {
        resetEdit();
        mealStatus.textContent = "Meal edit canceled.";
    });

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
        addMealButton.disabled = saving || !selectedPlan || recipes.length === 0;

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

                const contents = section.querySelector("p");
                contents.replaceChildren();

                selectedPlan.meals.forEach((meal, mealIndex) => {
                    if (meal.date !== dateText || meal.mealSlot !== slot) {
                        return;
                    }

                    const recipe = recipes.find(item => item.record_id === meal.recipe_id);
                    const name = recipe ? recipe.name : "Unknown Recipe";
                    const row = document.createElement("span");
                    row.style.display = "block";
                    row.append(`${name} (${meal.servings} servings) `);

                    for (const [label, action] of [
                        ["Edit", () => {
                            if (saving) return;
                            editing = {mealIndex, original: meal};
                            mealDate.value = meal.date;
                            mealSlot.value = meal.mealSlot;
                            recipeSelect.value = String(meal.recipe_id);
                            mealServings.value = meal.servings;
                            addMealButton.textContent = "Save Changes";
                            cancelEdit.hidden = false;
                            mealStatus.textContent = "Editing " + name;
                            mealDate.focus();
                        }],
                        ["Remove", () => {
                            if (!saving && window.confirm("Remove " + name + " from this plan?")) {
                                saveMeal("DELETE", {original: meal}, mealIndex, "Meal removed.");
                            }
                        }]
                    ]) {
                        const button = document.createElement("button");
                        button.type = "button";
                        button.className = "btn btn-secondary";
                        button.textContent = label;
                        button.disabled = saving;
                        button.addEventListener("click", action);
                        row.append(button, " ");
                    }
                    contents.append(row);
                });

                if (!contents.hasChildNodes()) {
                    contents.textContent = "No meal planned";
                }
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

        resetEdit();
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
        resetEdit();
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

    addMealButton.addEventListener("click", () => {
        if (saving || !selectedPlan || !addMealForm.reportValidity()) {
            return;
        }

        const meal = {
            date: mealDate.value,
            mealSlot: mealSlot.value,
            recipeId: Number(recipeSelect.value),
            servings: Number(mealServings.value)
        };

        if (editing) {
            saveMeal("PUT", {original: editing.original, meal}, editing.mealIndex, "Meal updated.");
        } else {
            saveMeal("POST", meal, null, "Meal added successfully!");
        }
    });

    async function saveMeal(method, payload, mealIndex, message) {
        const planId = selectedPlan.record_id;
        const base = `/api/meal-plans/${planId}/meals`;
        const url = mealIndex === null ? base : `${base}/${mealIndex}`;
        saving = true;
        createButton.disabled = true;
        planSelect.disabled = true;
        cancelEdit.disabled = true;
        renderPlan();

        try {
            const updated = await apiRequest(url, {
                method,
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload)
            });
            selectedPlan = updated;
            plans = plans.map(plan => plan.record_id === planId ? updated : plan);
            resetEdit();
            mealStatus.textContent = message;
        } catch (error) {
            mealStatus.textContent = error.message;
        } finally {
            saving = false;
            createButton.disabled = false;
            planSelect.disabled = false;
            cancelEdit.disabled = false;
            renderPlan();
            if (method === "DELETE") {
                planStatus.textContent = mealStatus.textContent;
            }
        }
    }

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
