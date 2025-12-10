"""Tests for carrier detection and validation module."""

import pytest

from schematic_explorer.carriers import (
    get_carrier_data,
    _normalize_for_match,
    _is_known_carrier,
    _is_non_carrier,
    _looks_like_policy_number,
)


class TestCarrierDataLoading:
    """Test lazy-loaded carrier data."""

    def test_get_carrier_data_returns_frozen_sets(self):
        """Carrier data should be immutable (frozenset)."""
        data = get_carrier_data()
        assert isinstance(data.known_carriers, frozenset)
        assert isinstance(data.non_carriers, frozenset)

    def test_get_carrier_data_is_cached(self):
        """Multiple calls should return the same cached object."""
        data1 = get_carrier_data()
        data2 = get_carrier_data()
        assert data1 is data2

    def test_get_carrier_data_loads_carriers(self):
        """Should load carriers from YAML file."""
        data = get_carrier_data()
        # Should have at least some known carriers
        assert len(data.known_carriers) > 0

    def test_carrier_data_is_normalized(self):
        """All carrier names should be normalized (lowercase, no punctuation)."""
        data = get_carrier_data()
        for carrier in data.known_carriers:
            assert carrier == carrier.lower()
            assert carrier == _normalize_for_match(carrier)


class TestNormalizeForMatch:
    """Test string normalization for fuzzy matching."""

    def test_lowercase(self):
        assert _normalize_for_match("CHUBB") == "chubb"

    def test_strip_punctuation(self):
        assert _normalize_for_match("Lloyd's") == "lloyds"

    def test_preserve_spaces(self):
        assert _normalize_for_match("AIG Inc.") == "aig inc"


class TestIsKnownCarrier:
    """Test known carrier detection."""

    def test_known_carrier_exact_match(self):
        """Should match known carriers exactly."""
        assert _is_known_carrier("Chubb")
        assert _is_known_carrier("AIG")

    def test_known_carrier_fuzzy_match(self):
        """Should match variations of known carriers."""
        assert _is_known_carrier("Chubb Bermuda")
        assert _is_known_carrier("AIG Insurance")

    def test_lloyds_patterns(self):
        """Should recognize Lloyd's patterns."""
        assert _is_known_carrier("Lloyd's of London")
        assert _is_known_carrier("Lloyds")

    def test_unknown_carrier(self):
        """Should not match unknown text."""
        assert not _is_known_carrier("Random Text")
        assert not _is_known_carrier("12345")


class TestIsNonCarrier:
    """Test non-carrier detection."""

    def test_non_carrier_phrase(self):
        """Should detect non-carrier phrases."""
        assert _is_non_carrier("subject to terms")
        assert _is_non_carrier("aggregate premium")

    def test_symbol_prefix(self):
        """Should detect symbol-prefixed values."""
        assert _is_non_carrier("*Note")
        assert _is_non_carrier("#Reference")

    def test_carrier_not_flagged(self):
        """Should not flag valid carriers."""
        assert not _is_non_carrier("Chubb")
        assert not _is_non_carrier("AIG")


class TestLooksLikePolicyNumber:
    """Test policy number detection."""

    def test_pure_numeric(self):
        """Should detect pure numeric policy numbers."""
        assert _looks_like_policy_number("12345678")
        assert _looks_like_policy_number("123456")

    def test_alphanumeric_pattern(self):
        """Should detect alphanumeric policy patterns."""
        assert _looks_like_policy_number("ABC12345")
        assert _looks_like_policy_number("PG2507405")

    def test_carrier_name_not_policy(self):
        """Should not flag carrier names as policy numbers."""
        assert not _looks_like_policy_number("Chubb")
        assert not _looks_like_policy_number("American Insurance Group")

    def test_empty_or_long(self):
        """Should not flag empty or very long strings."""
        assert not _looks_like_policy_number("")
        assert not _looks_like_policy_number("A" * 100)
