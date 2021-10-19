from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from tests.sqlalchemy.example_app.schema import *
from tests.sqlalchemy.example_app.schema import schema as strawberry_schema


@pytest.fixture(scope='function')
async def session() -> AsyncSession:
    async with engine.begin() as s:
        await s.run_sync(Base.metadata.create_all)
    async with sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)() as s:
        yield s


@pytest.fixture(scope='function', autouse=True)
async def prepare_database(session):
    async with session.begin():
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
        session.add_all(weapons)
        await session.flush()
        king1 = King(name='Vizimir II')
        session.add(king1)
        await session.flush()
        king2 = King(name='Radovid V', submits_to=king1, weapons=[weapons[5]])
        session.add(king2)
        await session.flush()
        entities = [
            Entity(),
            Entity(submits_to=king2),
            Entity(submits_to=king1, weapons=[weapons[0]]),
            Archer(submits_to=king1, weapons=[weapons[1]], draw_strength=30),
            Archer(weapons=weapons[3:4], draw_strength=16),
            Archer(draw_strength=40, submits_to=king2),
            Mage(weapons=[weapons[-2]], submits_to=king1, power_source=Mage.MageTypeEnum.AIR),
            Mage(weapons=[weapons[-1]], submits_to=king2, power_source=Mage.MageTypeEnum.FIRE),
        ]
        session.add_all(entities)
        await session.commit()
    data = [*weapons, king1, king2, *entities]
    yield data
    async with engine.begin() as s:
        await s.run_sync(Base.metadata.drop_all, checkfirst=False)


@pytest.fixture(scope='function')
def schema():
    return strawberry_schema


@pytest.fixture(scope='function')
def operations():
    with open(Path(__file__).parent / 'graphql_operations' / 'operations.graphql', 'r') as f:
        data = f.read()
    return data
