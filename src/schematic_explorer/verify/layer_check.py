"""Layer total cross-checking functionality."""

from ..types import CarrierEntry, LayerSummary, VerificationResult

# Cross-check thresholds
LAYER_MISSING_PREMIUM_THRESHOLD = 10000  # Flag if layer shows > $10K but no carriers
LAYER_DISCREPANCY_THRESHOLD = 2.0  # Flag if > 200% difference between carrier sum and layer total
MAX_LAYER_PENALTY = 0.15  # Maximum score reduction for layer discrepancies
PENALTY_PER_DISCREPANCY = 0.05  # Score penalty per discrepancy found


def calculate_discrepancy_pct(expected: float, actual: float) -> float:
    """Calculate discrepancy percentage between expected and actual values."""
    if expected > 0:
        return abs(expected - actual) / expected
    return 0.0 if actual == 0 else 1.0


def check_missing_carriers(
    layer_limit: str, summary: LayerSummary, actual: float
) -> str | None:
    """Check if layer has no carriers but should have data.

    Args:
        layer_limit: The layer limit identifier
        summary: Layer summary with expected values
        actual: Actual carrier premium total

    Returns:
        Issue string or None if no issue
    """
    expected = summary.layer_bound_premium
    if actual == 0 and expected > LAYER_MISSING_PREMIUM_THRESHOLD:
        return (
            f"Layer {layer_limit}: No carrier premiums extracted but "
            f"summary shows ${expected:,.0f} (cell {summary.excel_range}) - possible extraction gap"
        )
    return None


def check_extreme_discrepancy(
    layer_limit: str, summary: LayerSummary, actual: float, discrepancy_pct: float
) -> str | None:
    """Check for extreme discrepancy between carrier sum and layer total.

    Args:
        layer_limit: The layer limit identifier
        summary: Layer summary with expected values
        actual: Actual carrier premium total
        discrepancy_pct: Calculated discrepancy percentage

    Returns:
        Issue string or None if no issue
    """
    expected = summary.layer_bound_premium
    if discrepancy_pct > LAYER_DISCREPANCY_THRESHOLD:
        return (
            f"Layer {layer_limit}: Carrier premiums ${actual:,.0f} vs "
            f"summary ${expected:,.0f} (cell {summary.excel_range}) - "
            f"{discrepancy_pct:.0%} difference (may be prior year data)"
        )
    return None


def build_carrier_totals_by_layer(entries: list[CarrierEntry]) -> dict[str, float]:
    """Group carrier entries by layer and sum premiums.

    Args:
        entries: List of carrier entries

    Returns:
        Dict mapping layer limit to total premium
    """
    totals: dict[str, float] = {}
    for entry in entries:
        layer = entry.layer_limit
        if layer not in totals:
            totals[layer] = 0.0
        if entry.premium is not None:
            totals[layer] += entry.premium
    return totals


def cross_check_layer_totals(
    entries: list[CarrierEntry], layer_summaries: list[LayerSummary], result: VerificationResult
) -> VerificationResult:
    """
    Cross-check extracted carrier premiums against layer summary totals.

    For each layer with a summary, sum the carrier premiums and compare
    to the layer_bound_premium. Large discrepancies indicate extraction issues.

    Args:
        entries: Extracted carrier entries
        layer_summaries: Layer-level summary data from summary columns
        result: Current verification result to augment

    Returns:
        Updated VerificationResult with any layer total issues
    """
    issues = list(result.issues)
    suggestions = list(result.suggestions)

    # Build lookup structures
    summary_by_layer = {s.layer_limit: s for s in layer_summaries}
    carrier_totals_by_layer = build_carrier_totals_by_layer(entries)

    # Cross-check each layer
    discrepancies_found = 0

    for layer_limit, summary in summary_by_layer.items():
        if summary.layer_bound_premium is None:
            continue

        actual = carrier_totals_by_layer.get(layer_limit, 0.0)
        discrepancy_pct = calculate_discrepancy_pct(summary.layer_bound_premium, actual)

        # Check for missing carriers
        issue = check_missing_carriers(layer_limit, summary, actual)
        if issue:
            discrepancies_found += 1
            issues.append(issue)
            continue

        # Check for extreme discrepancy
        issue = check_extreme_discrepancy(layer_limit, summary, actual, discrepancy_pct)
        if issue:
            discrepancies_found += 1
            issues.append(issue)

    # Adjust score only for severe issues
    score = result.score
    if discrepancies_found > 0:
        penalty = min(PENALTY_PER_DISCREPANCY * discrepancies_found, MAX_LAYER_PENALTY)
        score = max(0.0, score - penalty)
        suggestions.append(
            f"Review {discrepancies_found} layer(s) with significant carrier/summary differences "
            "(note: summary columns may show prior year data)"
        )

    return VerificationResult(
        score=score,
        summary=result.summary,
        issues=issues,
        suggestions=suggestions,
        raw_response=result.raw_response,
    )
