"""Data models for insurance tower extraction."""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class CarrierEntry:
    """Represents a single carrier's participation in a layer."""
    layer_limit: str
    layer_description: str
    carrier: str
    participation_pct: Optional[float]
    premium: Optional[float]
    premium_share: Optional[float]
    terms: Optional[str]
    policy_number: Optional[str]
    excel_range: str
    col_span: int
    row_span: int
    fill_color: Optional[str] = None
    attachment_point: Optional[str] = None  # Parsed from "xs." notation (e.g., "$50M xs. $10M" -> "$10M")

    def to_dict(self):
        return asdict(self)


@dataclass
class LayerSummary:
    """Layer-level aggregate data extracted from summary columns.

    This is used for cross-checking: the sum of carrier premiums
    in a layer should match the layer_bound_premium.
    """
    layer_limit: str
    layer_target: Optional[float] = None          # Annualized Layer Target
    layer_rate: Optional[float] = None            # Annualized Layer Rate
    layer_bound_premium: Optional[float] = None   # Layer Bound Premiums (total)
    excel_range: Optional[str] = None             # Cell reference for traceability

    def to_dict(self):
        return asdict(self)


def parse_limit_value(val) -> Optional[str]:
    """Parse various limit formats into standardized string."""
    if val is None:
        return None

    if isinstance(val, (int, float)):
        if val >= 1_000_000:
            return f"${int(val / 1_000_000)}M"
        elif val >= 1_000:
            return f"${int(val / 1_000)}K"
        return f"${int(val)}"

    if isinstance(val, str):
        if val.startswith('$'):
            return val
        cleaned = val.replace(',', '').replace('$', '')
        try:
            num = float(cleaned)
            return parse_limit_value(num)
        except ValueError:
            return val

    return None


def parse_excess_notation(text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse 'xs.' or 'x/s' or 'excess' notation from policy description.

    Examples:
        "Umbrella $50M xs. $50M" -> (limit="$50M", attachment="$50M")
        "General Liability $40M xs. $10M" -> (limit="$40M", attachment="$10M")
        "$25M x/s $25M" -> (limit="$25M", attachment="$25M")
        "Primary Auto $10M" -> (limit="$10M", attachment=None)

    Returns:
        Tuple of (limit, attachment_point) - either may be None
    """
    import re

    if not text or not isinstance(text, str):
        return None, None

    # Pattern for "xs." or "x/s" or "xs " or "excess of" or "excess" notation
    # Captures: <optional prefix> <limit> <xs notation> <attachment>
    patterns = [
        # "$50M xs. $50M" or "Umbrella $50M xs. $50M"
        r'(\$[\d,.]+[KMBkmb]?)\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*(\$[\d,.]+[KMBkmb]?)',
        # "50M xs 50M" without dollar signs
        r'([\d,.]+[KMBkmb])\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*([\d,.]+[KMBkmb])',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            limit = match.group(1)
            attachment = match.group(2)
            # Normalize to have $ prefix
            if not limit.startswith('$'):
                limit = '$' + limit
            if not attachment.startswith('$'):
                attachment = '$' + attachment
            return limit.upper(), attachment.upper()

    # Try to extract just a limit without attachment
    limit_pattern = r'(\$[\d,.]+[KMBkmb]?)'
    match = re.search(limit_pattern, text)
    if match:
        return match.group(1).upper(), None

    return None, None


def parse_limit_for_sort(limit_str: str) -> float:
    """Parse limit string to numeric value for sorting."""
    if not limit_str:
        return 0
    cleaned = limit_str.replace('$', '').replace(',', '').upper()
    multiplier = 1
    if cleaned.endswith('M'):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith('K'):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith('B'):
        multiplier = 1_000_000_000
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return 0
