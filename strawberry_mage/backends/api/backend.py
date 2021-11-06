"""Backend for relaying calls to other JSON APIs."""

import dataclasses
from typing import Any, Iterable, List, Optional, Type, cast

from overrides import overrides
from strawberry.type import StrawberryType
from strawberry.types import Info
from strawberry.types.nodes import SelectedField

from strawberry_mage.backends.json.backend import JSONBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.strawberry_types import IntegerFilter
from strawberry_mage.core.types import GraphQLOperation


class APIBackend(JSONBackend):
    """Backend for relaying calls to other JSON APIs."""

    @overrides
    async def resolve(
        self,
        model: Type[PythonEntityModel],
        operation: GraphQLOperation,
        info: Info,
        data: Any,
        *args,
        dataset: Optional[Iterable] = None,
        **kwargs
    ) -> Any:

        if isinstance(dataset, list):
            if operation == GraphQLOperation.DELETE_MANY:
                delete_type = model.get_strawberry_type().delete_many
                assert delete_type is not None  # for pyright
                assert not isinstance(delete_type.type, StrawberryType)  # for pyright
                return delete_type.type(affected_rows=len(dataset))
            if operation in {
                GraphQLOperation.UPDATE_MANY,
                GraphQLOperation.CREATE_MANY,
            }:
                types = model.get_strawberry_type().graphql_input_types
                filter_type = dataclasses.make_dataclass("FilterStub", {"id": IntegerFilter})
                data = types["query_many_input"](
                    page_size=len(dataset),
                    filters=[filter_type(id=IntegerFilter(in_=[entry["id"] for entry in dataset]))],
                )
                field = cast(List[SelectedField], info.selected_fields)[0]
                field.selections = [
                    SelectedField(
                        "results",
                        selections=field.selections,
                        arguments={},
                        alias=None,
                        directives={},
                    )
                ]
            result = await super().resolve(
                model, GraphQLOperation.QUERY_MANY, info, data, *args, dataset=dataset, **kwargs
            )
            return result.results if operation != GraphQLOperation.QUERY_MANY else result
        if isinstance(dataset, dict):
            if operation == GraphQLOperation.DELETE_ONE:
                delete_type = model.get_strawberry_type().delete_one
                assert delete_type is not None  # for pyright
                assert not isinstance(delete_type.type, StrawberryType)  # for pyright
                return delete_type.type(affected_rows=dataset.get("affected_rows", 1))
            if operation in {GraphQLOperation.UPDATE_ONE, GraphQLOperation.CREATE_ONE}:
                types = model.get_strawberry_type().graphql_input_types
                data = types["query_one_input"](types["primary_key_input"](dataset["id"]))
                operation = GraphQLOperation.QUERY_ONE
            return await super().resolve(model, operation, info, data, *args, dataset=[dataset], **kwargs)
        if isinstance(dataset, int):
            delete_type = model.get_strawberry_type().delete_one
            assert delete_type is not None  # for pyright
            assert not isinstance(delete_type.type, StrawberryType)  # for pyright
            return delete_type.type(affected_rows=dataset)
