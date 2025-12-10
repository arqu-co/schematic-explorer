"""AI-powered verification of extracted tower data.

This package provides verification functionality using Gemini for:
- Comparing extracted data against original Excel files
- Visual snapshot verification
- Cross-validation to filter false positives
- Layer total cross-checking

The package is split into focused modules:
- core: Main verification functions (verify_extraction, verify_file, etc.)
- formatting: Excel/text formatting utilities
- gemini: Gemini API client and request handling
- layer_check: Layer total cross-checking
- prompts: Verification prompts and schemas
"""

# Re-export public API for backward compatibility
from .core import (
    create_error_result,
    cross_validate,
    get_snapshot_path,
    verify_extraction,
    verify_file,
    verify_snapshot,
)
from .formatting import (
    entries_to_text,
    excel_to_text,
    format_cell_rows,
    format_merged_cells,
    load_workbook_for_verification,
)
from .gemini import (
    get_client,
    make_gemini_request,
    parse_json_response,
)
from .layer_check import (
    build_carrier_totals_by_layer,
    calculate_discrepancy_pct,
    check_extreme_discrepancy,
    check_missing_carriers,
    cross_check_layer_totals,
)
from .prompts import (
    CROSS_VALIDATION_PROMPT,
    CROSS_VALIDATION_SCHEMA,
    SNAPSHOT_VERIFICATION_PROMPT,
    SNAPSHOT_VERIFICATION_SCHEMA,
    VERIFICATION_PROMPT,
    VERIFICATION_PROMPT_TEXT_ONLY,
    VERIFICATION_SCHEMA,
)

__all__ = [
    # Core verification
    "verify_extraction",
    "verify_file",
    "verify_snapshot",
    "cross_validate",
    "create_error_result",
    "get_snapshot_path",
    # Formatting
    "excel_to_text",
    "entries_to_text",
    "format_cell_rows",
    "format_merged_cells",
    "load_workbook_for_verification",
    # Gemini
    "get_client",
    "make_gemini_request",
    "parse_json_response",
    # Layer checking
    "cross_check_layer_totals",
    "build_carrier_totals_by_layer",
    "calculate_discrepancy_pct",
    "check_missing_carriers",
    "check_extreme_discrepancy",
    # Prompts and schemas
    "VERIFICATION_SCHEMA",
    "SNAPSHOT_VERIFICATION_SCHEMA",
    "CROSS_VALIDATION_SCHEMA",
    "VERIFICATION_PROMPT",
    "VERIFICATION_PROMPT_TEXT_ONLY",
    "SNAPSHOT_VERIFICATION_PROMPT",
    "CROSS_VALIDATION_PROMPT",
]
