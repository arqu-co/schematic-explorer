"""Type definitions for insurance tower extraction."""

from dataclasses import asdict, dataclass


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


@dataclass
class VerificationResult:
    """Result of verification check."""

    score: float  # 0.0 to 1.0
    summary: str
    issues: list[str]
    suggestions: list[str]
    raw_response: str


def parse_limit_value(val) -> str | None:
    """Parse various limit formats into standardized string."""
    if val is None:
        return None

    if isinstance(val, int | float):
        if val >= 1_000_000:
            return f"${int(val / 1_000_000)}M"
        elif val >= 1_000:
            return f"${int(val / 1_000)}K"
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


def parse_excess_notation(text: str) -> tuple[str | None, str | None]:
    """Parse 'xs.' or 'x/s' or 'excess' notation from policy description.

    Examples:
        "Umbrella $50M xs. $50M" -> (limit="$50M", attachment="$50M")
        "$25M x/s $25M" -> (limit="$25M", attachment="$25M")

    Returns:
        Tuple of (limit, attachment_point) - either may be None
    """
    import re

    if not text or not isinstance(text, str):
        return None, None

    patterns = [
        r"(\$[\d,.]+[KMBkmb]?)\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*(\$[\d,.]+[KMBkmb]?)",
        r"([\d,.]+[KMBkmb])\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*([\d,.]+[KMBkmb])",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            limit = match.group(1)
            attachment = match.group(2)
            if not limit.startswith("$"):
                limit = "$" + limit
            if not attachment.startswith("$"):
                attachment = "$" + attachment
            return limit.upper(), attachment.upper()

    limit_pattern = r"(\$[\d,.]+[KMBkmb]?)"
    match = re.search(limit_pattern, text)
    if match:
        return match.group(1).upper(), None

    return None, None


def parse_limit_for_sort(limit_str: str) -> float:
    """Parse limit string to numeric value for sorting."""
    if not limit_str:
        return 0
    cleaned = limit_str.replace("$", "").replace(",", "").upper()
    multiplier = 1
    if cleaned.endswith("M"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("B"):
        multiplier = 1_000_000_000
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return 0
