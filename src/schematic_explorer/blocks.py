"""Block classification and type inference logic.

This module handles the core data structures and classification:
- Block dataclass for representing visual blocks in spreadsheets
- Type inference from cell content
- Block classification by content patterns
"""

from dataclasses import dataclass
from typing import Any

from .carriers import (
    COMPANY_SUFFIXES,
    MAX_CARRIER_NAME_LENGTH,
    MIN_CARRIER_NAME_LENGTH,
    _is_known_carrier,
    _is_non_carrier,
    _looks_like_policy_number,
)
from .types import MILLION, THOUSAND

# Type alias for inference results: (data_type, numeric_value)
TypeInferenceResult = tuple[str | None, float]

# =============================================================================
# Constants
# =============================================================================

# Percentage thresholds
PERCENTAGE_WHOLE_NUMBER_THRESHOLD = 1  # Values > 1 are assumed to be whole number %
PERCENTAGE_MAX_WHOLE_NUMBER = 100  # Maximum value for whole number percentage

# Coverage/terms indicators
COVERAGE_PATTERNS = [
    "excl",
    "incl",
    "flood",
    "earthquake",
    "eq ",
    "wind",
    "terror",
    "blanket",
    "margin",
    "ded",
    "retention",
    "all risk",
    "dic",
    "aop",
    "named storm",
    "nws",
]

# Column header label patterns
LABEL_PATTERNS = [
    "carrier",
    "participation",
    "premium",
    "share",
    "layer",
    "limit",
    "policy",
    "terms",
    "coverage",
    "deductible",
    "total",
]

# Status indicator values
STATUS_VALUES = ("tbd", "n/a", "pending", "incumbent", "new", "renewal")


# =============================================================================
# Block Dataclass
# =============================================================================


@dataclass
class Block:
    """A visual block in the spreadsheet (merged cell region or single cell)."""

    row: int
    col: int
    value: Any
    rows: int = 1
    cols: int = 1
    field_type: str | None = None
    confidence: float = 0.0


# =============================================================================
# Type Inference
# =============================================================================


def _infer_numeric_type(value: int | float) -> TypeInferenceResult:
    """Infer field type from a numeric value.

    Returns:
        Tuple of (field_type, confidence)
    """
    if value == 0:
        return "zero", 0.5
    if 0 < value <= PERCENTAGE_WHOLE_NUMBER_THRESHOLD:
        return "percentage", 0.9  # High confidence - typical participation format
    if PERCENTAGE_WHOLE_NUMBER_THRESHOLD < value <= PERCENTAGE_MAX_WHOLE_NUMBER:
        # Could be percentage as whole number, or small dollar amount
        return "percentage_or_number", 0.6
    if value > MILLION:
        return "large_number", 0.8  # Likely limit or TIV
    if value > THOUSAND:
        return "currency", 0.7  # Likely premium
    return "number", 0.5


def _infer_dollar_string_type(val: str, val_lower: str) -> TypeInferenceResult | None:
    """Infer field type from a dollar-prefixed string.

    Returns:
        Tuple of (field_type, confidence) if matched, None otherwise
    """
    if not val.startswith("$"):
        return None

    # Check for complex expressions first
    if any(x in val_lower for x in ["xs", "x/s", "p/o", "excess"]):
        return "layer_description", 0.95
    # Simple dollar amount with magnitude suffix
    if any(c in val.upper() for c in ["M", "K", "B"]) and val.count("$") == 1:
        return "limit", 0.9
    # Plain dollar amount
    rest = val[1:].replace(",", "").replace(".", "")
    if rest.isdigit():
        return "currency_string", 0.8

    return None


def _infer_carrier_type(val: str, val_lower: str) -> TypeInferenceResult | None:
    """Infer if value looks like a carrier name.

    Returns:
        Tuple of (field_type, confidence) if matched, None otherwise
    """
    # Company name heuristics for unknown carriers
    # - Reasonable length
    # - Not starting with $ or digit
    # - Contains letters
    # - May contain common suffixes
    if not (
        MIN_CARRIER_NAME_LENGTH <= len(val) <= MAX_CARRIER_NAME_LENGTH
        and not val[0].isdigit()
        and not val.startswith("$")
        and any(c.isalpha() for c in val)
    ):
        return None

    # Higher confidence if has company suffix
    if any(s in val_lower for s in COMPANY_SUFFIXES):
        return "carrier", 0.85
    # Medium confidence for other text that looks like a name
    if len(val) >= MIN_CARRIER_NAME_LENGTH and val[0].isupper():
        return "carrier", 0.6

    return None


def _infer_type(value: Any) -> TypeInferenceResult:
    """Infer field type and confidence from content alone."""
    if value is None:
        return None, 0.0

    # Numeric analysis
    if isinstance(value, int | float):
        return _infer_numeric_type(value)

    if not isinstance(value, str):
        return "unknown", 0.0

    val = str(value).strip()
    if not val:
        return None, 0.0

    val_lower = val.lower()

    # Dollar amounts with M/K/B suffix (layer limits)
    dollar_result = _infer_dollar_string_type(val, val_lower)
    if dollar_result:
        return dollar_result

    # Percentage string
    if val.endswith("%"):
        return "percentage_string", 0.9

    # Look for terms/coverage indicators
    if any(p in val_lower for p in COVERAGE_PATTERNS):
        return "terms", 0.85

    # Common label patterns
    if val_lower in LABEL_PATTERNS or any(val_lower.startswith(p) for p in LABEL_PATTERNS):
        return "label", 0.9

    # Status indicators
    if val_lower in STATUS_VALUES:
        return "status", 0.8

    # Catch patterns like "% Premium" - labels starting with symbols
    if val.startswith("%"):
        return "label", 0.7

    # Policy number patterns - alphanumeric codes with specific formats
    if _looks_like_policy_number(val):
        return "policy_number", 0.85

    # Check against known non-carrier terms (from YAML)
    if _is_non_carrier(val):
        return "label", 0.7

    # Very short strings (1-3 chars) are unlikely to be carrier names
    # Note: _is_known_carrier now supports context for short-alias gating,
    # but we don't have context available here. Short aliases (<=5 chars)
    # will only match if they're known carriers AND context keywords are present.
    # Since we don't pass context here, very short known carriers may not match.
    if len(val) <= 3 and not _is_known_carrier(val):
        return "label", 0.6

    # Check against known carrier names (from YAML) - fuzzy match
    # Context-aware matching is available but not used here yet.
    # Future: Pass nearby cell values as context for short-alias gating.
    if _is_known_carrier(val):
        return "carrier", 0.9

    # Check carrier name heuristics
    carrier_result = _infer_carrier_type(val, val_lower)
    if carrier_result:
        return carrier_result

    return "text", 0.3


def classify_blocks(blocks: list[Block]) -> None:
    """Classify each block by analyzing its content."""
    for block in blocks:
        block.field_type, block.confidence = _infer_type(block.value)
