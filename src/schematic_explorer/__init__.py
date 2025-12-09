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
"""

from .extractor import extract_schematic, extract_schematic_with_summaries
from .preflight import preflight, PreflightResult
from .types import CarrierEntry, LayerSummary, VerificationResult

__version__ = "0.1.0"

__all__ = [
    "extract_schematic",
    "extract_schematic_with_summaries",
    "preflight",
    "PreflightResult",
    "CarrierEntry",
    "LayerSummary",
    "VerificationResult",
]
