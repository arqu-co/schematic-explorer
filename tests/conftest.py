"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture(autouse=True)
def reset_carrier_cache():
    """Reset the carrier cache before each test.

    This ensures tests are isolated and don't depend on
    carrier loading state from other tests.
    """
    from schematic_explorer.extractor import _KNOWN_CARRIERS, _NON_CARRIERS

    # Clear the cache before each test
    _KNOWN_CARRIERS.clear()
    _NON_CARRIERS.clear()

    yield

    # Clear again after test
    _KNOWN_CARRIERS.clear()
    _NON_CARRIERS.clear()
