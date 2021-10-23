import json
from typing import Any, Callable, Dict, Iterable, Optional, Set, Type

from strawberry.types import Info

from strawberry_mage.backends.api.backend import APIBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.types import GraphQLOperation, IEntityModel
from tests.api.example_app.api import graphql_app


class CustomBackend(APIBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _build_graphql_input(self, root: str, op: str, entry: Dict[str, Any]):
        pk_arg = entry.get("primaryKey_", {}).get("id")
        arg = {k: v for k, v in entry.items() if k != "primaryKey_"}
        args = "( "
        if pk_arg:
            args += f"pk: {pk_arg}"
        for name, value in arg.items():
            if name != "id":
                if isinstance(value, list) and len(value) > 0:
                    value = [json.loads(v["primaryKey_"]["id"]) for v in value]
                if len(args) > 2:
                    args += ", "
                args += f"{name}: {value}"
        args += ")"
        query_string = f"""
        {root} {{
            {op}{args if arg or (args != '( )') else ''} {{
                id
                __typename
                weapons {{
                    id
                    __typename
                    damage
                }}
            }}
        }}
        """
        if op == "delete":
            query_string = f"""
            {root} {{
                {op}{args if arg or (args != '( )') else ''}
            }}
            """
        return query_string

    async def api_resolve(
            self,
            model: Type[PythonEntityModel],
            operation: GraphQLOperation,
            info: Info,
            data: Any,
    ):
        op = {
            GraphQLOperation.QUERY_ONE: "retrieve",
            GraphQLOperation.QUERY_MANY: "list",
            GraphQLOperation.CREATE_ONE: "create",
            GraphQLOperation.CREATE_MANY: "create",
            GraphQLOperation.UPDATE_ONE: "update",
            GraphQLOperation.UPDATE_MANY: "update",
            GraphQLOperation.DELETE_ONE: "delete",
            GraphQLOperation.DELETE_MANY: "delete",
        }.get(operation)
        root = "query" if operation in {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY} else "mutation"
        field = info.selected_fields[0]
        data = field.arguments.get("data", {})
        results = []
        if isinstance(data, list):
            for entry in data:
                results.append((await graphql_app.execute(self._build_graphql_input(root, op, entry))).data[op])
            if operation == GraphQLOperation.DELETE_MANY:
                return sum(results)
            return results
        query_string = self._build_graphql_input(root, op, data)
        result = await graphql_app.execute(query_string)
        return result.data[op]

    def add_dataset(
            self,
            dataset: Iterable[dict],
            model: Optional[Type[PythonEntityModel]] = None,
            model_mapper: Callable[[dict], Type[PythonEntityModel]] = None,
    ):
        from tests.api.example_app.schema import Entity, Weapon

        mapping = {"TestEntity": Entity, "TestWeapon": Weapon}

        def get_model(entry: dict):
            return mapping[entry["__typename"]]

        return super().add_dataset(dataset, model_mapper=get_model)

    def get_operations(self, model: Type[IEntityModel]) -> Set[GraphQLOperation]:
        return {
            GraphQLOperation.QUERY_ONE,
            GraphQLOperation.QUERY_MANY,
            GraphQLOperation.CREATE_ONE,
            GraphQLOperation.CREATE_MANY,
            GraphQLOperation.UPDATE_ONE,
            GraphQLOperation.UPDATE_MANY,
            GraphQLOperation.DELETE_ONE,
            GraphQLOperation.DELETE_MANY,
        }

    async def resolve(
            self,
            model: Type[PythonEntityModel],
            operation: GraphQLOperation,
            info: Info,
            data: Any,
            *args,
            **kwargs
    ) -> Any:
        api_dataset = await self.api_resolve(model, operation, info, data)
        return await super().resolve(model, operation, info, data, dataset=api_dataset)
