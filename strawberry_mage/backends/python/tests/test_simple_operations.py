import pytest
from strawberry import Schema

from strawberry_mage.backends.python.tests.example_app.schema import backend


@pytest.mark.asyncio
async def test_simple_query(schema: Schema, dataset, operations):
    result = await schema.execute(operations, operation_name='simpleQuery')

    assert result.errors is None

    assert len(result.data['archers']) == 3
    assert len(result.data['weapons']) == 8
