import asyncio
from asyncio import Queue
from timeit import default_timer

from sqlalchemy import Column, Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from strawberry.asgi import GraphQL

Base = declarative_base()


async def cleanup_engine(engine: AsyncEngine, engines: Queue):
    async with AsyncSession(engine) as session:
        for m in Base.metadata.sorted_tables:
            await session.run_sync(lambda s: s.query(m).delete())
    await engines.put(engine)


async def main():
    iterations = 1000
    engines_count = 200
    tables = 15
    models = []
    for i in range(tables):
        models.append(
            type(f'Model_{i}', (Base,), {'__tablename__': f'model_{i}', 'id': Column(Integer, primary_key=True)}))
    engines = Queue()
    for _ in range(engines_count):
        e = create_async_engine('sqlite+aiosqlite://')
        future = asyncio.create_task(engines.put(e))
        async with e.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await future
    start = default_timer()
    for _ in range(iterations):
        while engines.empty():
            await asyncio.sleep(0.1)
        engine = engines.get_nowait()
        asyncio.create_task(cleanup_engine(engine, engines))
    await asyncio.gather(*[t for t in asyncio.all_tasks() if t.get_coro().__name__ != main.__name__])
    end = default_timer()
    print(f'{iterations} iterations took {end - start} seconds')
    print(f'One iteration took {(end - start) / iterations * 1000} milliseconds')


def app(debug=False):
    from strawberry_mage.backends.json.tests.example_app.schema import Weapon, Entity, King, Archer, Mage, schema, schema_manager
    weapons = [
        {'__type__': 'weapon', 'id': 1, 'damage': 10, 'name': 'mace'},
        {'__type__': 'weapon', 'id': 2, 'damage': 10, 'name': 'bow'},
        {'__type__': 'weapon', 'id': 3, 'damage': 13, 'name': 'one-handed sword'},
        {'__type__': 'weapon', 'id': 4, 'damage': 17, 'name': 'crossbow'},
        {'__type__': 'weapon', 'id': 5, 'damage': 17, 'name': 'blue crossbow'},
        {'__type__': 'weapon', 'id': 6, 'damage': 20, 'name': 'two-handed sword'},
        {'__type__': 'weapon', 'id': 7, 'damage': 30, 'name': 'lightning wand'},
        {'__type__': 'weapon', 'id': 8, 'damage': 31, 'name': 'fire staff'},
    ]
    king1 = {'__type__': 'king', 'id': 1, 'name': 'Vizimir II'}
    king2 = {'__type__': 'king', 'id': 2, 'name': 'Radovid V', 'submits_to': king1, 'weapons': [weapons[5]]}
    entities = [
        {'__type__': 'entity', 'id': 3},
        {'__type__': 'entity', 'id': 4, 'submits_to': king2},
        {'__type__': 'entity', 'id': 5, 'submits_to': king1, 'weapons': [weapons[0]]},
        {'__type__': 'archer', 'id': 6, 'submits_to': king1, 'weapons': [weapons[1]], 'draw_strength': 30},
        {'__type__': 'archer', 'id': 7, 'weapons': weapons[3:4], 'draw_strength': 16},
        {'__type__': 'archer', 'id': 8, 'submits_to': king1, 'draw_strength': 40},
        {'__type__': 'mage', 'id': 9, 'submits_to': king1, 'power_source': Mage.MageTypeEnum.AIR,
         'weapons': [weapons[-2]]},
        {'__type__': 'mage', 'id': 10, 'submits_to': king2, 'power_source': Mage.MageTypeEnum.FIRE,
         'weapons': [weapons[-1]]},
    ]

    def resolve_type(entity: dict):
        return {
            'weapon': Weapon,
            'entity': Entity,
            'king': King,
            'archer': Archer,
            'mage': Mage,
        }[entity['__type__']]

    data = [*weapons, king1, king2, *entities]
    schema_manager.backend.add_dataset(data, model_mapper=resolve_type)
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[
        Route('/', gql),
        WebSocketRoute('/', gql)
    ])
    return application


if __name__ == '__main__':
    asyncio.run(main())
