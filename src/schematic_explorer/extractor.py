"""Adaptive extraction logic for any tower format.

This extractor analyzes the spreadsheet structure from first principles:
1. Merged cells define visual blocks - these are the primary structure
2. Spatial proximity determines relationships
3. Content patterns infer field types
4. No assumptions about specific labels or column positions
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from openpyxl.utils import get_column_letter, range_boundaries

from .types import CarrierEntry, LayerSummary, parse_excess_notation, parse_limit_value
from .utils import find_merged_range_at, get_cell_color, get_cell_value

# =============================================================================
# Constants
# =============================================================================

# Numeric thresholds for type inference
MILLION = 1_000_000
THOUSAND = 1_000
BILLION = 1_000_000_000

# Percentage thresholds
PERCENTAGE_WHOLE_NUMBER_THRESHOLD = 1  # Values > 1 are assumed to be whole number %
PERCENTAGE_MAX_WHOLE_NUMBER = 100  # Maximum value for whole number percentage

# Proximity thresholds for spatial matching
MAX_COLUMN_DISTANCE = 3  # Maximum columns away for non-aligned data matching
MAX_ROW_SEARCH_DISTANCE = 10  # How many rows below carrier to search for data
LAYER_ROW_PROXIMITY = 2  # Distance threshold for "nearby" layer rows

# Column limits
MAX_LAYER_LIMIT_COLUMN = 2  # Layer limits should be in columns A or B
MAX_HEADER_SCAN_ROW = 10  # How many rows to scan for headers
MAX_HEADER_SCAN_COLUMN = 30  # How many columns to scan for headers

# Policy number constraints
MAX_POLICY_NUMBER_LENGTH = 30
MIN_POLICY_NUMBER_DIGITS = 4
MIN_PURE_NUMERIC_POLICY_LENGTH = 6

# Carrier name constraints
MIN_CARRIER_NAME_LENGTH = 3
MAX_CARRIER_NAME_LENGTH = 100

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

# Patterns that indicate summary columns (not per-carrier data)
SUMMARY_COLUMN_PATTERNS = [
    "annualized",
    "layer rate",  # "Layer Rates" but not "Layer Premium"
    "bound premium",
    "layer target",
    "total premium",
    "aggregate",
]

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

# Status indicator values
STATUS_VALUES = ("tbd", "n/a", "pending", "incumbent", "new", "renewal")

# =============================================================================
# Carrier Data (loaded from YAML)
# =============================================================================

# Load carrier lists from YAML
_CARRIERS_FILE = Path(__file__).parent / "carriers.yml"
_KNOWN_CARRIERS: set[str] = set()
_NON_CARRIERS: set[str] = set()


def _normalize_for_match(s: str) -> str:
    """Normalize string for fuzzy matching - lowercase, strip punctuation."""
    return re.sub(r"[^a-z0-9\s]", "", s.lower()).strip()


def _load_carriers():
    """Load carrier lists from YAML file."""
    global _KNOWN_CARRIERS, _NON_CARRIERS
    if _KNOWN_CARRIERS:  # Already loaded
        return

    if _CARRIERS_FILE.exists():
        with open(_CARRIERS_FILE) as f:
            data = yaml.safe_load(f)
        _KNOWN_CARRIERS = {_normalize_for_match(c) for c in data.get("carriers", [])}
        _NON_CARRIERS = {_normalize_for_match(c) for c in data.get("non_carriers", [])}


def _is_known_carrier(value: str) -> bool:
    """Check if value matches a known carrier (fuzzy match)."""
    _load_carriers()
    normalized = _normalize_for_match(value)

    # Direct match
    if normalized in _KNOWN_CARRIERS:
        return True

    # Check if any known carrier is contained in the value
    # e.g., "Chubb Bermuda" contains "chubb"
    for carrier in _KNOWN_CARRIERS:
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
    _load_carriers()
    normalized = _normalize_for_match(value)

    # Direct match only - don't do substring matching on non-carrier terms
    # This prevents "Chubb Bermuda" from matching "Bermuda"
    # and "London - Fidelis" from matching "London"
    if normalized in _NON_CARRIERS:
        return True

    # For compound non-carrier terms (like "RT Layer"), check if value starts with them
    # But ONLY for multi-word non-carrier terms to avoid blocking "London - Fidelis"
    for term in _NON_CARRIERS:
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


def extract_adaptive(ws) -> tuple[list[CarrierEntry], list[LayerSummary]]:
    """Extract tower data by analyzing merged cell structure and spatial patterns.

    Returns:
        tuple: (carrier_entries, layer_summaries)
            - carrier_entries: List of per-carrier participation data
            - layer_summaries: List of layer-level aggregate data (for cross-checking)
    """

    # Step 1: Find all blocks (merged regions and significant single cells)
    blocks = _find_all_blocks(ws)

    # Step 2: Classify blocks by content
    _classify_blocks(blocks)

    # Step 3: Detect summary/aggregate columns to exclude from carrier extraction
    # These columns contain layer-level data like "Annualized Layer Rate" not per-carrier data
    summary_info = _detect_summary_columns(ws)
    summary_cols = summary_info["columns"]

    # Step 4: Find layer structure by looking for large limit values
    layers = _identify_layers(blocks, ws)

    # Step 5: For each layer, find carrier blocks and their associated data
    entries = []
    layer_summaries = []
    for layer in layers:
        layer_entries = _extract_layer_data(ws, blocks, layer, summary_cols)
        entries.extend(layer_entries)

        # Extract layer summary data from summary columns (for cross-checking)
        summary = _extract_layer_summary(ws, layer, summary_info)
        if summary:
            layer_summaries.append(summary)

    return entries, layer_summaries


def _detect_summary_columns(ws) -> dict:
    """Detect columns that contain summary/aggregate data rather than per-carrier data.

    These columns typically have headers like:
    - "Annualized Layer Rate"
    - "Layer Bound Premiums"
    - "Layer Rates"
    - "Layer Target"

    Returns dict with:
        - 'columns': set of column numbers to exclude from carrier extraction
        - 'bound_premium_col': column with Layer Bound Premiums (for cross-check)
        - 'layer_target_col': column with Layer Target
        - 'layer_rate_col': column with Layer Rate
    """
    result = {
        "columns": set(),
        "bound_premium_col": None,
        "layer_target_col": None,
        "layer_rate_col": None,
    }

    # Also detect year-prefixed layer premium columns (e.g., "2019 Layer Premium")
    # These are summary columns showing premium totals by year, not per-carrier data
    year_layer_premium_pattern = re.compile(r"^\d{4}\s+layer\s+premium", re.IGNORECASE)

    # Scan header rows for summary column indicators
    for row in range(1, MAX_HEADER_SCAN_ROW + 1):
        for col in range(1, min(ws.max_column + 1, MAX_HEADER_SCAN_COLUMN)):
            cell = ws.cell(row=row, column=col)
            val = cell.value
            if val and isinstance(val, str):
                # Normalize whitespace for pattern matching
                val_lower = " ".join(val.lower().split())

                # Check for year-prefixed layer premium (e.g., "2019 Layer Premium")
                if year_layer_premium_pattern.match(val_lower):
                    result["columns"].add(col)
                    # Also mark consecutive columns to the right as summary (Fees, Taxes, Total)
                    # These typically follow the year layer premium column
                    for extra_col in range(col + 1, min(col + 5, ws.max_column + 1)):
                        extra_val = ws.cell(row=row, column=extra_col).value
                        if extra_val and isinstance(extra_val, str):
                            extra_lower = extra_val.lower().strip()
                            if extra_lower in ("fees", "total") or "tax" in extra_lower:
                                result["columns"].add(extra_col)
                            # Also catch year layer rate (e.g., "2019 Layer Rate")
                            if re.match(r"^\d{4}\s+layer\s+rate", extra_lower):
                                result["columns"].add(extra_col)
                                result["layer_rate_col"] = extra_col
                    continue

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

    return result


def _extract_layer_summary(ws, layer: dict, summary_info: dict) -> LayerSummary | None:
    """Extract layer-level summary data from summary columns.

    This data is used for cross-checking that carrier premiums sum to layer totals.

    Args:
        ws: The worksheet
        layer: Layer dict with limit, start_row, end_row
        summary_info: Dict with bound_premium_col, layer_target_col, layer_rate_col

    Returns:
        LayerSummary or None if no summary data found for this layer
    """
    bound_premium_col = summary_info.get("bound_premium_col")
    layer_target_col = summary_info.get("layer_target_col")
    layer_rate_col = summary_info.get("layer_rate_col")

    # If no summary columns detected, skip
    if not any([bound_premium_col, layer_target_col, layer_rate_col]):
        return None

    start_row = layer["start_row"]
    end_row = layer["end_row"]

    layer_bound_premium = None
    layer_target = None
    layer_rate = None
    excel_range = None

    # Look for values in summary columns within this layer's row range
    # Summary values are typically in a specific row for each layer
    for row in range(start_row, end_row + 1):
        if bound_premium_col:
            val = get_cell_value(ws, row, bound_premium_col)
            if val is not None and isinstance(val, int | float) and val > 0:
                layer_bound_premium = float(val)
                excel_range = f"{get_column_letter(bound_premium_col)}{row}"

        if layer_target_col:
            val = get_cell_value(ws, row, layer_target_col)
            if val is not None and isinstance(val, int | float) and val > 0:
                layer_target = float(val)

        if layer_rate_col:
            val = get_cell_value(ws, row, layer_rate_col)
            if val is not None and isinstance(val, int | float):
                # Rate could be very small (e.g., 0.0038)
                layer_rate = float(val)

    # Only return if we found at least one value
    if layer_bound_premium is not None or layer_target is not None or layer_rate is not None:
        return LayerSummary(
            layer_limit=layer["limit"],
            layer_target=layer_target,
            layer_rate=layer_rate,
            layer_bound_premium=layer_bound_premium,
            excel_range=excel_range,
        )

    return None


def _find_all_blocks(ws) -> list[Block]:
    """Find all merged cell regions and significant single cells."""
    blocks = []
    processed = set()

    for row in range(1, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            if (row, col) in processed:
                continue

            val = get_cell_value(ws, row, col)
            if val is None or (isinstance(val, str) and not val.strip()):
                processed.add((row, col))
                continue

            # Check for merged range
            merged = find_merged_range_at(ws, row, col)
            if merged:
                min_c, min_r, max_c, max_r = range_boundaries(merged)
                # Only process from top-left
                if row != min_r or col != min_c:
                    processed.add((row, col))
                    continue

                block = Block(
                    row=min_r, col=min_c, value=val, rows=max_r - min_r + 1, cols=max_c - min_c + 1
                )
                # Mark all cells in merge as processed
                for r in range(min_r, max_r + 1):
                    for c in range(min_c, max_c + 1):
                        processed.add((r, c))
            else:
                block = Block(row=row, col=col, value=val)
                processed.add((row, col))

            blocks.append(block)

    return blocks


def _classify_blocks(blocks: list[Block]):
    """Classify each block by analyzing its content."""
    for block in blocks:
        block.field_type, block.confidence = _infer_type(block.value)


def _infer_numeric_type(value: int | float) -> tuple[str, float]:
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


def _infer_dollar_string_type(val: str, val_lower: str) -> tuple[str, float] | None:
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


def _infer_carrier_type(val: str, val_lower: str) -> tuple[str, float] | None:
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


def _infer_type(value) -> tuple[str, float]:
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
    if len(val) <= 3 and not _is_known_carrier(val):
        return "label", 0.6

    # Check against known carrier names (from YAML) - fuzzy match
    if _is_known_carrier(val):
        return "carrier", 0.9

    # Check carrier name heuristics
    carrier_result = _infer_carrier_type(val, val_lower)
    if carrier_result:
        return carrier_result

    return "text", 0.3


def _has_conflicting_label(block: Block, other: Block) -> bool:
    """Check if another block indicates this block is not a layer limit.

    Returns True if the other block contains patterns that indicate the
    current block's row contains data, not layer definitions.
    """
    # Check same-row labels that indicate data rows
    if other.field_type == "label" and other.row == block.row:
        val_lower = str(other.value).lower()
        # "LIMIT" in column A means per-carrier limits, not layer limit
        # "Premium" or "Policy" means this row has data, not layer definitions
        if "premium" in val_lower or val_lower == "limit" or "policy" in val_lower:
            return True

    # Check for year patterns in same row - "2019 Bound", "2018 Marketing" etc.
    # These indicate summary/historical rows, not layer definitions
    if other.row == block.row:
        val_str = str(other.value)
        if re.match(r"^20\d{2}\b", val_str):  # Starts with year like 2019, 2018
            return True

    # Check the row ABOVE - if it contains "Premium" or "Share Premium" labels,
    # this row contains premium data, not layer limits
    if other.field_type == "label" and other.row == block.row - 1:
        val_lower = str(other.value).lower()
        if "premium" in val_lower or "participation" in val_lower:
            return True

    return False


def _should_skip_large_number_block(block: Block, blocks: list[Block]) -> bool:
    """Check if a large_number block should be skipped as a layer limit candidate."""
    return any(_has_conflicting_label(block, other) for other in blocks)


def _is_valid_limit_block(block: Block, blocks: list[Block]) -> bool:
    """Check if a block is a valid layer limit candidate."""
    # Must be limit or large_number type with sufficient confidence
    if block.field_type not in ("limit", "large_number") or block.confidence < 0.7:
        return False

    # Only consider blocks in leftmost columns (A or B) for layer limits
    if block.col > MAX_LAYER_LIMIT_COLUMN:
        return False

    # Filter out aggregate totals - numbers > $1B are almost never layer limits
    if isinstance(block.value, int | float) and block.value > BILLION:
        return False

    # For large_number type, check for conflicting labels nearby
    if block.field_type == "large_number" and _should_skip_large_number_block(block, blocks):
        return False

    return True


def _identify_layers(blocks: list[Block], ws) -> list[dict]:
    """Identify layer boundaries from limit blocks."""
    # Find blocks that look like layer limits
    # Layer limits should be:
    # 1. In column A or B (leftmost columns)
    # 2. Formatted as dollar amounts with M/K suffix, OR
    # 3. Large numbers that are explicitly labeled as limits
    limit_blocks = [b for b in blocks if _is_valid_limit_block(b, blocks)]

    # Sort by row
    limit_blocks.sort(key=lambda b: b.row)

    # Filter to keep only "primary" limits (leftmost in their row region)
    primary_limits = _filter_primary_limits(limit_blocks)

    # Build layer info from primary limits
    return _build_layer_info(primary_limits, ws.max_row)


def _is_dominated_by_existing(block: Block, existing_limits: list[Block]) -> bool:
    """Check if a block is dominated by an existing limit in its row region."""
    return any(
        abs(block.row - existing.row) <= LAYER_ROW_PROXIMITY and block.col > existing.col
        for existing in existing_limits
    )


def _filter_primary_limits(limit_blocks: list[Block]) -> list[Block]:
    """Filter limit blocks to keep only the primary (leftmost) in each row region."""
    primary_limits = []
    for block in limit_blocks:
        if not _is_dominated_by_existing(block, primary_limits):
            primary_limits.append(block)
    return primary_limits


def _build_layer_info(primary_limits: list[Block], max_row: int) -> list[dict]:
    """Build layer info dictionaries from primary limit blocks."""
    layers = []
    for i, block in enumerate(primary_limits):
        end_row = primary_limits[i + 1].row - 1 if i + 1 < len(primary_limits) else max_row
        layers.append({
            "limit": _format_limit(block.value),
            "limit_row": block.row,
            "limit_col": block.col,
            "start_row": block.row,
            "end_row": end_row,
        })
    return layers


def _format_limit(value) -> str:
    """Format a limit value for display."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int | float):
        return parse_limit_value(value)
    return str(value)


