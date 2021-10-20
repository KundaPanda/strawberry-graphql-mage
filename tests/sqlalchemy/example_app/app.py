import asyncio

from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

from tests.sqlalchemy.example_app.schema import schema, Base, engine


def app(debug=False):
    async def set_up():
        async with engine.begin() as s:
            await s.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().create_task(set_up()).__await__()
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[Route("/", gql), WebSocketRoute("/", gql)])
    return application
