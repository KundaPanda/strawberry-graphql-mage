from pathlib import Path

import pytest

from strawberry_mage.backends.api.tests.example_app.schema import schema as strawberry_schema


@pytest.fixture(scope='function')
def schema():
    return strawberry_schema


@pytest.fixture(scope='function')
def operations():
    with open(Path(__file__).parent / 'example_app' / 'graphql_operations' / 'operations.graphql', 'r') as f:
        data = f.read()
    return data