def _split_multiline_carrier(carrier_block: Block) -> list[tuple[Block, str]]:
    """Split a carrier block containing multiple carriers (newlines) into separate blocks.

    Returns list of tuples: (block, original_cell_ref)
    The original_cell_ref preserves the actual Excel cell for traceability.
    """
    value = carrier_block.value
    original_cell = f"{get_column_letter(carrier_block.col)}{carrier_block.row}"

    if not isinstance(value, str):
        return [(carrier_block, original_cell)]

    # Split on newlines
    lines = [line.strip() for line in value.split("\n") if line.strip()]

    # If only one line, return original
    if len(lines) <= 1:
        return [(carrier_block, original_cell)]

    # Create a new block for each line
    split_blocks = []
    for i, line in enumerate(lines):
        # Skip if it looks like a non-carrier (policy number, label, etc.)
        if _looks_like_policy_number(line):
            continue
        if _is_non_carrier(line):
            continue

        # Create new block with adjusted row for data matching
        # but preserve original cell reference for traceability
        new_block = Block(
            row=carrier_block.row + i,  # Adjust row for data proximity matching
            col=carrier_block.col,
            value=line,
            rows=1,
            cols=carrier_block.cols,
            field_type="carrier",
            confidence=carrier_block.confidence,
        )
        split_blocks.append((new_block, original_cell))

    return split_blocks if split_blocks else [(carrier_block, original_cell)]


