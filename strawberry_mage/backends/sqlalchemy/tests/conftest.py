from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from strawberry_mage.backends.sqlalchemy.tests.example_app.schema import schema as strawberry_schema
from strawberry_mage.backends.sqlalchemy.tests.example_app.schema import *


@pytest.fixture(scope='function', autouse=True)
def prepare_database():
    Base.metadata.create_all(bind=engine)
    s = Session(engine)
    s.begin()
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
    s.add_all(weapons)
    s.flush()
    king1 = King(name='Vizimir II')
    s.add(king1)
    s.flush()
    king2 = King(name='Radovid V', submits_to=king1, weapons=[weapons[5]])
    s.add(king2)
    s.flush()
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
    s.add_all(entities)
    s.commit()
    s.close()
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
