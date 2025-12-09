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