def _extract_layer_data(
    ws, blocks: list[Block], layer: dict, summary_cols: set[int] = None
) -> list[CarrierEntry]:
    """Extract carrier entries from a layer region.

    Args:
        ws: The worksheet
        blocks: All classified blocks
        layer: Layer dict with start_row, end_row, limit
        summary_cols: Set of column numbers to exclude (contain aggregate data, not per-carrier)
    """
    entries = []
    start_row = layer["start_row"]
    end_row = layer["end_row"]
    summary_cols = summary_cols or set()

    # Find all blocks in this layer's row range
    layer_blocks = [b for b in blocks if start_row <= b.row <= end_row]

    # Find column headers for this layer
    column_headers = _find_column_headers(ws, blocks, layer)

    # Find row labels for this layer (Premium vs % Premium distinction)
    row_labels = _find_row_labels(ws, blocks, layer)

    # Find carrier blocks, excluding those in summary columns
    carrier_blocks = [
        b
        for b in layer_blocks
        if b.field_type == "carrier" and b.confidence >= 0.5 and b.col not in summary_cols
    ]

    # Split multi-line carrier blocks into individual carriers
    # Returns list of (block, original_cell_ref) tuples
    expanded_carriers = []
    for carrier in carrier_blocks:
        expanded_carriers.extend(_split_multiline_carrier(carrier))

    # Find data blocks (percentages, currency, terms)
    # Note: large_number is included because premium values can be > $1M
    # Exclude data from summary columns as well
    data_blocks = [
        b
        for b in layer_blocks
        if b.field_type
        in (
            "percentage",
            "percentage_or_number",
            "currency",
            "currency_string",
            "large_number",
            "zero",
            "terms",
            "layer_description",
        )
        and b.col not in summary_cols
    ]

    # Try to match carriers with their data using spatial proximity
    for carrier, original_cell in expanded_carriers:
        entry = _build_entry_from_proximity(
            ws, carrier, data_blocks, layer, column_headers, row_labels, original_cell
        )
        if entry:
            entries.append(entry)

    return entries


