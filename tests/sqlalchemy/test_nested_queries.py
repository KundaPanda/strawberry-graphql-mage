import pytest
from sqlalchemy import desc, select
from sqlalchemy.orm import aliased, joinedload
from strawberry import Schema

from tests.sqlalchemy.example_app.schema import Archer, Entity, King, Weapon


# @pytest.mark.asyncio
# async def test_asdt(schema: Schema, operations, session):
#     t = with_polymorphic(Title, '*', aliased=True)
#     t1 = with_polymorphic(Title, '*', aliased=True)
#     q = select(Entity)
#     sq = select(Entity).join(t1, Entity.titles).where(t1.name == 'squire').subquery()
#     expr = q.join(sq, Entity.id == sq.c.id).join(t, Entity.titles).options(contains_eager(Entity.titles.of_type(t)))
#     res = (await session.execute(expr)).unique().scalars().all()
#     print(res)


@pytest.mark.asyncio
async def test_nested_select(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name="nestedSelectQuery")

    assert result.errors is None
    data = result.data["archers"]["results"]

    archers = (
        (
            await session.execute(
                select(Archer).options(
                    joinedload(Archer.submits_to).joinedload(King.subjects),
                    joinedload(Archer.weapons),
                )
            )
        )
        .unique()
        .scalars()
        .all()
    )
    assert len(data) == len(archers)
    assert any((a["titles"][0].get("name")) == "personal guard" for a in data if a["titles"])
    for archer in archers:
        (selected,) = [a for a in data if a["id"] == archer.id]
        if archer.submits_to:
            assert archer.submits_to.id == selected["submitsTo"]["id"]
            if archer.submits_to.subjects:
                assert (
                    sorted(
                        [{"id": s.id} for s in archer.submits_to.subjects],
                        key=lambda s: s["id"],
                    )
                    == selected["submitsTo"]["subjects"]
                )
        else:
            assert selected.get("submitsTo") == archer.submits_to
        if archer.weapons:
            assert [{"damage": w.damage, "id": w.id} for w in archer.weapons] == selected["weapons"]
        else:
            assert selected.get("weapons") == archer.weapons


@pytest.mark.asyncio
async def test_nested_filter(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name="nestedFilterQuery")

    assert result.errors is None
    data = result.data["archers"]["results"]

    k = aliased(King)
    w = aliased(Weapon)
    archers = (
        (
            await session.execute(
                select(Archer)
                .join(k, Archer.submits_to)
                .join(w, k.weapons)
                .where(Archer.submits_to.__ne__(None))
                .where(k.weapons.any())
                .where(w.damage > 10)
            )
        )
        .unique()
        .scalars()
        .all()
    )
    assert len(data) == len(archers)
    assert sorted([a.id for a in archers]) == [r["id"] for r in data]


@pytest.mark.asyncio
async def test_nested_ordering(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name="nestedOrderingQuery")

    assert result.errors is None
    data = result.data["archers"]["results"]

    k = aliased(King)
    w = aliased(Weapon)
    archers = (
        (
            await session.execute(
                select(Archer)
                .outerjoin(k, Archer.submits_to)
                .outerjoin(w, Archer.weapons)
                .order_by(desc(w.damage), desc(Archer.draw_strength), desc(Archer.id))
            )
        )
        .unique()
        .scalars()
        .all()
    )
    assert len(data) == len(archers)
    assert [r["id"] for r in data] == [a.id for a in archers]


@pytest.mark.asyncio
async def test_polymorphic_fragment(schema: Schema, operations, session):
    result = await schema.execute(operations, operation_name="fragmentQuery")

    assert result.errors is None
    data = result.data["entities"]["results"]

    entities = (await session.execute(select(Entity))).unique().scalars().all()
    assert len(data) == len(entities)
    assert [r["id"] for r in data] == [a.id for a in entities]
