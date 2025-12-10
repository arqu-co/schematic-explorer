"""Carrier detection and validation logic.

This module handles carrier name identification, including:
- Loading known carriers from YAML
- Alias resolution (multiple aliases → canonical name)
- Longest-alias-wins matching strategy
- Context-aware short alias gating
- Non-carrier filtering (policy numbers, labels, etc.)
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from .types import CarrierConfig

# =============================================================================
# Constants
# =============================================================================

# Patterns that indicate non-carrier text (descriptive/conditional text)
NON_CARRIER_PHRASES = [
    "subject to",
    "conditions",
    "terms &",
    "all terms",
    "tied to",
    "offer capacity",
    "no rp for",
    "loss rating",
    "increase in",
    "decrease in",
    "updated",
    "by year",
    "buy down",
    "all risk",
    "dic premium",
    "aggregate",
]

# Company name suffixes that indicate a carrier
COMPANY_SUFFIXES = [
    "inc",
    "llc",
    "ltd",
    "co",
    "corp",
    "company",
    "ins",
    "insurance",
    "assurance",
    "specialty",
    "group",
    "re",
]

# Policy number constraints
MAX_POLICY_NUMBER_LENGTH = 30
MIN_POLICY_NUMBER_DIGITS = 4
MIN_PURE_NUMERIC_POLICY_LENGTH = 6

# Carrier name constraints
MIN_CARRIER_NAME_LENGTH = 3
MAX_CARRIER_NAME_LENGTH = 100

# =============================================================================
# Carrier Data (immutable, lazy-loaded)
# =============================================================================

_CARRIERS_FILE = Path(__file__).parent / "carriers.yml"


@dataclass(frozen=True)
class CarrierData:
    """Immutable container for carrier matching data.

    Uses frozensets for thread safety and immutability.
    """

    known_carriers: frozenset[str]
    non_carriers: frozenset[str]


def _normalize_for_match(s: str) -> str:
    """Normalize string for fuzzy matching - lowercase, strip punctuation."""
    return re.sub(r"[^a-z0-9\s]", "", s.lower()).strip()


@cache
def get_carrier_data() -> CarrierData:
    """Load carrier data from YAML file (cached, thread-safe).

    Returns immutable CarrierData with frozensets for known carriers
    and non-carriers. Uses functools.cache for automatic memoization.

    Supports both old format (flat lists) and new format (carrier_entities).
    """
    known_carriers: frozenset[str] = frozenset()
    non_carriers: frozenset[str] = frozenset()

    if _CARRIERS_FILE.exists():
        with open(_CARRIERS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Check if using new format (has carrier_entities)
        if "carrier_entities" in data:
            # New format: extract all aliases from carrier_entities
            all_aliases = []
            for entity in data.get("carrier_entities", []):
                all_aliases.extend(entity.get("aliases", []))
            known_carriers = frozenset(
                _normalize_for_match(c) for c in all_aliases
            )

            # Non-carriers from both structural_labels and brokers_wholesalers
            non_carriers_config = data.get("non_carriers", {})
            all_non_carriers = (
                non_carriers_config.get("structural_labels", [])
                + non_carriers_config.get("brokers_wholesalers", [])
            )
            non_carriers = frozenset(
                _normalize_for_match(c) for c in all_non_carriers
            )
        else:
            # Old format: flat carriers and non_carriers lists
            known_carriers = frozenset(
                _normalize_for_match(c) for c in data.get("carriers", [])
            )
            non_carriers = frozenset(
                _normalize_for_match(c) for c in data.get("non_carriers", [])
            )

    return CarrierData(known_carriers=known_carriers, non_carriers=non_carriers)


def _is_known_carrier(value: str) -> bool:
    """Check if value matches a known carrier (fuzzy match)."""
    data = get_carrier_data()
    normalized = _normalize_for_match(value)

    # Direct match
    if normalized in data.known_carriers:
        return True

    # Check if any known carrier is contained in the value
    # e.g., "Chubb Bermuda" contains "chubb"
    for carrier in data.known_carriers:
        if carrier in normalized or normalized in carrier:
            return True

    # Check for Lloyd's patterns - very common in insurance
    if "lloyd" in normalized or "lloyds" in normalized:
        return True

    # Check for "London" with percentages - typically indicates London market carrier
    if "london" in normalized and "%" in value:
        return True

    return False


def _is_non_carrier(value: str) -> bool:
    """Check if value matches a known non-carrier term."""
    data = get_carrier_data()
    normalized = _normalize_for_match(value)

    # Direct match only - don't do substring matching on non-carrier terms
    # This prevents "Chubb Bermuda" from matching "Bermuda"
    # and "London - Fidelis" from matching "London"
    if normalized in data.non_carriers:
        return True

    # For compound non-carrier terms (like "RT Layer"), check if value starts with them
    # But ONLY for multi-word non-carrier terms to avoid blocking "London - Fidelis"
    for term in data.non_carriers:
        # Only do prefix matching for multi-word terms
        if " " in term and normalized.startswith(term + " "):
            return True

    # Additional patterns that indicate non-carrier text
    val_lower = value.lower()

    # Sentences or descriptive text (contains multiple words with common patterns)
    if any(phrase in val_lower for phrase in NON_CARRIER_PHRASES):
        return True

    # Starts with symbols or contains mostly special characters
    if value.startswith("*") or value.startswith("#"):
        return True

    return False


def _looks_like_policy_number(value: str) -> bool:
    """Check if value looks like a policy number rather than a carrier name.

    Policy numbers typically:
    - Are alphanumeric codes (letters + numbers mixed)
    - Have specific patterns like "ABC12345", "12345678", "ABC-123-456"
    - Are relatively short (< MAX_POLICY_NUMBER_LENGTH chars)
    - Have high digit-to-letter ratio or specific prefixes
    """
    if not value or len(value) > MAX_POLICY_NUMBER_LENGTH:
        return False

    # Pure numeric (likely policy number)
    digits_only = value.replace("-", "").replace(" ", "")
    if digits_only.isdigit() and len(digits_only) >= MIN_PURE_NUMERIC_POLICY_LENGTH:
        return True

    # Count digits and letters
    digits = sum(1 for c in value if c.isdigit())
    letters = sum(1 for c in value if c.isalpha())

    # If mostly digits with some letters, likely policy number
    if digits >= MIN_POLICY_NUMBER_DIGITS and digits > letters:
        return True

    # Common policy number patterns
    # - Starts with letters, ends with numbers: "PG2507405", "CSP00316270P-00"
    # - Has dashes/hyphens with alphanumeric segments
    val_upper = value.upper()
    if re.match(r"^[A-Z]{1,6}\d{5,}", val_upper):  # ABC12345... or RMANAH02273P03
        return True
    if re.match(r"^[A-Z]{1,6}-?\d+", val_upper) and digits >= 5:  # ABC-12345
        return True
    if re.match(r"^\d+[A-Z]+\d*", val_upper) and digits >= 5:  # 123ABC456
        return True
    # Pattern with letters at end: "RMANAH02273P03"
    if re.match(r"^[A-Z]+\d+[A-Z]*\d*$", val_upper) and digits >= 4:
        return True

    return False


# =============================================================================
# CarrierMatcher - Enhanced carrier detection with alias resolution
# =============================================================================


class CarrierMatcher:
    """Carrier matcher with alias resolution and context-aware gating.

    Features:
    - Canonical↔alias resolution: Multiple aliases map to one canonical name
    - Longest-alias-wins: Prevents partial matches when longer aliases exist
    - Context-aware gating: Short aliases require nearby keywords to match
    - Legal suffix normalization: Strips Inc, LLC, Ltd, etc.
    """

    def __init__(self, config: CarrierConfig):
        """Initialize matcher with carrier configuration.

        Args:
            config: CarrierConfig with entities, rules, and lookup maps
        """
        self.config = config

        # Build sorted aliases (longest first) for longest-match-wins
        # Format: [(normalized_alias, canonical_name), ...]
        self._sorted_aliases: list[tuple[str, str]] = sorted(
            [(alias.lower(), canonical) for alias, canonical in config.alias_to_canonical.items()],
            key=lambda x: len(x[0]),
            reverse=True,  # Longest first
        )

    def normalize(self, value: str) -> str:
        """Normalize text for matching.

        Normalization chain:
        1. Lowercase (if case_insensitive)
        2. Strip legal suffixes (Inc, LLC, etc.)
        3. Expand common terms (ins → insurance)
        4. Strip punctuation (if ignore_punctuation)

        Args:
            value: Text to normalize

        Returns:
            Normalized text for matching
        """
        result = value

        # 1. Lowercase
        if self.config.match_rules.case_insensitive:
            result = result.lower()

        # 2. Strip legal suffixes
        for suffix in self.config.legal_suffixes:
            # Match suffix at end of string, optionally preceded by space or punctuation
            pattern = rf"[\s,.]?{re.escape(suffix)}\.?$"
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)

        # 3. Expand common terms
        for from_term, to_term in self.config.normalize_terms.items():
            # Word boundary replacement
            pattern = rf"\b{re.escape(from_term)}\b"
            result = re.sub(pattern, to_term, result, flags=re.IGNORECASE)

        # 4. Strip punctuation
        if self.config.match_rules.ignore_punctuation:
            result = re.sub(r"[^a-z0-9\s]", "", result)

        return result.strip()

    def _has_context_keyword(self, context_text: str) -> bool:
        """Check if context contains any gating keywords.

        Args:
            context_text: Surrounding text to search for keywords

        Returns:
            True if any keyword found in context
        """
        if not context_text:
            return False

        context_lower = context_text.lower()
        return any(kw in context_lower for kw in self.config.match_rules.short_alias_keywords)

    def match_carrier(self, value: str, context_text: str = "") -> str | None:
        """Match value to a carrier and return canonical name.

        Uses longest-alias-wins strategy and context-aware short alias gating.

        Args:
            value: Text to match against carrier aliases
            context_text: Surrounding text for short-alias gating

        Returns:
            Canonical carrier name if matched, None otherwise
        """
        normalized = self.normalize(value)

        if not normalized:
            return None

        # Try exact match first (most common case)
        if normalized in self.config.alias_to_canonical:
            canonical = self.config.alias_to_canonical[normalized]
            alias_len = len(normalized)

            # Apply short alias gating
            if (
                self.config.match_rules.gate_short_aliases
                and alias_len <= self.config.match_rules.short_alias_max_len
                and not self._has_context_keyword(context_text)
            ):
                return None

            return canonical

        # Try longest-alias-wins containment matching
        if self.config.match_rules.longest_alias_wins:
            for alias, canonical in self._sorted_aliases:
                if alias in normalized:
                    alias_len = len(alias)

                    # Apply short alias gating
                    if (
                        self.config.match_rules.gate_short_aliases
                        and alias_len <= self.config.match_rules.short_alias_max_len
                        and not self._has_context_keyword(context_text)
                    ):
                        continue

                    return canonical

        return None

    def is_non_carrier(self, value: str) -> bool:
        """Check if value is a non-carrier term.

        Args:
            value: Text to check

        Returns:
            True if value matches structural label, broker, or non-carrier phrase
        """
        normalized = self.normalize(value)

        # Check against merged non-carriers (structural + brokers)
        if normalized in self.config.all_non_carriers:
            return True

        # Legacy phrase matching
        val_lower = value.lower()
        if any(phrase in val_lower for phrase in NON_CARRIER_PHRASES):
            return True

        # Symbol prefix check
        if value.startswith("*") or value.startswith("#"):
            return True

        return False

    def resolve_canonical(self, alias: str) -> str | None:
        """Resolve an alias to its canonical carrier name.

        Args:
            alias: Carrier alias to resolve

        Returns:
            Canonical name if found, None otherwise
        """
        normalized = self.normalize(alias)
        return self.config.alias_to_canonical.get(normalized)


# =============================================================================
# Cached CarrierMatcher instance
# =============================================================================


def _load_carrier_config() -> CarrierConfig:
    """Load carrier config from YAML file.

    Supports both old format (flat lists) and new format (with carrier_entities).
    """
    if not _CARRIERS_FILE.exists():
        # Return empty config if file doesn't exist
        return CarrierConfig.from_dict({})

    with open(_CARRIERS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Check if using new format (has carrier_entities)
    if "carrier_entities" in data:
        return CarrierConfig.from_dict(data)

    # Convert old format to new format for backward compatibility
    old_carriers = data.get("carriers", [])
    old_non_carriers = data.get("non_carriers", [])

    # Convert flat carrier list to entities (each carrier is its own canonical)
    carrier_entities = [{"canonical": c, "aliases": [c]} for c in old_carriers]

    new_format = {
        "match_rules": {},
        "normalization": {
            "legal_suffixes": COMPANY_SUFFIXES,  # Use existing suffixes
        },
        "carrier_entities": carrier_entities,
        "non_carriers": {
            "structural_labels": old_non_carriers,
            "brokers_wholesalers": [],
        },
    }

    return CarrierConfig.from_dict(new_format)


@cache
def get_carrier_matcher() -> CarrierMatcher:
    """Get cached CarrierMatcher instance.

    Returns:
        CarrierMatcher configured from carriers.yml
    """
    config = _load_carrier_config()
    return CarrierMatcher(config)


def get_canonical_name(alias: str) -> str | None:
    """Resolve an alias to its canonical carrier name.

    Args:
        alias: Carrier alias to resolve

    Returns:
        Canonical name if found, None otherwise
    """
    return get_carrier_matcher().resolve_canonical(alias)