def _find_column_headers(ws, blocks: list[Block], layer: dict) -> dict:
    """Find column header positions for Premium, Limit, Rate, TIV, etc.

    Looks in two places:
    1. Rows near/above the layer start (global headers)
    2. Within the layer (sub-headers for complex schematics)
    """
    headers = {}

    # First pass: look in rows near or above the layer start (traditional layout)
    search_start = max(1, layer["start_row"] - 5)
    search_end = layer["start_row"] + 3

    for block in blocks:
        if block.row < search_start or block.row > search_end:
            continue
        if block.field_type != "label":
            continue

        val_lower = str(block.value).lower().strip()
        _classify_column_header(val_lower, block.col, headers)

    # Second pass: look for sub-headers within the layer (for complex schematics)
    # Look for specific headers that appear mid-layer as data table column headers
    # These are typically in columns beyond A/B (which contain row labels)
    for block in blocks:
        if block.row < layer["start_row"] or block.row > layer["end_row"]:
            continue
        if block.field_type != "label":
            continue
        if block.col <= 2:  # Skip row labels in columns A/B
            continue

        val_lower = str(block.value).lower().strip()

        # Detect Rate headers
        if val_lower == "rate" and "rate_col" not in headers:
            headers["rate_col"] = block.col

        # Detect PREMIUM column header (uppercase "PREMIUM" is often a column header)
        # This takes precedence over row labels like "Share Premium"
        elif val_lower == "premium" and block.col > 2:
            headers["premium_col"] = block.col

        # TIV detection
        elif ("tiv" in val_lower or val_lower == "updated tiv") and "tiv_col" not in headers:
            headers["tiv_col"] = block.col
            if "tiv_data_col" not in headers:
                headers["tiv_data_col"] = block.col + 1

    return headers


