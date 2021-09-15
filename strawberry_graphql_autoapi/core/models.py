from typing import Any, Set, List, Type, Dict, Tuple, Optional

from strawberry_graphql_autoapi.core.resolver import resolver_query_one, resolver_query_many, resolver_create_one, \
    resolver_create_many, resolver_update_one, resolver_update_many, resolver_delete_one, resolver_delete_many
from strawberry_graphql_autoapi.core.strawberry_types import StrawberryModelType
from strawberry_graphql_autoapi.core.type_creator import create_entity_type, \
    create_input_types, create_filter_input, create_ordering_input
from strawberry_graphql_autoapi.core.types import GraphQLOperation, IEntityModel, IDataBackend


class EntityModel(IEntityModel):
    __backend__: IDataBackend = None
    _primary_key__: Any = None
    _strawberry_type: StrawberryModelType
    _properties: List[str]

    @classmethod
    def get_strawberry_type(cls):
        return cls._strawberry_type

    @classmethod
    def get_primary_key(cls) -> Tuple:
        return cls.__backend__.get_primary_key(cls)

    @classmethod
    def resolve(cls, operation: GraphQLOperation, data: Any):
        return cls.__backend__.resolve(cls, operation, data)

    @classmethod
    def get_operations(cls) -> Set[GraphQLOperation]:
        return cls.__backend__.get_operations(cls)

    @classmethod
    def get_attributes(cls, operation: Optional[GraphQLOperation] = None) -> List[str]:
        return cls.__backend__.get_attributes(cls, operation)

    @classmethod
    def get_attribute_types(cls) -> Dict[str, Type]:
        return cls.__backend__.get_attribute_types(cls)

    @classmethod
    def get_attribute_type(cls, attr: str) -> Type:
        return cls.__backend__.get_attribute_type(cls, attr)

    @classmethod
    def setup(cls):
        cls._properties = cls.__backend__.get_attributes(cls)
        cls._strawberry_type = StrawberryModelType(
            entity=create_entity_type(cls),
            filter=create_filter_input(cls),
            ordering=create_ordering_input(cls),
        )
        cls._strawberry_type.input_types = create_input_types(cls)
        cls._strawberry_type.query_one = resolver_query_one(cls)
        cls._strawberry_type.query_many = resolver_query_many(cls)
        cls._strawberry_type.create_one = resolver_create_one(cls)
        cls._strawberry_type.create_many = resolver_create_many(cls)
        cls._strawberry_type.update_one = resolver_update_one(cls)
        cls._strawberry_type.update_many = resolver_update_many(cls)
        cls._strawberry_type.delete_one = resolver_delete_one(cls)
        cls._strawberry_type.delete_many = resolver_delete_many(cls)
        return cls
