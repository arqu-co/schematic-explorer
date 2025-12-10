"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture(autouse=True)
def reset_carrier_cache():
    """Reset the carrier cache before each test.

    This ensures tests are isolated and don't depend on
    carrier loading state from other tests.
    """
    from schematic_explorer.carriers import get_carrier_data

    # Clear the functools.cache before each test
    get_carrier_data.cache_clear()

    yield

    # Clear again after test
    get_carrier_data.cache_clear()
