
/**
 * Plate Planner recipe page.
 * Connects the recipe UI to the Flask backend.
 */

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("recipe-form");
    const savedRecipes = document.getElementById("saved-recipes");
    const emptyState = document.querySelector(".recipe-empty-state");
    const addIngredientButton = document.getElementById("add-ingredient");
    const saveButton = document.getElementById("save-recipe");
    const ingredientsSection = document.querySelector(".ingredients-section");
    const firstIngredient = document.querySelector(".ingredient-entry");
    const status = document.querySelector(".form-note");
    const nameField = document.getElementById("recipe-name");
    const servingsField = document.getElementById("servings");
    const clearButton = form.querySelector('[type="reset"]');
    const nutritionFields = form.querySelectorAll("[data-nutrient]");
    let editingId = null;
    let existingNutrition = {};

    /**
     * Display a message to the user.
     */
    function showMessage(message) {
        status.textContent = message;
    }

    /**
     * Create and display the recipe list.
     */
    function displayRecipes(recipes) {
        savedRecipes.replaceChildren();

        emptyState.style.display = recipes.length ? "none" : "";

        for (const recipe of recipes) {
            const card = document.createElement("article");
            card.className = "recipe-card";

            const title = document.createElement("h3");
            title.textContent = recipe.name;

            const servings = document.createElement("p");
            servings.textContent = `Servings: ${recipe.servings}`;

            const ingredients = document.createElement("ul");

            for (const ingredient of recipe.ingredients || []) {
                const item = document.createElement("li");
                item.textContent =
                    `${ingredient.quantity} ${ingredient.unit} ${ingredient.name}`;
                ingredients.appendChild(item);
            }

            const edit = document.createElement("button");
            edit.type = "button";
            edit.className = "btn btn-secondary";
            edit.textContent = "Edit";
            edit.addEventListener("click", () => editRecipe(recipe));

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "btn btn-secondary";
            remove.textContent = "Delete";
            remove.addEventListener("click", () => deleteRecipe(recipe, remove));

            const actions = document.createElement("div");
            actions.className = "form-actions";
            actions.append(edit, remove);
            card.append(title, servings, ingredients, actions);
            savedRecipes.appendChild(card);
        }
    }

    /**
     * Retrieve saved recipes from Flask.
     */
    async function loadRecipes() {
        try {
            const response = await fetch("/api/recipes");

            if (!response.ok) {
                throw new Error("Could not load recipes.");
            }

            const recipes = await response.json();
            displayRecipes(recipes);
        } catch (error) {
            console.error(error);
            showMessage("Could not load saved recipes.");
        }
    }

    /**
     * Add another ingredient input row.
     */
    function addIngredientRow() {
        const newEntry = firstIngredient.cloneNode(true);

        newEntry.querySelectorAll("input, select").forEach(field => {
            field.value = "";
            field.removeAttribute("id");
        });

        ingredientsSection.insertBefore(newEntry, addIngredientButton);
        return newEntry;
    }

    addIngredientButton.addEventListener("click", addIngredientRow);

    form.addEventListener("reset", () => {
        editingId = null;
        existingNutrition = {};
        saveButton.textContent = "Save Recipe";
        clearButton.textContent = "Clear";
        ingredientsSection.querySelectorAll(".ingredient-entry").forEach(entry => {
            if (entry !== firstIngredient) {
                entry.remove();
            }
        });
        showMessage("");
    });

    function editRecipe(recipe) {
        if (saveButton.disabled) {
            return;
        }
        form.reset();
        editingId = recipe.record_id;
        existingNutrition = recipe.nutrition || {};
        for (const field of nutritionFields) {
            field.value = existingNutrition[field.dataset.nutrient] ?? "";
        }
        nameField.value = recipe.name;
        servingsField.value = recipe.servings;
        recipe.ingredients.forEach((ingredient, index) => {
            const entry = index === 0 ? firstIngredient : addIngredientRow();
            entry.querySelector('[name="ingredient_name"]').value = ingredient.name;
            entry.querySelector('[name="quantity"]').value = ingredient.quantity;
            const unit = entry.querySelector('[name="unit"]');
            if (![...unit.options].some(option => option.value === ingredient.unit)) {
                unit.add(new Option(ingredient.unit, ingredient.unit));
            }
            unit.value = ingredient.unit;
        });
        saveButton.textContent = "Save Changes";
        clearButton.textContent = "Cancel Edit";
        nameField.focus();
        showMessage("Editing " + recipe.name);
    }

    async function deleteRecipe(recipe, button) {
        if (saveButton.disabled || !window.confirm("Delete " + recipe.name + "?")) {
            return;
        }
        button.disabled = true;
        try {
            const response = await fetch("/api/recipes/" + recipe.record_id, {
                method: "DELETE"
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "Unable to delete recipe.");
            }
            if (editingId === recipe.record_id) {
                form.reset();
            }
            showMessage(result.message);
            await loadRecipes();
        } catch (error) {
            showMessage(error.message);
        } finally {
            button.disabled = false;
        }
    }

    /**
     * Collect all ingredient entries.
     */
    function getIngredients() {
        return [...document.querySelectorAll(".ingredient-entry")].map(entry => ({
            name: entry.querySelector('[name="ingredient_name"]').value.trim(),
            quantity: Number(entry.querySelector('[name="quantity"]').value),
            unit: entry.querySelector('[name="unit"]').value
        }));
    }

    /**
     * Send the recipe to Flask and save it in SQLite.
     */
    form.addEventListener("submit", async event => {
        event.preventDefault();

        if (!form.reportValidity()) {
            return;
        }

        const recipe = {
            name: nameField.value.trim(),
            servings: Number(servingsField.value),
            ingredients: getIngredients()
        };

        const nutrition = {...existingNutrition};
        for (const field of nutritionFields) {
            const nutrient = field.dataset.nutrient;
            if (field.value === "") {
                delete nutrition[nutrient];
            } else {
                nutrition[nutrient] = Number(field.value);
            }
        }
        if (editingId !== null || Object.keys(nutrition).length > 0) {
            recipe.nutrition = nutrition;
        }

        const url = editingId === null ? "/api/recipes" : "/api/recipes/" + editingId;
        const method = editingId === null ? "POST" : "PUT";
        saveButton.disabled = true;
        clearButton.disabled = true;
        showMessage("Saving recipe...");

        try {
            const response = await fetch(url, {
                method,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(recipe)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Unable to save recipe.");
            }

            form.reset();

            showMessage(result.message);
            await loadRecipes();

        } catch (error) {
            console.error(error);
            showMessage(error.message);
        } finally {
            saveButton.disabled = false;
            clearButton.disabled = false;
        }
    });

    loadRecipes();
});
