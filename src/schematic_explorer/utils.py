"""Utility functions for Excel cell operations."""

from typing import Any

from openpyxl.utils import range_boundaries


def find_merged_range_at(ws, row: int, col: int) -> str | None:
    """Find if a cell is part of a merged range, return the range string."""
    for merged_range in ws.merged_cells.ranges:
        min_col, min_row, max_col, max_row = range_boundaries(str(merged_range))
        if min_row <= row <= max_row and min_col <= col <= max_col:
            return str(merged_range)
    return None


def get_cell_value(ws, row: int, col: int) -> Any:
    """Get cell value, handling merged cells (value is in top-left)."""
    merged = find_merged_range_at(ws, row, col)
    if merged:
        min_col, min_row, _, _ = range_boundaries(merged)
        return ws.cell(row=min_row, column=min_col).value
    return ws.cell(row=row, column=col).value


def get_cell_color(ws, row: int, col: int) -> str | None:
    """Get background color of a cell as hex string."""
    merged = find_merged_range_at(ws, row, col)
    if merged:
        min_col, min_row, _, _ = range_boundaries(merged)
        cell = ws.cell(row=min_row, column=min_col)
    else:
        cell = ws.cell(row=row, column=col)

    if cell.fill and cell.fill.fgColor:
        color = cell.fill.fgColor
        if color.type == "rgb" and color.rgb and color.rgb not in ("00000000", "000000"):
            return color.rgb
    return None
