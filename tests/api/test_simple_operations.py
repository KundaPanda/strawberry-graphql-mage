import pytest
from strawberry import Schema


@pytest.mark.asyncio
async def test_simple_query(schema: Schema, operations):
    result = await schema.execute(operations, operation_name='simpleQuery')

    assert result.errors is None

    assert len(result.data['entities']) == 3
    assert result.data['entity'] == {'id': 1, '__typename': 'Entity_', 'weapons': [{'id': 1}]}


@pytest.mark.asyncio
async def test_simple_create(schema: Schema, operations):
    result = await schema.execute(operations, operation_name='simpleCreate')

    assert result.errors is None

    assert result.data['createEntity'] == {'id': 101, '__typename': 'Entity_', 'weapons': []}
    assert result.data['createEntities'] == [
        {'id': 102, '__typename': 'Entity_', 'weapons': []},
        {'id': 103, '__typename': 'Entity_', 'weapons': [{'id': 1}]}
    ]


@pytest.mark.asyncio
async def test_simple_update(schema: Schema, operations):
    result = await schema.execute(operations, operation_name='simpleUpdate')

    assert result.errors is None

    assert result.data['updateEntity'] == {'id': 1, '__typename': 'Entity_', 'weapons': [{'id': 1}]}
    assert result.data['updateEntities'] == [
        {'id': 1, '__typename': 'Entity_', 'weapons': []},
        {'id': 2, '__typename': 'Entity_', 'weapons': [{'id': 1}]}
    ]


@pytest.mark.asyncio
async def test_simple_delete(schema: Schema, operations):
    result = await schema.execute(operations, operation_name='simpleDelete')

    assert result.errors is None

    assert result.data['deleteEntity'] == {'affectedRows': 1}
    assert result.data['deleteEntities'] == {'affectedRows': 2}