def _classify_column_header(val_lower: str, col: int, headers: dict):
    """Classify a column header and update headers dict."""
    if "premium" in val_lower and "limit" not in val_lower:
        if "% premium" in val_lower or "share" in val_lower:
            if "premium_share_col" not in headers:
                headers["premium_share_col"] = col
        else:
            if "premium_col" not in headers:
                headers["premium_col"] = col
    elif "limit" in val_lower:
        if "limit_col" not in headers:
            headers["limit_col"] = col
    elif "participation" in val_lower or "% share" in val_lower or val_lower == "share":
        if "participation_col" not in headers:
            headers["participation_col"] = col
    elif val_lower == "rate":
        if "rate_col" not in headers:
            headers["rate_col"] = col
    elif "tiv" in val_lower or val_lower == "updated tiv":
        if "tiv_col" not in headers:
            headers["tiv_col"] = col
            if "tiv_data_col" not in headers:
                headers["tiv_data_col"] = col + 1


def _find_row_labels(ws, blocks: list[Block], layer: dict) -> dict:
    """Find row label positions for Premium, % Premium, etc.

    Many schematics use row labels in column A to indicate what each row contains.
    Some schematics (like Super Hard) repeat labels per carrier column.
    This helps distinguish between "Premium" row and "% Premium" row.
    """
    labels = {}
    start_row = layer["start_row"]
    end_row = layer["end_row"]

    # First pass: look for labels in columns A or B (traditional layout)
    for block in blocks:
        if block.row < start_row or block.row > end_row:
            continue
        if block.col > 2:
            continue
        if block.field_type != "label":
            continue

        val_lower = str(block.value).lower().strip()
        _classify_row_label(val_lower, block.row, labels)

    # Second pass: if we didn't find key labels, look in any column
    # (for schematics where labels repeat per carrier column)
    if "premium_row" not in labels or "participation_row" not in labels:
        for block in blocks:
            if block.row < start_row or block.row > end_row:
                continue
            if block.field_type != "label":
                continue

            val_lower = str(block.value).lower().strip()
            _classify_row_label(val_lower, block.row, labels)

    return labels


