from strawberry import Schema
from inflection import underscore, pluralize


class SchemaManager:
    _models = []

    def __init__(self, *models):
        self._models.extend(models)

    def get_schema(self):
        query = type('Query', (object,), {
            **{f'{underscore(model.__name__)}': model.query_one for model in self._models},
            **{f'{underscore(pluralize(model.__name__))}': model.query_many for model in self._models},
        })

        mutation = type('Mutation', (object,), {
            **{f'create_{underscore(model.__name__)}': model.create_one for model in self._models},
            **{f'create_{underscore(pluralize(model.__name__))}': model.create_many for model in self._models},
            **{f'update_{underscore(model.__name__)}': model.update_one for model in self._models},
            **{f'update_{underscore(pluralize(model.__name__))}': model.update_many for model in self._models},
            **{f'delete_{underscore(model.__name__)}': model.delete_one for model in self._models},
            **{f'delete_{underscore(pluralize(model.__name__))}': model.delete_many for model in self._models},
        })

        return Schema(query=query, mutation=mutation)
