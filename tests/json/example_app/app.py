from sqlalchemy.orm import declarative_base
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

Base = declarative_base()


def app(debug=False):
    from tests.json.example_app.schema import (
        Weapon,
        Entity,
        King,
        Archer,
        Mage,
        schema,
        schema_manager,
    )

    weapons = [
        {"__type__": "weapon", "id": 1, "damage": 10, "name": "mace"},
        {"__type__": "weapon", "id": 2, "damage": 10, "name": "bow"},
        {"__type__": "weapon", "id": 3, "damage": 13, "name": "one-handed sword"},
        {"__type__": "weapon", "id": 4, "damage": 17, "name": "crossbow"},
        {"__type__": "weapon", "id": 5, "damage": 17, "name": "blue crossbow"},
        {"__type__": "weapon", "id": 6, "damage": 20, "name": "two-handed sword"},
        {"__type__": "weapon", "id": 7, "damage": 30, "name": "lightning wand"},
        {"__type__": "weapon", "id": 8, "damage": 31, "name": "fire staff"},
    ]
    king1 = {"__type__": "king", "id": 1, "name": "Vizimir II"}
    king2 = {
        "__type__": "king",
        "id": 2,
        "name": "Radovid V",
        "submits_to": king1,
        "weapons": [weapons[5]],
    }
    entities = [
        {"__type__": "entity", "id": 3},
        {"__type__": "entity", "id": 4, "submits_to": king2},
        {"__type__": "entity", "id": 5, "submits_to": king1, "weapons": [weapons[0]]},
        {
            "__type__": "archer",
            "id": 6,
            "submits_to": king1,
            "weapons": [weapons[1]],
            "draw_strength": 30,
        },
        {"__type__": "archer", "id": 7, "weapons": weapons[3:4], "draw_strength": 16},
        {"__type__": "archer", "id": 8, "submits_to": king1, "draw_strength": 40},
        {
            "__type__": "mage",
            "id": 9,
            "submits_to": king1,
            "power_source": Mage.MageTypeEnum.AIR,
            "weapons": [weapons[-2]],
        },
        {
            "__type__": "mage",
            "id": 10,
            "submits_to": king2,
            "power_source": Mage.MageTypeEnum.FIRE,
            "weapons": [weapons[-1]],
        },
    ]

    def resolve_type(entity: dict):
        return {
            "weapon": Weapon,
            "entity": Entity,
            "king": King,
            "archer": Archer,
            "mage": Mage,
        }[entity["__type__"]]

    data = [*weapons, king1, king2, *entities]
    schema_manager.backend.add_dataset(data, model_mapper=resolve_type)
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[Route("/", gql), WebSocketRoute("/", gql)])
    return application