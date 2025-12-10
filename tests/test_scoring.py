"""Tests for schematic_explorer.scoring module (score utilities)."""

import pytest

from schematic_explorer.scoring import (
    apply_penalty,
    calculate_weighted_score,
    clamp_score,
)


class TestClampScore:
    """Tests for clamp_score function."""

    def test_clamp_within_range(self):
        """Score within 0-1 range is unchanged."""
        assert clamp_score(0.5) == 0.5
        assert clamp_score(0.0) == 0.0
        assert clamp_score(1.0) == 1.0

    def test_clamp_below_zero(self):
        """Negative scores clamp to 0."""
        assert clamp_score(-0.5) == 0.0
        assert clamp_score(-1.0) == 0.0

    def test_clamp_above_one(self):
        """Scores above 1 clamp to 1."""
        assert clamp_score(1.5) == 1.0
        assert clamp_score(2.0) == 1.0


class TestApplyPenalty:
    """Tests for apply_penalty function."""

    def test_penalty_reduces_score(self):
        """Penalty reduces the score."""
        assert apply_penalty(1.0, 0.1) == 0.9
        assert apply_penalty(0.8, 0.2) == pytest.approx(0.6)

    def test_penalty_capped_at_max(self):
        """Penalty is capped at max_penalty."""
        # With max_penalty=0.15, 3*0.1=0.3 is capped to 0.15
        assert apply_penalty(1.0, 0.1, count=3, max_penalty=0.15) == 0.85

    def test_penalty_does_not_go_negative(self):
        """Score cannot go below 0."""
        assert apply_penalty(0.1, 0.5) == 0.0

    def test_penalty_count_multiplies(self):
        """Count multiplies the penalty."""
        assert apply_penalty(1.0, 0.05, count=2) == 0.9  # 1.0 - 2*0.05


class TestCalculateWeightedScore:
    """Tests for calculate_weighted_score function."""

    def test_all_components_present(self):
        """Full score when all weighted components are present."""
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        present = {"a": 1.0, "b": 1.0, "c": 1.0}
        assert calculate_weighted_score(weights, present) == 1.0

    def test_partial_components(self):
        """Partial score when some components are missing."""
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        present = {"a": 1.0}  # Only 'a' present, b and c missing
        assert calculate_weighted_score(weights, present) == 0.5

    def test_weighted_by_confidence(self):
        """Components weighted by their confidence value."""
        weights = {"a": 0.6, "b": 0.4}
        present = {"a": 0.5, "b": 1.0}  # a at 50% confidence
        # 0.6 * 0.5 + 0.4 * 1.0 = 0.3 + 0.4 = 0.7
        assert calculate_weighted_score(weights, present) == 0.7

    def test_empty_weights(self):
        """Empty weights returns 0."""
        assert calculate_weighted_score({}, {}) == 0.0

    def test_missing_component_uses_zero(self):
        """Components not in present dict contribute 0."""
        weights = {"a": 0.5, "b": 0.5}
        present = {"a": 1.0}  # b missing
        assert calculate_weighted_score(weights, present) == 0.5
