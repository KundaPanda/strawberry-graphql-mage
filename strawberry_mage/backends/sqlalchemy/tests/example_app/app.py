from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

from strawberry_mage.backends.sqlalchemy.tests.example_app.schema import schema, Base, engine


def app(debug=False):
    Base.metadata.create_all(bind=engine)
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[
        Route('/', gql),
        WebSocketRoute('/', gql)
    ])
    return application
