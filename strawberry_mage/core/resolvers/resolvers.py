"""Strawberry resolvers for crud fields."""

from typing import List, Optional, Type

import strawberry
from strawberry import UNSET
from strawberry.types import Info

from strawberry_mage.core.resolvers.base import ModuleBoundStrawberryResolver
from strawberry_mage.core.strawberry_types import DeleteResult
from strawberry_mage.core.resolvers.base import GeneratedType
from strawberry_mage.core.types import (
    GraphQLOperation,
    IEntityModel,
)


def resolver_query_one(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for retrieving one entity.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    return_type = Optional[model.get_strawberry_type().entity]  # type: ignore
    data_type = GeneratedType.QUERY_ONE.get_typename(model.__name__)  # type: ignore

    async def query_one(info: Info, data: data_type = UNSET) -> return_type:  # type: ignore
        return await model.resolve(GraphQLOperation.QUERY_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(query_one))


def resolver_query_many(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for listing entities.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    return_type = model.get_strawberry_type().query_many_output  # type: ignore
    data_type = GeneratedType.QUERY_MANY_INPUT.get_typename(model.__name__)  # type: ignore

    async def query_many(info: Info, data: Optional[data_type] = UNSET) -> return_type:  # type: ignore
        return await model.resolve(GraphQLOperation.QUERY_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(query_many))


def resolver_create_one(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for creating one entity.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    return_type = Optional[model.get_strawberry_type().entity]  # type: ignore
    data_type = GeneratedType.CREATE_ONE.get_typename(model.__name__)  # type: ignore

    async def create_one(info: Info, data: data_type) -> return_type:  # type: ignore
        return await model.resolve(GraphQLOperation.CREATE_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(create_one))


def resolver_create_many(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for creating many entities.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    return_type = List[Optional[model.get_strawberry_type().entity]]  # type: ignore
    data_type = List[GeneratedType.CREATE_ONE.get_typename(model.__name__)]  # type: ignore

    async def create_many(info: Info, data: data_type) -> return_type:
        return await model.resolve(GraphQLOperation.CREATE_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(create_many))


def resolver_update_one(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for updating one entity.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    return_type = Optional[model.get_strawberry_type().entity]  # type: ignore
    data_type = GeneratedType.UPDATE_ONE.get_typename(model.__name__)  # type: ignore

    async def update_one(info: Info, data: data_type) -> return_type:  # type: ignore
        return await model.resolve(GraphQLOperation.UPDATE_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(update_one))


def resolver_update_many(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for updating multiple entities.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    return_type = List[Optional[model.get_strawberry_type().entity]]  # type: ignore
    data_type = List[GeneratedType.UPDATE_ONE.get_typename(model.__name__)]  # type: ignore

    async def update_many(info: Info, data: data_type) -> return_type:
        return await model.resolve(GraphQLOperation.UPDATE_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(update_many))


def resolver_delete_one(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for deleting one entity.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    data_type = GeneratedType.PRIMARY_KEY_FIELD.get_typename(model.__name__)  # type: ignore

    async def delete_one(info: Info, data: data_type) -> DeleteResult:  # type: ignore
        return await model.resolve(GraphQLOperation.DELETE_ONE, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(delete_one))


def resolver_delete_many(model: Type[IEntityModel]):
    """
    Create strawberry field resolver for deleting many entities.

    :param model: entity model to use for the resolver
    :return: strawberry field resolver
    """
    data_type = List[GeneratedType.PRIMARY_KEY_FIELD.get_typename(model.__name__)]  # type: ignore

    async def delete_many(info: Info, data: data_type) -> DeleteResult:
        return await model.resolve(GraphQLOperation.DELETE_MANY, info, data)

    return strawberry.field(ModuleBoundStrawberryResolver(delete_many))
