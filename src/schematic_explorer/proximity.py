"""Proximity matching helpers for carrier-to-data association.

This module handles spatial proximity logic:
- Column overlap detection
- Currency block matching by row/column
- Participation percentage matching
- Summary column detection
"""

import re

from .blocks import PERCENTAGE_WHOLE_NUMBER_THRESHOLD, Block
from .types import SummaryColumnInfo

# =============================================================================
# Constants
# =============================================================================

# Proximity thresholds for spatial matching
MAX_COLUMN_DISTANCE = 3  # Maximum columns away for non-aligned data matching

# Column limits
MAX_HEADER_SCAN_ROW = 10  # How many rows to scan for headers
MAX_HEADER_SCAN_COLUMN = 30  # How many columns to scan for headers

# Patterns that indicate summary columns (not per-carrier data)
SUMMARY_COLUMN_PATTERNS = [
    "annualized",
    "layer rate",  # "Layer Rates" but not "Layer Premium"
    "bound premium",
    "layer target",
    "total premium",
    "aggregate",
]

# Pattern for year-prefixed layer columns (e.g., "2019 Layer Premium")
_YEAR_LAYER_PREMIUM_PATTERN = re.compile(r"^\d{4}\s+layer\s+premium", re.IGNORECASE)
_YEAR_LAYER_RATE_PATTERN = re.compile(r"^\d{4}\s+layer\s+rate", re.IGNORECASE)


# =============================================================================
# Column Range Helpers
# =============================================================================


def get_column_range(block: Block) -> range:
    """Get the range of columns spanned by a block."""
    return range(block.col, block.col + block.cols)


def columns_overlap(range1: range, range2: range) -> bool:
    """Check if two column ranges overlap using efficient set intersection."""
    return bool(set(range1) & set(range2))


def calculate_block_proximity(block: Block, carrier: Block, carrier_col_range: range) -> tuple:
    """Calculate proximity score for sorting blocks by relevance to carrier.

    Returns:
        Tuple of (not_column_aligned, row_distance) for sorting.
        Lower values = higher priority.
    """
    block_col_range = get_column_range(block)
    col_overlap = columns_overlap(block_col_range, carrier_col_range)
    row_dist = abs(block.row - carrier.row)
    return (not col_overlap, row_dist)


def is_block_relevant(
    block: Block, carrier: Block, carrier_col_range: range, row_range: range
) -> bool:
    """Check if a data block is relevant to a carrier based on spatial proximity.

    A block is relevant if:
    - It's in the carrier's column range, OR
    - It's in the same row (±1) and within MAX_COLUMN_DISTANCE columns
    """
    block_col_range = get_column_range(block)
    in_col = columns_overlap(block_col_range, carrier_col_range)

    if in_col:
        return True

    # For non-column-aligned blocks, require same row and close proximity
    if abs(block.row - carrier.row) <= 1 and abs(block.col - carrier.col) <= MAX_COLUMN_DISTANCE:
        return True

    return False


# =============================================================================
# Summary Column Detection
# =============================================================================


def _check_adjacent_summary_columns(ws, row: int, start_col: int, result: dict) -> None:
    """Check columns adjacent to year-prefixed layer premium for related summary data."""
    for extra_col in range(start_col + 1, min(start_col + 5, ws.max_column + 1)):
        extra_val = ws.cell(row=row, column=extra_col).value
        if not extra_val or not isinstance(extra_val, str):
            continue

        extra_lower = extra_val.lower().strip()
        # Check for fees, total, or tax columns
        if extra_lower in ("fees", "total") or "tax" in extra_lower:
            result["columns"].add(extra_col)
        # Check for year layer rate (e.g., "2019 Layer Rate")
        if _YEAR_LAYER_RATE_PATTERN.match(extra_lower):
            result["columns"].add(extra_col)
            result["layer_rate_col"] = extra_col


def _classify_summary_column(val_lower: str, col: int, result: dict) -> None:
    """Classify a summary column and update result dict."""
    for pattern in SUMMARY_COLUMN_PATTERNS:
        if pattern in val_lower:
            result["columns"].add(col)
            # Track specific column types for extraction
            if "bound premium" in val_lower:
                result["bound_premium_col"] = col
            elif "target" in val_lower:
                result["layer_target_col"] = col
            elif "rate" in val_lower and "annualized" not in val_lower:
                result["layer_rate_col"] = col
            break


def detect_summary_columns(ws) -> SummaryColumnInfo:
    """Detect columns that contain summary/aggregate data rather than per-carrier data.

    These columns typically have headers like:
    - "Annualized Layer Rate"
    - "Layer Bound Premiums"
    - "Layer Rates"
    - "Layer Target"

    Returns:
        SummaryColumnInfo with detected column information
    """
    # Use internal dict for building, convert to dataclass at end
    result = {
        "columns": set(),
        "bound_premium_col": None,
        "layer_target_col": None,
        "layer_rate_col": None,
    }

    # Scan header rows for summary column indicators
    for row in range(1, MAX_HEADER_SCAN_ROW + 1):
        for col in range(1, min(ws.max_column + 1, MAX_HEADER_SCAN_COLUMN)):
            cell = ws.cell(row=row, column=col)
            val = cell.value
            if not val or not isinstance(val, str):
                continue

            # Normalize whitespace for pattern matching
            val_lower = " ".join(val.lower().split())

            # Check for year-prefixed layer premium (e.g., "2019 Layer Premium")
            if _YEAR_LAYER_PREMIUM_PATTERN.match(val_lower):
                result["columns"].add(col)
                _check_adjacent_summary_columns(ws, row, col, result)
                continue

            # Check for standard summary column patterns
            _classify_summary_column(val_lower, col, result)

    return SummaryColumnInfo(
        columns=result["columns"],
        bound_premium_col=result["bound_premium_col"],
        layer_target_col=result["layer_target_col"],
        layer_rate_col=result["layer_rate_col"],
    )


