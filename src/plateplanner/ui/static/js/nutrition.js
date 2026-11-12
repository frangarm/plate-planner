document.addEventListener("DOMContentLoaded", async () => {
    const plan = document.getElementById("nutrition-plan");
    const period = document.getElementById("nutrition-period");
    const analyze = document.getElementById("analyze-nutrition");
    const status = document.getElementById("nutrition-status");
    const warning = document.getElementById("nutrition-warning");
    const table = document.getElementById("nutrition-results");
    const counts = {
        analyzed: document.getElementById("nutrients-analyzed"),
        deficits: document.getElementById("nutrition-deficits"),
        excesses: document.getElementById("nutrition-excesses")
    };
    const labels = {
        calories: "Calories (kcal)",
        protein: "Protein (g)",
        carbohydrates: "Carbohydrates (g)",
        fat: "Fat (g)"
    };
    const format = new Intl.NumberFormat("en-US", {maximumFractionDigits: 2});

    async function getJSON(url) {
        const response = await fetch(url);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Unable to load nutrition results.");
        }
        return data;
    }

    function showPlaceholder(message) {
        const row = document.createElement("tr");
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = message;
        table.replaceChildren(row);
    }

    function clearResults() {
        warning.hidden = true;
        for (const count of Object.values(counts)) {
            count.textContent = "—";
        }
        showPlaceholder("Select a plan and run nutrition analysis.");
    }

    function render(result) {
        const daily = result.period === "daily";
        const groups = daily ? Object.entries(result.totals) : [["Weekly total", result.totals]];
        const nutrients = new Set();
        let deficits = 0;
        let excesses = 0;
        warning.hidden = !result.incomplete;
        table.replaceChildren();

        for (const [label, totals] of groups) {
            const heading = table.insertRow();
            const title = document.createElement("th");
            title.colSpan = 4;
            title.textContent = label;
            heading.append(title);
            for (const [nutrient, total] of Object.entries(totals)) {
                nutrients.add(nutrient);
                const comparison = result.comparisons[label]?.[nutrient];
                deficits += Number(comparison === "Deficit");
                excesses += Number(comparison === "Excess");
                const target = result.targets[nutrient];
                const row = table.insertRow();
                for (const value of [
                    labels[nutrient] || nutrient,
                    format.format(total),
                    target === undefined ? "—" : format.format(target),
                    comparison || "—"
                ]) {
                    row.insertCell().textContent = value;
                }
            }
        }

        if (nutrients.size === 0) {
            showPlaceholder("No nutrition values available for this period.");
        }
        counts.analyzed.textContent = nutrients.size;
        counts.deficits.textContent = result.incomplete ? "—" : deficits;
        counts.excesses.textContent = result.incomplete ? "—" : excesses;
        status.textContent = result.incomplete ? "Partial results" : "Analysis complete";
    }

    analyze.addEventListener("click", async () => {
        const planId = plan.value;
        const selectedPeriod = period.value;
        clearResults();
        plan.disabled = period.disabled = analyze.disabled = true;
        status.textContent = "Analyzing…";
        try {
            render(await getJSON(`/api/meal-plans/${planId}/nutrition?period=${selectedPeriod}`));
        } catch (error) {
            status.textContent = error.message;
        } finally {
            plan.disabled = period.disabled = analyze.disabled = false;
        }
    });

    for (const field of [plan, period]) {
        field.addEventListener("change", () => {
            clearResults();
            status.textContent = "Ready to analyze";
        });
    }

    try {
        const plans = await getJSON("/api/meal-plans");
        if (plans.length === 0) {
            status.textContent = "Create a meal plan first.";
            return;
        }
        plan.replaceChildren(...plans.map(item =>
            new Option(`Week of ${item.weekStart}`, String(item.record_id))
        ));
        period.value = "weekly";
        plan.disabled = period.disabled = analyze.disabled = false;
        status.textContent = "Ready to analyze";
    } catch (error) {
        status.textContent = error.message;
    }
});
