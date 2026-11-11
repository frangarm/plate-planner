
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

            card.append(title, servings, ingredients);
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
    addIngredientButton.addEventListener("click", () => {
        const newEntry = firstIngredient.cloneNode(true);

        newEntry.querySelectorAll("input, select").forEach(field => {
            field.value = "";
            field.removeAttribute("id");
        });

        ingredientsSection.insertBefore(newEntry, addIngredientButton);
    });

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
            name: document.getElementById("recipe-name").value.trim(),
            servings: Number(document.getElementById("servings").value),
            ingredients: getIngredients()
        };

        saveButton.disabled = true;
        showMessage("Saving recipe...");

        try {
            const response = await fetch("/api/recipes", {
                method: "POST",
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

            // Remove extra ingredient rows after saving.
            document.querySelectorAll(".ingredient-entry").forEach(
                (entry, index) => {
                    if (index > 0) {
                        entry.remove();
                    }
                }
            );

            showMessage("Recipe saved successfully!");
            await loadRecipes();

        } catch (error) {
            console.error(error);
            showMessage(error.message);
        } finally {
            saveButton.disabled = false;
        }
    });

    loadRecipes();
});
