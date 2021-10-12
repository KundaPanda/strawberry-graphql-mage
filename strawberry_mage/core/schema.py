from functools import lru_cache
from typing import Dict

import strawberry
from graphql import GraphQLInterfaceType
from inflection import underscore, pluralize
from strawberry import Schema
from strawberry.schema.types import ConcreteType

from strawberry_mage.core.type_creator import GeneratedType
from strawberry_mage.core.types import GraphQLOperation, IEntityModel, ISchemaManager


class SchemaManager(ISchemaManager):
    _models: Dict[str, IEntityModel]

    def __init__(self, *models):
        self._models = {GeneratedType.ENTITY.get_typename(m.__name__): m for m in models}
        for model in self._models.values():
            model.pre_setup(self)

    @staticmethod
    def _add_operation(type_object, operation: GraphQLOperation, model: IEntityModel):
        if operation in model.get_operations():
            name = model.__name__

            if operation.value % 2 == 0:
                name = pluralize(name)
            name = underscore(name)
            if operation.value > 2:
                name = operation.name.lower().split('_')[0] + '_' + name

            setattr(type_object, name, getattr(model.get_strawberry_type(), operation.name.lower()))
            return

    def get_models(self):
        return self._models[:]

    def get_model_for_name(self, name: str):
        return self._models.get(name, None)

    @lru_cache
    def _collect_types(self):
        types = []
        for model in self._models.values():
            entity = model.get_strawberry_type()
            if entity.base_entity:
                types.append(entity.base_entity)
        return types

    def get_schema(self):
        for model in self._models.values():
            model.post_setup()
        query_object = type('Query', (object,), {})
        mutation_object = type('Mutation', (object,), {})

        for model in self._models.values():
            # Query
            self._add_operation(query_object, GraphQLOperation.QUERY_ONE, model)
            self._add_operation(query_object, GraphQLOperation.QUERY_MANY, model)

            # Create
            self._add_operation(mutation_object, GraphQLOperation.CREATE_ONE, model)
            self._add_operation(mutation_object, GraphQLOperation.CREATE_MANY, model)

            # Update
            self._add_operation(mutation_object, GraphQLOperation.UPDATE_ONE, model)
            self._add_operation(mutation_object, GraphQLOperation.UPDATE_MANY, model)

            # Delete
            self._add_operation(mutation_object, GraphQLOperation.DELETE_ONE, model)
            self._add_operation(mutation_object, GraphQLOperation.DELETE_MANY, model)

        query = strawberry.type(query_object)
        mutation = strawberry.type(mutation_object)

        schema = Schema(query=query,
                        mutation=(mutation if len(mutation.__annotations__) > 0 else None),
                        types=self._collect_types())

        def resolve_interface_type(obj, info, type_):
            if (base_type := schema.schema_converter.type_map.get(
                    GeneratedType.POLYMORPHIC_BASE.get_typename(obj.__class__.__name__))) is not None:
                return base_type.implementation
            return schema.schema_converter.type_map[obj.__class__.__name__].implementation

        for entry in schema.schema_converter.type_map.values():
            if isinstance(entry, ConcreteType) and isinstance(entry.implementation, GraphQLInterfaceType):
                setattr(entry.implementation, 'resolve_type', resolve_interface_type)

        return schema
