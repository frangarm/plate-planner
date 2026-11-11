
/**
 * Grocery List page for Plate Planner.
 * Loads, generates, edits, and saves grocery lists.
 */

document.addEventListener("DOMContentLoaded", () => {
    const planSelect = document.getElementById("meal-plan-select");
    const generateButton = document.getElementById("generate-grocery-list");
    const itemsBody = document.getElementById("grocery-items");
    const addItemForm = document.getElementById("add-grocery-item-form");
    const addItemButton = document.getElementById("add-grocery-item");

    const totalItems = document.getElementById("total-items");
    const purchasedItems = document.getElementById("purchased-items");
    const remainingItems = document.getElementById("remaining-items");

    const generateStatus = document.querySelector(
        "#grocery-settings .grocery-help-text"
    );
    const itemStatus = addItemForm.querySelector(".grocery-help-text");

    let currentList = null;

    /**
     * Send a request to Flask and parse its response.
     */
    async function apiRequest(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed.");
        }

        return data;
    }

    /**
     * Load all saved meal plans into the selector.
     */
    async function loadPlans() {
        const plans = await apiRequest("/api/meal-plans");

        planSelect.replaceChildren();
        planSelect.add(new Option("Select a meal plan", ""));

        for (const plan of plans) {
            planSelect.add(new Option(
                `Week of ${plan.weekStart}`,
                String(plan.record_id)
            ));
        }

        planSelect.disabled = plans.length === 0;
        generateButton.disabled = plans.length === 0;

        if (plans.length === 0) {
            generateStatus.textContent =
                "Create a weekly meal plan before generating a list.";
            renderList();
            return;
        }

        const previousId = localStorage.getItem("platePlannerPlanId");

        if (plans.some(plan => String(plan.record_id) === previousId)) {
            planSelect.value = previousId;
        } else {
            planSelect.value = String(plans[plans.length - 1].record_id);
        }

        await loadCurrentList();
    }

    /**
     * Load the saved grocery list for the selected meal plan.
     */
    async function loadCurrentList() {
        const lists = await apiRequest("/api/grocery-lists");
        const planId = Number(planSelect.value);

        currentList = lists.find(
            list => list.plan_id === planId
        ) || null;

        renderList();
    }

    /**
     * Update the overview counts.
     */
    function updateSummary() {
        const items = currentList ? currentList.items : [];
        const purchased = items.filter(item => item.purchased).length;

        totalItems.textContent = items.length;
        purchasedItems.textContent = purchased;
        remainingItems.textContent = items.length - purchased;
    }

    /**
     * Save updated items through Flask.
     */
    async function saveItems(items) {
        if (!currentList) {
            throw new Error("Generate a grocery list first.");
        }

        currentList = await apiRequest(
            `/api/grocery-lists/${currentList.record_id}`,
            {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({items})
            }
        );

        renderList();
        itemStatus.textContent = "Grocery list updated.";
    }

    /**
     * Add a single cell containing text.
     */
    function addTextCell(row, value) {
        const cell = document.createElement("td");
        cell.textContent = String(value);
        row.appendChild(cell);
        return cell;
    }

    /**
     * Display the grocery items and action controls.
     */
    function renderList() {
        itemsBody.replaceChildren();

        const items = currentList ? currentList.items : [];

        addItemButton.disabled = !currentList;
        updateSummary();

        if (!currentList) {
            const row = document.createElement("tr");
            addTextCell(
                row,
                "Select a meal plan and generate a grocery list."
            ).colSpan = 5;

            itemsBody.appendChild(row);
            return;
        }

        if (items.length === 0) {
            const row = document.createElement("tr");
            addTextCell(row, "No grocery items yet.").colSpan = 5;
            itemsBody.appendChild(row);
            return;
        }

        items.forEach((item, index) => {
            const row = document.createElement("tr");

            // Ingredient name.
            addTextCell(row, item.name);

            // Editable quantity.
            const quantityCell = document.createElement("td");
            const quantityInput = document.createElement("input");

            quantityInput.type = "number";
            quantityInput.min = "0.01";
            quantityInput.step = "any";
            quantityInput.value = item.quantity;
            quantityInput.style.width = "85px";

            quantityInput.addEventListener("change", async () => {
                const quantity = Number(quantityInput.value);

                if (!Number.isFinite(quantity) || quantity <= 0) {
                    itemStatus.textContent =
                        "Quantity must be greater than zero.";
                    renderList();
                    return;
                }

                const updated = items.map((entry, position) =>
                    position === index
                        ? {...entry, quantity}
                        : {...entry}
                );

                try {
                    await saveItems(updated);
                } catch (error) {
                    itemStatus.textContent = error.message;
                    renderList();
                }
            });

            quantityCell.appendChild(quantityInput);
            row.appendChild(quantityCell);

            // Unit.
            addTextCell(row, item.unit);

            // Purchased checkbox.
            const purchasedCell = document.createElement("td");
            const checkbox = document.createElement("input");

            checkbox.type = "checkbox";
            checkbox.checked = Boolean(item.purchased);

            checkbox.addEventListener("change", async () => {
                const updated = items.map((entry, position) =>
                    position === index
                        ? {...entry, purchased: checkbox.checked}
                        : {...entry}
                );

                try {
                    await saveItems(updated);
                } catch (error) {
                    itemStatus.textContent = error.message;
                    renderList();
                }
            });

            purchasedCell.appendChild(checkbox);
            row.appendChild(purchasedCell);

            // Remove item.
            const actionCell = document.createElement("td");
            const removeButton = document.createElement("button");

            removeButton.type = "button";
            removeButton.className = "btn btn-secondary";
            removeButton.textContent = "Remove";

            removeButton.addEventListener("click", async () => {
                const updated = items.filter(
                    (_, position) => position !== index
                );

                try {
                    await saveItems(updated);
                } catch (error) {
                    itemStatus.textContent = error.message;
                }
            });

            actionCell.appendChild(removeButton);
            row.appendChild(actionCell);

            itemsBody.appendChild(row);
        });
    }

    /**
     * Generate a new list or load an existing saved list.
     */
    generateButton.addEventListener("click", async () => {
        const planId = Number(planSelect.value);

        if (!planId) {
            generateStatus.textContent = "Select a meal plan.";
            return;
        }

        generateButton.disabled = true;

        try {
            currentList = await apiRequest("/api/grocery-lists", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({planId})
            });

            generateStatus.textContent = "Grocery list loaded!";
            renderList();
        } catch (error) {
            generateStatus.textContent = error.message;
        } finally {
            generateButton.disabled = false;
        }
    });

    /**
     * Add an ingredient manually to the saved grocery list.
     */
    addItemForm.addEventListener("submit", async event => {
        event.preventDefault();

        if (!currentList || !addItemForm.reportValidity()) {
            return;
        }

        const item = {
            name: document.getElementById("grocery-item-name").value.trim(),
            quantity: Number(
                document.getElementById("grocery-quantity").value
            ),
            unit: document.getElementById("grocery-unit").value,
            purchased: false
        };

        try {
            await saveItems([...currentList.items, item]);
            addItemForm.reset();
            itemStatus.textContent = "Item added successfully!";
        } catch (error) {
            itemStatus.textContent = error.message;
        }
    });

    /**
     * Switch between saved meal plans.
     */
    planSelect.addEventListener("change", async () => {
        if (planSelect.value) {
            localStorage.setItem(
                "platePlannerPlanId",
                planSelect.value
            );
        }

        try {
            await loadCurrentList();
        } catch (error) {
            generateStatus.textContent = error.message;
        }
    });

    /**
     * Initialize the page.
     */
    async function initialize() {
        try {
            await loadPlans();
        } catch (error) {
            console.error(error);
            generateStatus.textContent =
                "Unable to load meal plans or grocery lists.";
        }
    }

    initialize();
});
