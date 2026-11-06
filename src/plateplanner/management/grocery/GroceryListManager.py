class GroceryListManager:
    def __init__(self, get_meal_plan=None, get_recipe=None):
        self.get_meal_plan = get_meal_plan
        self.get_recipe = get_recipe

    def gather_ingredients(self, plan_id: int) -> list[dict]:
        if self.get_meal_plan is None or self.get_recipe is None:
            raise ValueError("Meal plan and recipe lookups are required.")

        meal_plan = self.get_meal_plan(plan_id)
        if meal_plan is None:
            raise ValueError(f"Meal plan {plan_id} was not found.")

        ingredients = []

        for meal in meal_plan["meals"]:
            recipe_id = meal["recipe_id"]
            recipe = self.get_recipe(recipe_id)
            if recipe is None:
                raise ValueError(f"Recipe {recipe_id} was not found.")

            scale = meal["servings"] / recipe["servings"]

            for ingredient in recipe["ingredients"]:
                ingredients.append({
                    "name": ingredient["name"],
                    "quantity": ingredient["quantity"] * scale,
                    "unit": ingredient["unit"],
                })

        return ingredients

    def combine_ingredients(self, ingredients: list[dict]) -> list[dict]:
        combined = {}

        for ingredient in ingredients:
            name = ingredient["name"].strip()
            unit = ingredient["unit"].strip().lower()
            quantity = ingredient["quantity"]

            if unit == "kg":
                quantity *= 1000
                unit = "g"

            key = (name.lower(), unit)

            if key in combined:
                combined[key]["quantity"] += quantity
            else:
                combined[key] = {
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                }

        return list(combined.values())