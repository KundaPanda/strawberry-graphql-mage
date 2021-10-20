from functools import cached_property
from typing import Type, List, Optional

import strawberry
from strawberry.arguments import StrawberryArgument, UNSET
from strawberry.types import Info
from strawberry.types.fields.resolver import StrawberryResolver

from strawberry_mage.core.strawberry_types import DeleteResult
from strawberry_mage.core.type_creator import GeneratedType
from strawberry_mage.core.types import (
    GraphQLOperation,
    IEntityModel,
    ModuleBoundStrawberryAnnotation,
)


class ModuleBoundStrawberryResolver(StrawberryResolver):
    @cached_property
    def arguments(self) -> List[StrawberryArgument]:
        args = super().arguments
        return [
            StrawberryArgument(
                a.python_name,
                a.graphql_name,
                ModuleBoundStrawberryAnnotation.from_annotation(a.type_annotation),
                a.is_subscription,
                a.description,
                a.default,
            )
            for a in args
        ]


def resolver_query_one(model: Type[IEntityModel]):
    return_type = Optional[model.get_strawberry_type().entity]
    data_type = GeneratedType.QUERY_ONE.get_typename(model.__name__)

    async def query_one(info: Info, data: data_type = UNSET) -> return_type:
        return await model.resolve(GraphQLOperation.QUERY_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(query_one))


def resolver_query_many(model: Type[IEntityModel]):
    return_type = List[model.get_strawberry_type().entity]
    data_type = GeneratedType.QUERY_MANY.get_typename(model.__name__)

    async def query_many(info: Info, data: Optional[data_type] = UNSET) -> return_type:
        return await model.resolve(GraphQLOperation.QUERY_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(query_many))


def resolver_create_one(model: Type[IEntityModel]):
    return_type = Optional[model.get_strawberry_type().entity]
    data_type = GeneratedType.CREATE_ONE.get_typename(model.__name__)

    async def create_one(info: Info, data: data_type) -> return_type:
        return await model.resolve(GraphQLOperation.CREATE_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(create_one))


def resolver_create_many(model: Type[IEntityModel]):
    return_type = List[Optional[model.get_strawberry_type().entity]]
    data_type = List[GeneratedType.CREATE_ONE.get_typename(model.__name__)]

    async def create_many(info: Info, data: data_type) -> return_type:
        return await model.resolve(GraphQLOperation.CREATE_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(create_many))


def resolver_update_one(model: Type[IEntityModel]):
    return_type = Optional[model.get_strawberry_type().entity]
    data_type = GeneratedType.UPDATE_ONE.get_typename(model.__name__)

    async def update_one(info: Info, data: data_type) -> return_type:
        return await model.resolve(GraphQLOperation.UPDATE_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(update_one))


def resolver_update_many(model: Type[IEntityModel]):
    return_type = List[Optional[model.get_strawberry_type().entity]]
    data_type = List[GeneratedType.UPDATE_ONE.get_typename(model.__name__)]

    async def update_many(info: Info, data: data_type) -> return_type:
        return await model.resolve(GraphQLOperation.UPDATE_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(update_many))


def resolver_delete_one(model: Type[IEntityModel]):
    data_type = GeneratedType.PRIMARY_KEY_FIELD.get_typename(model.__name__)

    async def delete_one(info: Info, data: data_type) -> DeleteResult:
        return await model.resolve(GraphQLOperation.DELETE_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(delete_one))


def resolver_delete_many(model: Type[IEntityModel]):
    data_type = List[GeneratedType.PRIMARY_KEY_FIELD.get_typename(model.__name__)]

    async def delete_many(info: Info, data: data_type) -> DeleteResult:
        return await model.resolve(GraphQLOperation.DELETE_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(delete_many))