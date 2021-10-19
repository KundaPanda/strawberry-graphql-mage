from pathlib import Path

import pytest

from tests.api.example_app.schema import schema as strawberry_schema


@pytest.fixture(scope='function')
def schema():
    return strawberry_schema


@pytest.fixture(scope='function')
def operations():
    with open(Path(__file__).parent / 'graphql_operations' / 'operations.graphql', 'r') as f:
        data = f.read()
    return data
