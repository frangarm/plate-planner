class ServiceError(Exception):
    def __init__(self, *args):
        raise NotImplementedError

class InvalidRecipeError(ServiceError):
    def __init__(self, *args):
        raise NotImplementedError
class RecipeNotFoundError(ServiceError): 
    def __init__(self, *args):
        raise NotImplementedError
class RecipeInUseError(ServiceError):
    def __init__(self, *args):
        raise NotImplementedError


class RecipeService:
    def __init__(self, storage, validator=None):
        raise NotImplementedError

    def create(self, recipe_data):
        raise NotImplementedError

    def get(self, recipe_id):
        raise NotImplementedError

    def get_all(self):
        raise NotImplementedError

    def update(self, recipe_id, recipe_data):
        raise NotImplementedError

    def delete(self, recipe_id):
        raise NotImplementedError