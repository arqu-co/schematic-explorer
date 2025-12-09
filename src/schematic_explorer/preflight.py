"""Preflight check for Excel files - assess extraction confidence before processing.

This module provides a way to assess whether an Excel file can be extracted
and estimate the confidence level of the extraction.

Example:
    >>> from schematic_explorer import preflight
    >>> result = preflight("tower.xlsx")
    >>> if result.can_extract:
    ...     print(f"Ready to extract with {result.confidence:.0%} confidence")
    ... else:
    ...     print(f"Issues: {result.issues}")
"""

from dataclasses import dataclass
from typing import Optional

import openpyxl

from .extractor import Block, _find_all_blocks, _classify_blocks, _identify_layers


@dataclass
class PreflightResult:
    """Results of preflight analysis.

    Attributes:
        file_name: Name of the analyzed file
        sheet_name: Name of the analyzed sheet
        can_extract: Whether extraction is likely to succeed
        confidence: Confidence score from 0.0 to 1.0
        layers_found: Number of layer limits detected
        carriers_found: Number of carrier names detected
        has_percentages: Whether participation percentages were found
        has_currency: Whether premium/currency values were found
        has_terms: Whether terms/conditions text was found
        issues: List of detected issues that may affect extraction
        suggestions: List of suggestions for improving extraction results
    """
    file_name: str
    sheet_name: str
    can_extract: bool
    confidence: float
    layers_found: int
    carriers_found: int
    has_percentages: bool
    has_currency: bool
    has_terms: bool
    issues: list[str]
    suggestions: list[str]


def preflight(
    filepath: str,
    sheet_name: Optional[str] = None
) -> PreflightResult:
    """Run preflight analysis on an Excel file to assess extraction viability.

    This function analyzes the structure of an Excel file to determine:
    - Whether it contains extractable insurance tower data
    - The confidence level of potential extraction
    - What data types are present (carriers, percentages, premiums, etc.)
    - Any issues that might affect extraction quality

    Args:
        filepath: Path to the Excel file to analyze
        sheet_name: Optional sheet name to analyze. If not provided,
                   the active sheet will be used.

    Returns:
        PreflightResult containing analysis results and recommendations.

    Example:
        >>> result = preflight("tower.xlsx")
        >>> print(f"Can extract: {result.can_extract}")
        >>> print(f"Confidence: {result.confidence:.0%}")
        >>> print(f"Layers: {result.layers_found}, Carriers: {result.carriers_found}")
        >>> if result.issues:
        ...     for issue in result.issues:
        ...         print(f"  - {issue}")
    """
    from pathlib import Path

    wb = openpyxl.load_workbook(filepath, data_only=True)

    if sheet_name:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    # Find and classify all blocks
    blocks = _find_all_blocks(ws)
    _classify_blocks(blocks)

    # Identify layers
    layers = _identify_layers(blocks, ws)

    # Analyze what we found
    issues = []
    suggestions = []

    # Count block types
    type_counts = {}
    for block in blocks:
        t = block.field_type or 'unknown'
        type_counts[t] = type_counts.get(t, 0) + 1

    # Check for carriers
    carriers = [b for b in blocks if b.field_type == 'carrier']
    high_conf_carriers = [b for b in carriers if b.confidence >= 0.7]

    # Check for percentages
    percentages = [b for b in blocks if b.field_type in ('percentage', 'percentage_or_number')]

    # Check for currency
    currency = [b for b in blocks if b.field_type in ('currency', 'currency_string')]

    # Check for terms
    terms = [b for b in blocks if b.field_type == 'terms']

    # Assess issues
    if not layers:
        issues.append("No layer limits detected (looking for $XXM patterns or large numbers)")
        suggestions.append("Ensure layer limits are visible as $XXM, $XXK, or numeric values > 1M")

    if not carriers:
        issues.append("No carrier names detected")
        suggestions.append("Carrier names should be text cells with company-like names")
    elif len(high_conf_carriers) < len(carriers) * 0.5:
        issues.append(f"Low confidence on carrier detection ({len(high_conf_carriers)}/{len(carriers)} high confidence)")
        suggestions.append("Carrier names with 'Insurance', 'Inc', 'Lloyd's' etc. are detected with higher confidence")

    if not percentages:
        issues.append("No participation percentages detected")
        suggestions.append("Percentages should be decimal (0.25) or whole numbers (25) or strings ('25%')")

    if not currency:
        issues.append("No premium/currency values detected")
        suggestions.append("Currency values should be numbers > 1000 or strings starting with '$'")

    # Calculate confidence score
    confidence = 0.0
    weights = {
        'layers': 0.3,
        'carriers': 0.3,
        'percentages': 0.2,
        'currency': 0.1,
        'terms': 0.1
    }

    if layers:
        confidence += weights['layers']
    if carriers:
        avg_carrier_conf = sum(c.confidence for c in carriers) / len(carriers)
        confidence += weights['carriers'] * avg_carrier_conf
    if percentages:
        confidence += weights['percentages']
    if currency:
        confidence += weights['currency']
    if terms:
        confidence += weights['terms']

    can_extract = len(layers) > 0 and len(carriers) > 0

    return PreflightResult(
        file_name=Path(filepath).name,
        sheet_name=ws.title,
        can_extract=can_extract,
        confidence=confidence,
        layers_found=len(layers),
        carriers_found=len(carriers),
        has_percentages=len(percentages) > 0,
        has_currency=len(currency) > 0,
        has_terms=len(terms) > 0,
        issues=issues,
        suggestions=suggestions
    )
