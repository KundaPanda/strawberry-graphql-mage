import pytest
from sqlalchemy.orm import Session
from strawberry import Schema

from strawberry_mage.backends.sqlalchemy.tests.example_app.schema import King, Weapon, Entity, Archer


@pytest.mark.asyncio
async def test_simple_query(schema: Schema, operations):
    result = await schema.execute(operations, operation_name='simpleQuery')

    assert result.errors is None

    assert len(result.data['archers']) == 3
    assert len(result.data['weapons']) == 8


@pytest.mark.asyncio
async def test_simple_create(schema: Schema, session: Session, operations):
    result = await schema.execute(operations, operation_name='simpleCreate')

    assert result.errors is None

    ids = sorted([e['id'] for e in result.data['createWeapons']], key=lambda e: e['id'])
    assert session.get(King, result.data['createKing']['id']) is not None
    assert len(result.data['createWeapons']) == 2
    assert [e[0] for e in session.query(Weapon.id).where(Weapon.id.in_(ids)).order_by(Weapon.id)] == ids


@pytest.mark.asyncio
async def test_simple_update(schema: Schema, session: Session, operations):
    result = await schema.execute(operations, operation_name='simpleUpdate', variable_values={
        'entityId': 1, 'weaponId': 6, 'weaponId1': 2, 'weaponId2': 3, 'ownerId': 4
    })

    assert result.errors is None

    results = sorted(result.data['updateWeapons'], key=lambda e: e['id'])
    assert [w.id for w in session.get(Entity, 1).weapons] == [6]
    assert result.data['updateEntity']['weapons'] == [{'id': 6}]
    assert len(result.data['updateWeapons']) == 2
    assert session.get(Weapon, 2).damage == 1 == results[0]['damage']
    assert session.get(Weapon, 3).owner.id == 4 == results[1]['owner']['id']


@pytest.mark.asyncio
async def test_simple_delete(schema: Schema, session: Session, operations):
    archer = session.query(Archer).first()
    archer_id = archer.id
    assert session.get(Weapon, 1) is not None
    assert session.get(Weapon, 6) is not None

    result = await schema.execute(operations, operation_name='simpleDelete', variable_values={
        'archerId': archer_id, 'weaponId1': 1, 'weaponId2': 6,
    })
    session.expire_all()

    assert result.errors is None

    assert result.data['deleteArcher']['affectedRows'] == 1
    assert result.data['deleteWeapons']['affectedRows'] == 2
    assert session.get(Archer, archer_id) is None
    assert session.get(Weapon, 1) is None
    assert session.get(Weapon, 6) is None
