import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from strawberry import Schema

from tests.sqlalchemy.example_app.schema import King, Weapon, Entity, Archer


@pytest.mark.asyncio
async def test_simple_query(schema: Schema, operations):
    result = await schema.execute(operations, operation_name="simpleQuery")

    assert result.errors is None

    assert len(result.data["archers"]) == 3
    assert len(result.data["weapons"]) == 8


@pytest.mark.asyncio
async def test_simple_create(schema: Schema, session: AsyncSession, operations):
    result = await schema.execute(operations, operation_name="simpleCreate")

    assert result.errors is None

    ids = sorted([e["id"] for e in result.data["createWeapons"]])
    assert await session.get(King, result.data["createKing"]["id"]) is not None
    assert len(result.data["createWeapons"]) == 2
    weapon_ids = (
        (await session.execute(select(Weapon.id).where(Weapon.id.in_(ids)).order_by(Weapon.id))).scalars().all()
    )
    assert weapon_ids == ids


@pytest.mark.asyncio
async def test_simple_update(schema: Schema, session: AsyncSession, operations):
    result = await schema.execute(
        operations,
        operation_name="simpleUpdate",
        variable_values={
            "entityId": 1,
            "weaponId": 6,
            "weaponId1": 2,
            "weaponId2": 3,
            "ownerId": 4,
        },
    )
    session.expire_all()

    assert result.errors is None

    results = sorted(result.data["updateWeapons"], key=lambda e: e["id"])
    entity = (
        await session.execute(select(Entity).where(Entity.id == 1).options(selectinload(Entity.weapons)).limit(1))
    ).scalar()
    assert [w.id for w in entity.weapons] == [6]
    assert result.data["updateEntity"]["weapons"] == [{"id": 6}]
    assert len(result.data["updateWeapons"]) == 2
    assert (await session.get(Weapon, 2)).damage == 123 == results[0]["damage"]
    assert (
        (await session.execute(select(Weapon).where(Weapon.id == 3).options(selectinload("owner")).limit(1)))
        .scalar()
        .owner.id
        == 4
        == results[1]["owner"]["id"]
    )


@pytest.mark.asyncio
async def test_simple_delete(schema: Schema, session: AsyncSession, operations):
    archer = (await session.execute(select(Archer).limit(1))).scalars().first()
    archer_id = archer.id
    assert await session.get(Weapon, 1) is not None
    assert await session.get(Weapon, 6) is not None

    result = await schema.execute(
        operations,
        operation_name="simpleDelete",
        variable_values={
            "archerId": archer_id,
            "weaponId1": 1,
            "weaponId2": 6,
        },
    )
    session.expire_all()

    assert result.errors is None

    assert result.data["deleteArcher"]["affectedRows"] == 1
    assert result.data["deleteWeapons"]["affectedRows"] == 2
    assert await session.get(Archer, archer_id) is None
    assert await session.get(Weapon, 1) is None
    assert await session.get(Weapon, 6) is None
