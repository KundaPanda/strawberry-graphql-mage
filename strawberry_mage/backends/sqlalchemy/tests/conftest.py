from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from strawberry_mage.backends.sqlalchemy.tests.example_app.schema import *
from strawberry_mage.backends.sqlalchemy.tests.example_app.schema import schema as strawberry_schema


@pytest.fixture(scope='function')
def session():
    Base.metadata.create_all(bind=engine)
    s = Session(engine)
    s.begin()
    yield s
    s.close()


@pytest.fixture(scope='function', autouse=True)
def prepare_database(session):
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
    session.flush()
    king1 = King(name='Vizimir II')
    session.add(king1)
    session.flush()
    king2 = King(name='Radovid V', submits_to=king1, weapons=[weapons[5]])
    session.add(king2)
    session.flush()
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
    session.add_all(entities)
    session.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope='function')
def schema():
    return strawberry_schema


@pytest.fixture(scope='function')
def operations():
    with open(Path(__file__).parent / 'example_app' / 'graphql_operations' / 'operations.graphql', 'r') as f:
        data = f.read()
    return data