# =============================================================================
# Participation Matching
# =============================================================================


def _normalize_percentage(value: int | float | str | None) -> float | None:
    """Normalize a percentage value to 0-1 range."""
    if value is None:
        return None

    if isinstance(value, str):
        val_str = value.replace("%", "").strip()
        try:
            value = float(val_str)
        except ValueError:
            return None

    if not isinstance(value, int | float):
        return None

    # If > 1, assume it's a whole number percentage
    if value > PERCENTAGE_WHOLE_NUMBER_THRESHOLD:
        return value / 100

    return float(value)


def match_participation_block(
    block: Block, row_labels: dict | None, rate_col: int | None
) -> float | None:
    """Try to match a percentage block as participation.

    Returns:
        Normalized participation percentage (0-1) or None if not a match.
    """
    # Skip Rate column - rates are NOT participation percentages
    if rate_col and block.col == rate_col:
        return None

    participation_row = row_labels.get("participation_row") if row_labels else None

    if participation_row:
        # Only accept values from participation row (or row below)
        if block.row == participation_row or block.row == participation_row + 1:
            return _normalize_percentage(block.value)
        return None
    else:
        # No participation_row label - use proximity-based matching
        return _normalize_percentage(block.value)


# =============================================================================
# Currency Block Matching
# =============================================================================


def _parse_currency(value: int | float | str | None) -> float | None:
    """Parse a currency value."""
    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        val_str = value.replace("$", "").replace(",", "").strip()
        try:
            return float(val_str)
        except ValueError:
            return None

    return None


def should_skip_currency_block(
    block: Block,
    column_headers: dict | None,
    row_labels: dict | None,
) -> bool:
    """Check if a currency block should be skipped based on its position."""
    # Skip TIV columns
    tiv_col = column_headers.get("tiv_col") if column_headers else None
    tiv_data_col = column_headers.get("tiv_data_col") if column_headers else None
    if tiv_col and block.col == tiv_col:
        return True
    if tiv_data_col and block.col == tiv_data_col:
        return True

    # Skip policy number row
    policy_row = row_labels.get("policy_row") if row_labels else None
    if policy_row and block.row == policy_row:
        return True

    # Skip Limit column
    limit_col = column_headers.get("limit_col") if column_headers else None
    if limit_col and block.col == limit_col:
        return True

    return False


def _is_row_match(block_row: int, target_row: int | None) -> bool:
    """Check if block row matches target row or adjacent row."""
    if target_row is None:
        return False
    return block_row == target_row or block_row == target_row + 1


def _match_currency_by_row(
    block: Block,
    val: float,
    row_labels: dict | None,
    current_premium: float | None,
    current_premium_share: float | None,
) -> tuple[float | None, float | None, bool]:
    """Try to match currency value by row labels.

    Returns:
        Tuple of (premium, premium_share, matched) where matched indicates if a match was found.
    """
    percent_premium_row = row_labels.get("percent_premium_row") if row_labels else None
    premium_row = row_labels.get("premium_row") if row_labels else None
    limit_row = row_labels.get("limit_row") if row_labels else None

    # Check for % Premium / Share Premium row (carrier's share)
    if _is_row_match(block.row, percent_premium_row):
        if current_premium is None:
            return val, current_premium_share, True
        return current_premium, current_premium_share, True

    # Check for Premium row (layer total)
    if _is_row_match(block.row, premium_row):
        if percent_premium_row:
            # Skip layer totals when we have % Premium row
            return current_premium, current_premium_share, True
        if current_premium is None:
            return val, current_premium_share, True
        return current_premium, current_premium_share, True

    # Check for LIMIT row
    if limit_row and block.row == limit_row:
        if current_premium is None:
            return val, current_premium_share, True
        return current_premium, current_premium_share, True

    return current_premium, current_premium_share, False


def _match_currency_by_column(
    block: Block,
    val: float,
    column_headers: dict | None,
    current_premium: float | None,
    current_premium_share: float | None,
) -> tuple[float | None, float | None]:
    """Match currency value by column headers with fallback logic."""
    premium_col = column_headers.get("premium_col") if column_headers else None
    premium_share_col = column_headers.get("premium_share_col") if column_headers else None

    # Check for premium_col column header
    if premium_col and block.col == premium_col:
        if current_premium is None:
            return val, current_premium_share
        return current_premium, current_premium_share
    elif premium_col:
        # We have a premium_col but this block isn't in it - skip
        return current_premium, current_premium_share

    # Fallback to column-based logic
    if premium_share_col and block.col == premium_share_col:
        if current_premium_share is None:
            return current_premium, val
    elif current_premium is None:
        return val, current_premium_share
    elif current_premium_share is None:
        return current_premium, val

    return current_premium, current_premium_share


def match_currency_block(
    block: Block,
    column_headers: dict | None,
    row_labels: dict | None,
    current_premium: float | None,
    current_premium_share: float | None,
) -> tuple[float | None, float | None]:
    """Try to match a currency block as premium or premium_share.

    Returns:
        Tuple of (premium, premium_share) with updated values.
    """
    # Check if block should be skipped
    if should_skip_currency_block(block, column_headers, row_labels):
        return current_premium, current_premium_share

    val = _parse_currency(block.value)
    if val is None:
        return current_premium, current_premium_share

    # Try row-based matching first
    premium, premium_share, matched = _match_currency_by_row(
        block, val, row_labels, current_premium, current_premium_share
    )
    if matched:
        return premium, premium_share

    # Fall back to column-based matching
    return _match_currency_by_column(
        block, val, column_headers, current_premium, current_premium_share
    )
