import dataclasses
from typing import Any, Iterable, Optional, Type

from strawberry.arguments import UNSET
from strawberry.types import Info

from strawberry_mage.backends.json.backend import JSONBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.strawberry_types import IntegerFilter
from strawberry_mage.core.types import GraphQLOperation


class APIBackend(JSONBackend):
    async def resolve(
            self,
            model: Type[PythonEntityModel],
            operation: GraphQLOperation,
            info: Info,
            data: Any,
            dataset: Optional[Iterable] = None,
            *args,
            **kwargs
    ) -> Any:

        if isinstance(dataset, list):
            if operation == GraphQLOperation.DELETE_MANY:
                return model.get_strawberry_type().delete_one.type(
                    affected_rows=len(dataset)
                )
            if operation in {
                GraphQLOperation.UPDATE_MANY,
                GraphQLOperation.CREATE_MANY,
            }:
                types = model.get_strawberry_type().graphql_input_types
                filter_type = dataclasses.make_dataclass(
                    "FilterStub", {"id": IntegerFilter}
                )
                data = types["query_many_input"](
                    page_size=UNSET,
                    filters=[
                        filter_type(
                            id=IntegerFilter(in_=[entry["id"] for entry in dataset])
                        )
                    ],
                )
                operation = GraphQLOperation.QUERY_MANY
            return await super().resolve(model, operation, info, data, dataset=dataset)
        if isinstance(dataset, dict):
            if operation == GraphQLOperation.DELETE_ONE:
                return model.get_strawberry_type().delete_one.type(
                    affected_rows=dataset.get("affected_rows", 1)
                )
            if operation in {GraphQLOperation.UPDATE_ONE, GraphQLOperation.CREATE_ONE}:
                types = model.get_strawberry_type().graphql_input_types
                data = types["query_one_input"](
                    types["primary_key_input"](dataset["id"])
                )
                operation = GraphQLOperation.QUERY_ONE
            return await super().resolve(model, operation, info, data, dataset=[dataset])
        if isinstance(dataset, int):
            return model.get_strawberry_type().delete_one.type(affected_rows=dataset)
