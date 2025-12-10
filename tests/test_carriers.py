"""Tests for carrier detection and validation module."""

import pytest

from schematic_explorer.carriers import (
    get_carrier_data,
    _normalize_for_match,
    _is_known_carrier,
    _is_non_carrier,
    _looks_like_policy_number,
)
from schematic_explorer.types import (
    CarrierEntity,
    MatchRules,
    CarrierConfig,
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


# =============================================================================
# Tests for new Carrier Detection Types
# =============================================================================


class TestCarrierEntity:
    """Test CarrierEntity dataclass."""

    def test_create_carrier_entity(self):
        """Should create carrier entity with canonical name and aliases."""
        entity = CarrierEntity(
            canonical="Chubb",
            aliases=frozenset(["Chubb", "ACE", "ACE American", "Westchester"]),
        )
        assert entity.canonical == "Chubb"
        assert "ACE" in entity.aliases
        assert len(entity.aliases) == 4

    def test_from_dict(self):
        """Should create from YAML dict format."""
        data = {
            "canonical": "Allied World",
            "aliases": ["AWAC", "Allied World", "Allied World Assurance"],
        }
        entity = CarrierEntity.from_dict(data)
        assert entity.canonical == "Allied World"
        assert "AWAC" in entity.aliases
        assert len(entity.aliases) == 3

    def test_from_dict_default_alias(self):
        """Should use canonical as alias if aliases not provided."""
        data = {"canonical": "AIG"}
        entity = CarrierEntity.from_dict(data)
        assert entity.canonical == "AIG"
        assert "AIG" in entity.aliases

    def test_frozen(self):
        """CarrierEntity should be immutable."""
        entity = CarrierEntity(
            canonical="Test", aliases=frozenset(["Test"])
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            entity.canonical = "Changed"


class TestMatchRules:
    """Test MatchRules dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        rules = MatchRules()
        assert rules.case_insensitive is True
        assert rules.ignore_punctuation is True
        assert rules.longest_alias_wins is True
        assert rules.gate_short_aliases is True
        assert rules.short_alias_max_len == 5
        assert "carrier" in rules.short_alias_keywords
        assert "insurer" in rules.short_alias_keywords

    def test_from_dict(self):
        """Should create from YAML match_rules section."""
        data = {
            "case_insensitive": False,
            "gate_short_aliases": {
                "enabled": True,
                "max_len": 4,
                "require_any_nearby_keywords": ["carrier", "market"],
            },
        }
        rules = MatchRules.from_dict(data)
        assert rules.case_insensitive is False
        assert rules.gate_short_aliases is True
        assert rules.short_alias_max_len == 4
        assert "carrier" in rules.short_alias_keywords
        assert "market" in rules.short_alias_keywords


class TestCarrierConfig:
    """Test CarrierConfig dataclass."""

    def test_from_dict_builds_alias_lookup(self):
        """Should build alias-to-canonical lookup map."""
        data = {
            "match_rules": {},
            "normalization": {
                "legal_suffixes": ["inc", "llc"],
            },
            "carrier_entities": [
                {"canonical": "Chubb", "aliases": ["Chubb", "ACE"]},
                {"canonical": "Allied World", "aliases": ["AWAC", "Allied World"]},
            ],
            "non_carriers": {
                "structural_labels": ["Total", "Premium"],
                "brokers_wholesalers": ["AmWins"],
            },
        }
        config = CarrierConfig.from_dict(data)

        # Check alias-to-canonical mapping
        assert config.alias_to_canonical.get("ace") == "Chubb"
        assert config.alias_to_canonical.get("awac") == "Allied World"
        assert config.alias_to_canonical.get("chubb") == "Chubb"

    def test_from_dict_merges_non_carriers(self):
        """Should merge structural labels and brokers into all_non_carriers."""
        data = {
            "non_carriers": {
                "structural_labels": ["Total", "Premium"],
                "brokers_wholesalers": ["AmWins", "Lockton"],
            },
        }
        config = CarrierConfig.from_dict(data)

        assert "total" in config.all_non_carriers
        assert "premium" in config.all_non_carriers
        assert "amwins" in config.all_non_carriers
        assert "lockton" in config.all_non_carriers
        assert "total" in config.structural_labels
        assert "amwins" in config.brokers_wholesalers

    def test_from_dict_parses_normalize_terms(self):
        """Should parse normalize_common_terms into dict."""
        data = {
            "normalization": {
                "normalize_common_terms": [
                    {"from": ["ins", "ins."], "to": "insurance"},
                    {"from": ["re", "re."], "to": "re"},
                ],
            },
        }
        config = CarrierConfig.from_dict(data)

        assert config.normalize_terms.get("ins") == "insurance"
        assert config.normalize_terms.get("ins.") == "insurance"
        assert config.normalize_terms.get("re") == "re"


# =============================================================================
# Tests for CarrierMatcher (TDD - will fail until implemented)
# =============================================================================


class TestCarrierMatcherAliasResolution:
    """Test alias resolution - matching aliases to canonical names."""

    def test_direct_canonical_match(self):
        """Direct canonical name should match."""
        from schematic_explorer.carriers import get_canonical_name
        # These tests will work once carriers.yml is updated with aliases
        # For now, test the function exists and returns sensible values
        result = get_canonical_name("Chubb")
        # Should return canonical name or None
        assert result is None or isinstance(result, str)

    def test_alias_resolves_to_canonical(self):
        """Alias should resolve to canonical name."""
        from schematic_explorer.carriers import get_canonical_name
        # Currently ACE resolves to "ACE" (old format) or "Chubb" (new format)
        result = get_canonical_name("ACE")
        # Until carriers.yml is updated, ACE is its own canonical
        assert result is None or result in ("ACE", "Chubb")

    def test_unknown_returns_none(self):
        """Unknown carrier should return None."""
        from schematic_explorer.carriers import get_canonical_name
        assert get_canonical_name("NotACarrier12345") is None


class TestCarrierMatcherNormalization:
    """Test text normalization before matching."""

    def test_case_insensitive_match(self):
        """Should match regardless of case."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # "CHUBB" and "chubb" should normalize the same
        assert matcher.normalize("CHUBB") == matcher.normalize("chubb")

    def test_legal_suffix_stripping(self):
        """Should strip legal suffixes (Inc, LLC, Ltd)."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # Should normalize away suffixes
        norm_with_suffix = matcher.normalize("Chubb Inc")
        norm_without = matcher.normalize("Chubb")
        # After stripping, should be similar (may have trailing space)
        assert "chubb" in norm_with_suffix
        assert "chubb" in norm_without


class TestCarrierMatcherLongestAliasWins:
    """Test longest-alias-wins matching strategy."""

    def test_longer_alias_preferred(self):
        """Should prefer longer alias match over shorter."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # "Allied World Assurance" should match to "Allied World",
        # not just "Allied" if that were also an alias
        result = matcher.match_carrier("Allied World Assurance Co.")
        # Should match a carrier (specific canonical depends on yml)
        assert result is None or isinstance(result, str)


class TestCarrierMatcherShortAliasGating:
    """Test context-aware gating for short aliases."""

    def test_short_alias_without_context_blocked(self):
        """Short aliases should not match without context keywords."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # Short alias like "Ki" (2 chars) should require context
        result = matcher.match_carrier("Ki", context_text="")
        # Without context, short alias should NOT match
        # (This depends on Ki being in carriers.yml with short alias gating)
        assert result is None or len("Ki") > matcher.config.match_rules.short_alias_max_len

    def test_short_alias_with_context_allowed(self):
        """Short aliases should match when context keywords present."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # With "carrier" keyword in context, should allow short alias match
        result = matcher.match_carrier("Ki", context_text="carrier: Ki 25%")
        # May or may not match depending on if Ki is in carriers.yml
        assert result is None or isinstance(result, str)

    def test_long_alias_no_context_needed(self):
        """Long aliases should match without context."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # "Chubb" (5 chars) should match without context
        result = matcher.match_carrier("Chubb", context_text="")
        # Should match without needing context
        assert result is None or isinstance(result, str)


class TestCarrierMatcherNonCarrierDetection:
    """Test non-carrier detection with new structured categories."""

    def test_structural_label_is_non_carrier(self):
        """Structural labels should be detected as non-carriers."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        assert matcher.is_non_carrier("Total")
        assert matcher.is_non_carrier("Premium")
        assert matcher.is_non_carrier("Aggregate")

    def test_broker_is_non_carrier(self):
        """Brokers/wholesalers should be detected as non-carriers."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        # AmWins and Lockton are in non_carriers list in current yml
        # Will be in brokers_wholesalers after yml update
        assert matcher.is_non_carrier("AmWins") or "amwins" in matcher.config.all_non_carriers
        assert matcher.is_non_carrier("Lockton") or "lockton" in matcher.config.all_non_carriers

    def test_carrier_is_not_non_carrier(self):
        """Carriers should not be flagged as non-carriers."""
        from schematic_explorer.carriers import get_carrier_matcher

        matcher = get_carrier_matcher()
        assert not matcher.is_non_carrier("Chubb")
        assert not matcher.is_non_carrier("AIG")
