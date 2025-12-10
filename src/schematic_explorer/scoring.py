"""Score calculation utilities for verification and preflight."""


def clamp_score(score: float) -> float:
    """Clamp score to valid 0.0-1.0 range.

    Args:
        score: Raw score value

    Returns:
        Score clamped between 0.0 and 1.0
    """
    return max(0.0, min(1.0, score))


def apply_penalty(
    score: float,
    penalty_per_item: float,
    count: int = 1,
    max_penalty: float | None = None,
) -> float:
    """Apply a penalty to a score, optionally capped.

    Args:
        score: Current score (0.0-1.0)
        penalty_per_item: Penalty to apply per item
        count: Number of items to penalize for
        max_penalty: Maximum total penalty (None = no cap)

    Returns:
        Score after penalty, clamped to >= 0.0
    """
    total_penalty = penalty_per_item * count
    if max_penalty is not None:
        total_penalty = min(total_penalty, max_penalty)
    return clamp_score(score - total_penalty)


def calculate_weighted_score(
    weights: dict[str, float],
    present: dict[str, float],
) -> float:
    """Calculate weighted score from component values.

    Args:
        weights: Dict mapping component name to weight (should sum to 1.0)
        present: Dict mapping component name to confidence (0.0-1.0)
                 Missing components contribute 0.

    Returns:
        Weighted sum of component scores
    """
    total = 0.0
    for component, weight in weights.items():
        confidence = present.get(component, 0.0)
        total += weight * confidence
    return total
