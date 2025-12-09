"""Schematic Explorer - Extract insurance tower schematic data from Excel files.

This library uses AI-powered analysis to extract carrier participation data
from insurance tower diagrams in Excel spreadsheets.

Example:
    >>> from schematic_explorer import extract_schematic
    >>> entries = extract_schematic("tower.xlsx")
    >>> for entry in entries:
    ...     print(f"{entry['carrier']}: {entry['participation_pct']:.1%}")
"""

from .extractor import extract_schematic, extract_schematic_with_summaries
from .types import CarrierEntry, LayerSummary, VerificationResult

__version__ = "0.1.0"

__all__ = [
    "extract_schematic",
    "extract_schematic_with_summaries",
    "CarrierEntry",
    "LayerSummary",
    "VerificationResult",
]
