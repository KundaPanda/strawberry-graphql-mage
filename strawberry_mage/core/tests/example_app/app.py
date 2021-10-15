from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

from strawberry_mage.core.tests.example_app.schema import schema


def app(debug=False):
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[
        Route('/', gql),
        WebSocketRoute('/', gql)
    ])
    return application