def _classify_row_label(val_lower: str, row: int, labels: dict):
    """Classify a row label and update the labels dict if not already set."""
    # Identify row types by labels
    if "premium" in val_lower:
        if "% premium" in val_lower or val_lower.startswith("%"):
            if "percent_premium_row" not in labels:
                labels["percent_premium_row"] = row
        elif val_lower == "premium" or val_lower == "share premium" or "layer premium" in val_lower:
            if "premium_row" not in labels:
                labels["premium_row"] = row
    elif val_lower == "limit":
        # "LIMIT" row often contains premium/limit values per carrier
        if "limit_row" not in labels:
            labels["limit_row"] = row
    elif "participation" in val_lower or "% share" in val_lower or val_lower == "share":
        if "participation_row" not in labels:
            labels["participation_row"] = row
    elif "carrier" in val_lower:
        if "carrier_row" not in labels:
            labels["carrier_row"] = row
    elif "layer" in val_lower and "premium" not in val_lower:
        if "layer_row" not in labels:
            labels["layer_row"] = row
    elif "terms" in val_lower:
        if "terms_row" not in labels:
            labels["terms_row"] = row
    elif "policy" in val_lower:
        # Track policy number row so we don't mistake it for premium
        if "policy_row" not in labels:
            labels["policy_row"] = row


# =============================================================================
# Proximity Matching Helpers
# =============================================================================


