"""Carrier detection and validation logic.

This module handles carrier name identification, including:
- Loading known carriers from YAML
- Fuzzy matching against known carrier lists
- Heuristic detection of carrier-like names
- Non-carrier filtering (policy numbers, labels, etc.)
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

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
    """
    known_carriers: frozenset[str] = frozenset()
    non_carriers: frozenset[str] = frozenset()

    if _CARRIERS_FILE.exists():
        with open(_CARRIERS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
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
