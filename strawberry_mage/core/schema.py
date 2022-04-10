"""Manager class for all entity models and for creating strawberry schema."""

from functools import lru_cache
from typing import Dict, Optional, Type, TypeVar

import strawberry
from frozendict import frozendict
from graphql import GraphQLInterfaceType
from inflection import pluralize, underscore
from overrides import overrides
from strawberry import Schema
from strawberry.schema.types import ConcreteType

from strawberry_mage.core.type_creator import GeneratedType
from strawberry_mage.core.types import GraphQLOperation, IDataBackend, IEntityModel, ISchemaManager

TEntity = TypeVar("TEntity", bound=IEntityModel)


class SchemaManager(ISchemaManager[TEntity]):
    """Manager class for all entity models and for creating strawberry schema."""

    _models: Dict[str, Type[IEntityModel]]

    def __init__(self, *models: Type[TEntity], backend: IDataBackend[TEntity]):
        """
        Create a new schema manager.

        :param models: models which should be managed
        :param backend: data backend to use
        """
        if len(models) == 0:
            raise IndexError("Need at least one model for the GraphQL schema.")
        self._models = {GeneratedType.ENTITY.get_typename(m.__name__): m for m in models}
        self._backend = backend
        for model in self._models.values():
            model.__backend__ = self._backend
            model.pre_setup(self)
        self._backend.pre_setup(models)

    @property
    @overrides
    def backend(self):
        return self._backend

    @staticmethod
    def _add_operation(type_object, operation: GraphQLOperation, model: Type[IEntityModel]):
        if operation in model.get_operations():
            name = model.__name__

            if operation.value % 2 == 0:
                name = pluralize(name)
            name = underscore(name)
            if operation.value > 2:
                name = operation.name.lower().split("_")[0] + "_" + name

            setattr(
                type_object,
                name,
                getattr(model.get_strawberry_type(), operation.name.lower()),
            )
            return

    @overrides
    def get_models(self) -> frozendict:
        return frozendict(self._models)

    @overrides
    def get_model_for_name(self, name: str) -> Optional[Type[IEntityModel]]:
        return self._models.get(name, None)

    @lru_cache
    def _collect_types(self):
        types = []
        for model in self._models.values():
            entity = model.get_strawberry_type()
            if entity.base_entity:
                types.append(entity.base_entity)
        return types

    @overrides
    def get_schema(self) -> Schema:
        for model in self._models.values():
            model.post_setup()
        self._backend.post_setup()
        query_object = type("Query", (object,), {})
        mutation_object = type("Mutation", (object,), {})

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

        schema = Schema(
            query=query,
            mutation=(mutation if len(mutation.__annotations__) > 0 else None),
            types=self._collect_types(),
        )

        def resolve_interface_type(obj, *_, **__):
            if (
                base_type := schema.schema_converter.type_map.get(
                    GeneratedType.POLYMORPHIC_BASE.get_typename(obj.__class__.__name__)
                )
            ) is not None:
                return self._backend.get_polymorphic_type(base_type).name
            return self._backend.get_polymorphic_type(schema.schema_converter.type_map[obj.__class__.__name__]).name

        for entry in schema.schema_converter.type_map.values():
            if isinstance(entry, ConcreteType) and isinstance(entry.implementation, GraphQLInterfaceType):
                setattr(entry.implementation, "resolve_type", resolve_interface_type)

        return schema
