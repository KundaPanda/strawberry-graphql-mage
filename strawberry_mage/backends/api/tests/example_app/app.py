from sqlalchemy.orm import declarative_base
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

Base = declarative_base()


def app(debug=False):
    from strawberry_mage.backends.api.tests.example_app.schema import Weapon, Entity, King, Archer, Mage, schema, \
        schema_manager
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[
        Route('/', gql),
        WebSocketRoute('/', gql)
    ])
    return application