def _get_column_range(block: Block) -> range:
    """Get the range of columns spanned by a block."""
    return range(block.col, block.col + block.cols)


def _columns_overlap(range1: range, range2: range) -> bool:
    """Check if two column ranges overlap."""
    return any(c in range2 for c in range1) or any(c in range1 for c in range2)


def _calculate_block_proximity(block: Block, carrier: Block, carrier_col_range: range) -> tuple:
    """Calculate proximity score for sorting blocks by relevance to carrier.

    Returns:
        Tuple of (not_column_aligned, row_distance) for sorting.
        Lower values = higher priority.
    """
    block_col_range = _get_column_range(block)
    col_overlap = _columns_overlap(block_col_range, carrier_col_range)
    row_dist = abs(block.row - carrier.row)
    return (not col_overlap, row_dist)


def _is_block_relevant(
    block: Block, carrier: Block, carrier_col_range: range, row_range: range
) -> bool:
    """Check if a data block is relevant to a carrier based on spatial proximity.

    A block is relevant if:
    - It's in the carrier's column range, OR
    - It's in the same row (±1) and within MAX_COLUMN_DISTANCE columns
    """
    block_col_range = _get_column_range(block)
    in_col = _columns_overlap(block_col_range, carrier_col_range)

    if in_col:
        return True

    # For non-column-aligned blocks, require same row and close proximity
    if abs(block.row - carrier.row) <= 1 and abs(block.col - carrier.col) <= MAX_COLUMN_DISTANCE:
        return True

    return False


