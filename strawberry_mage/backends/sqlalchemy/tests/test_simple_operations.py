import pytest
from strawberry import Schema


@pytest.mark.asyncio
async def test_simple_query(schema: Schema, operations):
    result = await schema.execute(operations, operation_name='simpleQuery')

    assert result.errors is None

    assert len(result.data['archers']) == 3
    assert len(result.data['weapons']) == 8
