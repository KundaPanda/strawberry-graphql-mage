from sqlalchemy.orm import declarative_base
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

Base = declarative_base()


def app(debug=False):
    from tests.api.example_app.schema import schema

    gql = GraphQL(schema)
    application = Starlette(debug, routes=[Route("/", gql), WebSocketRoute("/", gql)])
    return application
