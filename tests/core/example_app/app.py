from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

from tests.core.example_app.schema import schema


def app(debug=False):
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[
        Route('/', gql),
        WebSocketRoute('/', gql)
    ])
    return application
