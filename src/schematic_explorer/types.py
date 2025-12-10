"""Type definitions for insurance tower extraction."""

import re
from dataclasses import asdict, dataclass

# =============================================================================
# Magnitude Constants
# =============================================================================

THOUSAND = 1_000
MILLION = 1_000_000
BILLION = 1_000_000_000

# =============================================================================
# Compiled Regex Patterns
# =============================================================================

# Patterns for parsing "xs." / "x/s" / "excess" notation
_EXCESS_PATTERN_DOLLAR = re.compile(
    r"(\$[\d,.]+[KMBkmb]?)\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*(\$[\d,.]+[KMBkmb]?)",
    re.IGNORECASE,
)
_EXCESS_PATTERN_NO_DOLLAR = re.compile(
    r"([\d,.]+[KMBkmb])\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*([\d,.]+[KMBkmb])",
    re.IGNORECASE,
)
_LIMIT_PATTERN = re.compile(r"(\$[\d,.]+[KMBkmb]?)")


@dataclass
class CarrierMatchContext:
    """Context for matching carrier blocks to related data.

    Groups related parameters used when building CarrierEntry objects,
    reducing the parameter count of proximity-matching functions.
    """

    layer: "Layer"  # The layer being processed
    data_blocks: list  # List of data blocks to search for matches
    column_headers: dict = None  # Dict mapping column types to column numbers
    row_labels: dict = None  # Dict mapping row types to row numbers

    def __post_init__(self):
        """Set default empty dicts if None provided."""
        if self.column_headers is None:
            self.column_headers = {}
        if self.row_labels is None:
            self.row_labels = {}


@dataclass
class SummaryColumnInfo:
    """Information about summary/aggregate columns detected in a worksheet.

    Summary columns contain layer-level totals rather than per-carrier data.
    They are excluded from carrier extraction but used for cross-checking.
    """

    columns: set[int]  # Set of column numbers to exclude from carrier extraction
    bound_premium_col: int | None = None  # Column with Layer Bound Premiums
    layer_target_col: int | None = None  # Column with Layer Target
    layer_rate_col: int | None = None  # Column with Layer Rate

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Layer:
    """Represents a layer boundary in an insurance tower.

    Layers are identified by their limit values and define row ranges
    in the spreadsheet that contain carrier participation data.
    """

    limit: str  # Formatted limit (e.g., "$50M")
    limit_row: int  # Row where the limit was found
    limit_col: int  # Column where the limit was found
    start_row: int  # First row of layer data
    end_row: int  # Last row of layer data

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CarrierEntry:
    """Represents a single carrier's participation in a layer."""

    layer_limit: str
    layer_description: str
    carrier: str
    participation_pct: float | None
    premium: float | None
    premium_share: float | None
    terms: str | None
    policy_number: str | None
    excel_range: str
    col_span: int
    row_span: int
    fill_color: str | None = None
    attachment_point: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LayerSummary:
    """Layer-level aggregate data extracted from summary columns.

    Used for cross-checking: the sum of carrier premiums
    in a layer should match the layer_bound_premium.
    """

    layer_limit: str
    layer_target: float | None = None
    layer_rate: float | None = None
    layer_bound_premium: float | None = None
    excel_range: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class VerificationError(Exception):
    """Raised when verification parsing fails after all retry attempts."""

    pass


@dataclass
class VerificationResult:
    """Result of verification check."""

    score: float  # 0.0 to 1.0
    summary: str
    issues: list[str]
    suggestions: list[str]
    raw_response: str
    metadata: dict | None = None  # Additional info (e.g., fallback_used, parsing_method)


def parse_limit_value(val: int | float | str | None) -> str | None:
    """Parse various limit formats into standardized string."""
    if val is None:
        return None

    if isinstance(val, int | float):
        if val >= MILLION:
            return f"${int(val / MILLION)}M"
        elif val >= THOUSAND:
            return f"${int(val / THOUSAND)}K"
        return f"${int(val)}"

    if isinstance(val, str):
        if val.startswith("$"):
            return val
        cleaned = val.replace(",", "").replace("$", "")
        try:
            num = float(cleaned)
            return parse_limit_value(num)
        except ValueError:
            return val

    return None


def parse_excess_notation(text: str | None) -> tuple[str | None, str | None]:
    """Parse 'xs.' or 'x/s' or 'excess' notation from policy description.

    Examples:
        "Umbrella $50M xs. $50M" -> (limit="$50M", attachment="$50M")
        "$25M x/s $25M" -> (limit="$25M", attachment="$25M")

    Returns:
        Tuple of (limit, attachment_point) - either may be None
    """
    if not text or not isinstance(text, str):
        return None, None

    # Try dollar-prefixed pattern first
    match = _EXCESS_PATTERN_DOLLAR.search(text)
    if match:
        return match.group(1).upper(), match.group(2).upper()

    # Try non-dollar pattern (adds $ prefix to results)
    match = _EXCESS_PATTERN_NO_DOLLAR.search(text)
    if match:
        limit = "$" + match.group(1)
        attachment = "$" + match.group(2)
        return limit.upper(), attachment.upper()

    # Fall back to extracting just a limit
    match = _LIMIT_PATTERN.search(text)
    if match:
        return match.group(1).upper(), None

    return None, None


def parse_limit_for_sort(limit_str: str | None) -> float:
    """Parse limit string to numeric value for sorting."""
    if not limit_str:
        return 0
    cleaned = limit_str.replace("$", "").replace(",", "").upper()
    multiplier = 1
    if cleaned.endswith("M"):
        multiplier = MILLION
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = THOUSAND
        cleaned = cleaned[:-1]
    elif cleaned.endswith("B"):
        multiplier = BILLION
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return 0
