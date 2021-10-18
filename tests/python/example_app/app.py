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
    from tests.python.example_app.schema import Weapon, Entity, King, Archer, Mage, schema, schema_manager
    weapons = [
        Weapon(damage=10, name='mace'),
        Weapon(damage=10, name='bow'),
        Weapon(damage=13, name='one-handed sword'),
        Weapon(damage=17, name='crossbow'),
        Weapon(damage=17, name='blue crossbow'),
        Weapon(damage=20, name='two-handed sword'),
        Weapon(damage=30, name='lightning wand'),
        Weapon(damage=31, name='fire staff'),
    ]
    king1 = King(name='Vizimir II')
    king2 = King(name='Radovid V', submits_to=king1, weapons=[weapons[5]])
    entities = [
        Entity(),
        Entity(submits_to=king2),
        Entity(submits_to=king1, weapons=[weapons[0]]),
        Archer(submits_to=king1, weapons=[weapons[1]], draw_strength=30),
        Archer(weapons=weapons[3:4], draw_strength=16),
        Archer(draw_strength=40, submits_to=king1),
        Mage(weapons=[weapons[-2]], submits_to=king1, power_source=Mage.MageTypeEnum.AIR),
        Mage(weapons=[weapons[-1]], submits_to=king2, power_source=Mage.MageTypeEnum.FIRE),
    ]
    data = [*weapons, king1, king2, *entities]
    schema_manager.backend.add_dataset(data)
    gql = GraphQL(schema)
    application = Starlette(debug, routes=[
        Route('/', gql),
        WebSocketRoute('/', gql)
    ])
    return application


if __name__ == '__main__':
    asyncio.run(main())
