from functools import cached_property
from typing import Type, List, Optional

import strawberry
from strawberry.arguments import StrawberryArgument, UNSET
from strawberry.types.fields.resolver import StrawberryResolver

from strawberry_graphql_autoapi.core.type_creator import GeneratedType
from strawberry_graphql_autoapi.core.types import GraphQLOperation, IEntityModel, ModuleBoundStrawberryAnnotation


class ModuleBoundStrawberryResolver(StrawberryResolver):
    @cached_property
    def arguments(self) -> List[StrawberryArgument]:
        args = super().arguments
        return [StrawberryArgument(a.python_name, a.graphql_name,
                                   ModuleBoundStrawberryAnnotation.from_annotation(a.type_annotation),
                                   a.is_subscription, a.description, a.default)
                for a in args]


def resolver_query_one(model: Type[IEntityModel]):
    return_type = Optional[model.get_strawberry_type().entity]
    data_type = GeneratedType.QUERY_ONE.get_typename(model.__name__)

    def query_one(data: data_type = UNSET) -> return_type:
        return model.resolve(GraphQLOperation.QUERY_ONE, data)

    return strawberry.field(ModuleBoundStrawberryResolver(query_one))


def resolver_query_many(model: Type[IEntityModel]):
    return_type = List[model.get_strawberry_type().entity]
    data_type = GeneratedType.QUERY_MANY.get_typename(model.__name__)

    def query_many(data: Optional[data_type] = UNSET) -> return_type:
        return model.resolve(GraphQLOperation.QUERY_MANY, data)

    return strawberry.field(ModuleBoundStrawberryResolver(query_many))
