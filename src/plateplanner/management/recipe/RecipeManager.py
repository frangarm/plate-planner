def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_positive_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 < value < float("inf")
    )


class RecipeManager:
    def validate_recipe(self, recipe_data: dict) -> bool:
        if not isinstance(recipe_data, dict):
            return False

        if not _has_text(recipe_data.get("name")):
            return False

        if not _is_positive_number(recipe_data.get("servings")):
            return False

        ingredients = recipe_data.get("ingredients")
        if not isinstance(ingredients, list) or not ingredients:
            return False

        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                return False

            if not _has_text(ingredient.get("name")):
                return False

            if not _is_positive_number(ingredient.get("quantity")):
                return False

            if not _has_text(ingredient.get("unit")):
                return False

        return True