from copy import deepcopy
from data.DataStorageManager import RECORD_TYPE_RECIPE
from plateplanner.management.recipe.RecipeManager import RecipeManager

class ServiceError(Exception):
    pass

class InvalidRecipeError(ServiceError):
    pass

class RecipeNotFoundError(ServiceError):
    pass

class RecipeInUseError(ServiceError):
    pass

class RecipeService:
    def __init__(self, storage, validator=None):
        self._storage = storage
        self._validator = RecipeManager() if validator is None else validator

    def _validated_copy(self, recipe_data):
        data = deepcopy(recipe_data)
        if not self._validator.validate_recipe(data):
            raise InvalidRecipeError("Invalid recipe information.")
        return data

    def create(self, recipe_data):
        data = self._validated_copy(recipe_data)
        recipe_id = self._storage.save_record(RECORD_TYPE_RECIPE, data)
        if recipe_id is None:
            raise InvalidRecipeError("Could not save the recipe.")
        return self.get(recipe_id)

    def get(self, recipe_id):
        recipe = self._storage.get_record(RECORD_TYPE_RECIPE, recipe_id)
        if recipe is None:
            raise RecipeNotFoundError("Recipe not found.")
        return recipe

    def get_all(self):
        return self._storage.get_all_records(RECORD_TYPE_RECIPE)

    def update(self, recipe_id, recipe_data):
        edits = self._validated_copy(recipe_data)
        existing = self.get(recipe_id)

        updated = {**existing, **edits}
        updated.pop("record_id", None)

        if not self._storage.update_record(RECORD_TYPE_RECIPE, recipe_id, updated):
            raise RecipeNotFoundError("Recipe not found.")
        return self.get(recipe_id)

    def delete(self, recipe_id):
        self.get(recipe_id)
        if not self._storage.delete_record(RECORD_TYPE_RECIPE, recipe_id):
            self.get(recipe_id)
            raise RecipeInUseError("This recipe is used in a saved meal plan.")