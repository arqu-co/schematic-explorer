"""Main extraction orchestrator."""

from typing import Optional
import openpyxl

from .models import CarrierEntry, LayerSummary
from .extract_adaptive import extract_adaptive


def extract_tower_data(
    filepath: str,
    sheet_name: Optional[str] = None
) -> tuple[list[CarrierEntry], list[LayerSummary]]:
    """
    Main extraction function. Uses adaptive extraction that analyzes structure dynamically.

    Args:
        filepath: Path to the Excel file
        sheet_name: Optional sheet name (uses active sheet if not specified)

    Returns:
        tuple: (carrier_entries, layer_summaries)
            - carrier_entries: List of CarrierEntry objects representing per-carrier data
            - layer_summaries: List of LayerSummary objects for cross-checking layer totals
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)

    if sheet_name:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    return extract_adaptive(ws)
