import pytest
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload, aliased
from strawberry import Schema

from tests.sqlalchemy.example_app.schema import Archer, King, Weapon, Entity


@pytest.mark.asyncio
async def test_nested_select(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name='nestedSelectQuery')

    assert result.errors is None

    archers = (await session.execute(select(Archer).options(joinedload(Archer.submits_to).joinedload(King.subjects),
                                                            joinedload(Archer.weapons)))).unique().scalars().all()
    assert len(result.data['archers']) == len(archers)
    for archer in archers:
        selected, = [a for a in result.data['archers'] if a['id'] == archer.id]
        if archer.submits_to:
            assert archer.submits_to.id == selected['submitsTo']['id']
            if archer.submits_to.subjects:
                assert sorted([{'id': s.id} for s in archer.submits_to.subjects], key=lambda s: s['id']) == \
                       selected['submitsTo']['subjects']
        else:
            assert selected.get('submitsTo') == archer.submits_to
        if archer.weapons:
            assert [{'damage': w.damage, 'id': w.id} for w in archer.weapons] == selected['weapons']
        else:
            assert selected.get('weapons') == archer.weapons


@pytest.mark.asyncio
async def test_nested_filter(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name='nestedFilterQuery')

    assert result.errors is None

    k = aliased(King)
    w = aliased(Weapon)
    archers = (await session.execute(select(Archer)
                                     .join(k, Archer.submits_to)
                                     .join(w, k.weapons)
                                     .where(Archer.submits_to.__ne__(None))
                                     .where(k.weapons.any())
                                     .where(w.damage > 10)
                                     )).unique().scalars().all()
    assert len(result.data['archers']) == len(archers)
    assert sorted([a.id for a in archers]) == [r['id'] for r in result.data['archers']]


@pytest.mark.asyncio
async def test_nested_ordering(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name='nestedOrderingQuery')

    assert result.errors is None

    k = aliased(King)
    w = aliased(Weapon)
    archers = (await session.execute(select(Archer)
                                     .outerjoin(k, Archer.submits_to)
                                     .outerjoin(w, Archer.weapons)
                                     .order_by(desc(w.damage), desc(Archer.draw_strength), desc(Archer.id))
                                     )).unique().scalars().all()
    assert len(result.data['archers']) == len(archers)
    assert [r['id'] for r in result.data['archers']] == [a.id for a in archers]


@pytest.mark.asyncio
async def test_polymorphic_fragment(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name='fragmentQuery')

    assert result.errors is None

    entities = (await session.execute(select(Entity))).unique().scalars().all()
    assert len(result.data['entities']) == len(entities)
    assert [r['id'] for r in result.data['entities']] == [a.id for a in entities]