def _match_participation_block(
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


def _match_currency_block(
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
    # Extract column headers
    tiv_col = column_headers.get("tiv_col") if column_headers else None
    tiv_data_col = column_headers.get("tiv_data_col") if column_headers else None
    limit_col = column_headers.get("limit_col") if column_headers else None
    premium_col = column_headers.get("premium_col") if column_headers else None
    premium_share_col = column_headers.get("premium_share_col") if column_headers else None

    # Extract row labels
    policy_row = row_labels.get("policy_row") if row_labels else None
    percent_premium_row = row_labels.get("percent_premium_row") if row_labels else None
    premium_row = row_labels.get("premium_row") if row_labels else None
    limit_row = row_labels.get("limit_row") if row_labels else None

    # Skip TIV columns
    if tiv_col and block.col == tiv_col:
        return current_premium, current_premium_share
    if tiv_data_col and block.col == tiv_data_col:
        return current_premium, current_premium_share

    val = _parse_currency(block.value)
    if val is None:
        return current_premium, current_premium_share

    # Skip policy number row
    if policy_row and block.row == policy_row:
        return current_premium, current_premium_share

    # Skip Limit column
    if limit_col and block.col == limit_col:
        return current_premium, current_premium_share

    # Check for % Premium / Share Premium row (carrier's share)
    if percent_premium_row:
        if block.row == percent_premium_row or block.row == percent_premium_row + 1:
            if current_premium is None:
                return val, current_premium_share
            return current_premium, current_premium_share

    # Check for Premium row (layer total)
    if premium_row:
        if block.row == premium_row or block.row == premium_row + 1:
            if percent_premium_row:
                # Skip layer totals when we have % Premium row
                return current_premium, current_premium_share
            elif current_premium is None:
                return val, current_premium_share
            return current_premium, current_premium_share

    # Check for LIMIT row
    if limit_row and block.row == limit_row:
        if current_premium is None:
            return val, current_premium_share
        return current_premium, current_premium_share

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


def _build_entry_from_proximity(
    ws,
    carrier: Block,
    data_blocks: list[Block],
    layer: dict,
    column_headers: dict = None,
    row_labels: dict = None,
    original_cell: str = None,
) -> CarrierEntry:
    """Build a CarrierEntry by finding spatially related data blocks.

    Args:
        ws: The worksheet
        carrier: The carrier block to build an entry for
        data_blocks: List of data blocks to search for related data
        layer: Layer dict with limit, start_row, end_row
        column_headers: Dict of column header positions
        row_labels: Dict of row label positions
        original_cell: The actual Excel cell reference (for multi-line carriers)

    Returns:
        CarrierEntry with extracted data
    """
    # Define search ranges
    carrier_col_range = _get_column_range(carrier)
    row_range = range(carrier.row, min(carrier.row + MAX_ROW_SEARCH_DISTANCE, layer["end_row"] + 1))

    # Initialize extracted values
    participation = None
    premium = None
    premium_share = None
    terms = None
    layer_desc = None

    # Get rate column for filtering (Rate != participation)
    rate_col = column_headers.get("rate_col") if column_headers else None

    # Sort data blocks by proximity to carrier
    sorted_blocks = sorted(
        data_blocks,
        key=lambda b: _calculate_block_proximity(b, carrier, carrier_col_range),
    )

    # Process each block
    for block in sorted_blocks:
        # Skip blocks that aren't relevant to this carrier
        if not _is_block_relevant(block, carrier, carrier_col_range, row_range):
            continue

        # Match percentage blocks (participation)
        if block.field_type in ("percentage", "percentage_or_number") and participation is None:
            matched = _match_participation_block(block, row_labels, rate_col)
            if matched is not None:
                participation = matched

        # Match currency blocks (premium)
        elif block.field_type in ("currency", "currency_string", "large_number", "zero"):
            premium, premium_share = _match_currency_block(
                block, column_headers, row_labels, premium, premium_share
            )

        # Match terms
        elif block.field_type == "terms" and terms is None:
            terms = str(block.value).strip()

        # Match layer description
        elif block.field_type == "layer_description" and layer_desc is None:
            layer_desc = str(block.value).strip()

    # Build cell reference
    cell_ref = original_cell if original_cell else f"{get_column_letter(carrier.col)}{carrier.row}"

    # Parse attachment point from carrier name or layer description
    carrier_name = str(carrier.value).strip()
    _, attachment_point = parse_excess_notation(carrier_name)
    if not attachment_point and layer_desc:
        _, attachment_point = parse_excess_notation(layer_desc)

    return CarrierEntry(
        layer_limit=layer["limit"],
        layer_description=layer_desc or "",
        carrier=carrier_name,
        participation_pct=participation,
        premium=premium,
        premium_share=premium_share,
        terms=terms,
        policy_number=None,
        excel_range=cell_ref,
        col_span=carrier.cols,
        row_span=carrier.rows,
        fill_color=get_cell_color(ws, carrier.row, carrier.col),
        attachment_point=attachment_point,
    )


def _normalize_percentage(value) -> float:
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


def _parse_currency(value) -> float:
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


def extract_schematic(filepath: str, sheet_name: str | None = None) -> list[dict]:
    """Extract insurance tower schematic data from an Excel file.

    This is the main entry point for the library. It analyzes the spreadsheet
    structure to extract carrier participation data from insurance tower diagrams.

    Args:
        filepath: Path to the Excel file (.xlsx)
        sheet_name: Optional sheet name (uses active sheet if not specified)

    Returns:
        List of carrier entry dictionaries, each containing:
        - layer_limit: Layer limit (e.g., "$250M")
        - layer_description: Layer description if any
        - carrier: Carrier name
        - participation_pct: Participation percentage (0-1 scale)
        - premium: Premium amount
        - excel_range: Source cell reference (e.g., "H47")
        - col_span, row_span: Cell span information
        - fill_color: Cell background color if any
        - attachment_point: Parsed from "xs." notation

    Example:
        >>> from schematic_explorer import extract_schematic
        >>> entries = extract_schematic("tower.xlsx")
        >>> for entry in entries:
        ...     print(f"{entry['carrier']}: {entry['participation_pct']}")
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)

    if sheet_name:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    entries, _ = extract_adaptive(ws)
    return [entry.to_dict() for entry in entries]


def extract_schematic_with_summaries(
    filepath: str, sheet_name: str | None = None
) -> tuple[list[dict], list[dict]]:
    """Extract schematic data along with layer summaries for cross-checking.

    Args:
        filepath: Path to the Excel file
        sheet_name: Optional sheet name

    Returns:
        Tuple of (carrier_entries, layer_summaries)
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    entries, summaries = extract_adaptive(ws)
    return ([entry.to_dict() for entry in entries], [summary.to_dict() for summary in summaries])
