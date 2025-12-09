"""Schematic Explorer - Extract insurance tower schematic data from Excel files.

This library uses AI-powered analysis to extract carrier participation data
from insurance tower diagrams in Excel spreadsheets.

Example:
    >>> from schematic_explorer import extract_schematic
    >>> entries = extract_schematic("tower.xlsx")
    >>> for entry in entries:
    ...     print(f"{entry['carrier']}: {entry['participation_pct']:.1%}")

Preflight check:
    >>> from schematic_explorer import preflight
    >>> result = preflight("tower.xlsx")
    >>> if result.can_extract:
    ...     entries = extract_schematic("tower.xlsx")

Verification:
    >>> from schematic_explorer import verify_file
    >>> result = verify_file("tower.xlsx")
    >>> print(f"Score: {result.score:.0%}")
"""

from .extractor import extract_schematic, extract_schematic_with_summaries
from .preflight import PreflightResult, preflight
from .types import CarrierEntry, LayerSummary, VerificationResult

__version__ = "0.1.0"


def verify_file(filepath: str, sheet_name: str | None = None):
    """Lazy import to avoid requiring google-generativeai for basic usage."""
    from .verify import verify_file as _verify_file
    return _verify_file(filepath, sheet_name)


def verify_extraction(filepath: str, entries, sheet_name: str | None = None):
    """Lazy import to avoid requiring google-generativeai for basic usage."""
    from .verify import verify_extraction as _verify_extraction
    return _verify_extraction(filepath, entries, sheet_name)


__all__ = [
    # Extraction
    "extract_schematic",
    "extract_schematic_with_summaries",
    # Preflight
    "preflight",
    "PreflightResult",
    # Verification
    "verify_file",
    "verify_extraction",
    # Types
    "CarrierEntry",
    "LayerSummary",
    "VerificationResult",
]
