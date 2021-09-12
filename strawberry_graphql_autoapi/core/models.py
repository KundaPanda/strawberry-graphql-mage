from typing import Any, Set, List, Type, Dict, Tuple

from strawberry_graphql_autoapi.core.resolver import resolver_query_one, resolver_query_many
from strawberry_graphql_autoapi.core.strawberry_types import StrawberryModelType
from strawberry_graphql_autoapi.core.type_creator import create_entity_type, \
    create_input_types
from strawberry_graphql_autoapi.core.types import GraphQLOperation, IEntityModel, IDataBackend


class EntityModel(IEntityModel):
    __backend__: IDataBackend = None
    __primary_key__: Any = None
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
    def get_all_attributes(cls) -> List[str]:
        return cls.__backend__.get_all_attributes(cls)

    @classmethod
    def get_attribute_types(cls) -> Dict[str, Type]:
        return cls.__backend__.get_attribute_types(cls)

    @classmethod
    def get_attribute_type(cls, attr: str) -> Type:
        return cls.__backend__.get_attribute_type(cls, attr)

    @classmethod
    def setup(cls):
        cls._properties = cls.__backend__.get_all_attributes(cls)
        cls._strawberry_type = StrawberryModelType(
            entity=create_entity_type(cls),
            input_types=create_input_types(cls),
            filter=None,
            ordering=None,
        )
        cls._strawberry_type.query_one = resolver_query_one(cls)
        cls._strawberry_type.query_many = resolver_query_many(cls)
        return cls
