"""Tests for schematic_explorer.types module."""

from schematic_explorer.types import (
    CarrierEntry,
    Layer,
    LayerSummary,
    VerificationResult,
    parse_excess_notation,
    parse_limit_for_sort,
    parse_limit_value,
)


class TestLayer:
    """Tests for Layer dataclass."""

    def test_create_basic_layer(self):
        """Test creating a basic Layer."""
        layer = Layer(
            limit="$50M",
            limit_row=5,
            limit_col=1,
            start_row=5,
            end_row=15,
        )
        assert layer.limit == "$50M"
        assert layer.limit_row == 5
        assert layer.limit_col == 1
        assert layer.start_row == 5
        assert layer.end_row == 15

    def test_layer_to_dict(self):
        """Test Layer to_dict conversion."""
        layer = Layer(
            limit="$100M",
            limit_row=10,
            limit_col=2,
            start_row=10,
            end_row=25,
        )
        d = layer.to_dict()
        assert isinstance(d, dict)
        assert d["limit"] == "$100M"
        assert d["limit_row"] == 10
        assert d["limit_col"] == 2
        assert d["start_row"] == 10
        assert d["end_row"] == 25

    def test_layer_equality(self):
        """Test Layer equality comparison."""
        layer1 = Layer(
            limit="$50M",
            limit_row=5,
            limit_col=1,
            start_row=5,
            end_row=15,
        )
        layer2 = Layer(
            limit="$50M",
            limit_row=5,
            limit_col=1,
            start_row=5,
            end_row=15,
        )
        assert layer1 == layer2


class TestCarrierEntry:
    """Tests for CarrierEntry dataclass."""

    def test_create_basic_entry(self):
        """Test creating a basic CarrierEntry."""
        entry = CarrierEntry(
            layer_limit="$50M",
            layer_description="Primary",
            carrier="Test Insurance",
            participation_pct=0.25,
            premium=100000.0,
            premium_share=25000.0,
            terms="All risks",
            policy_number="POL123",
            excel_range="A1",
            col_span=1,
            row_span=1,
        )
        assert entry.layer_limit == "$50M"
        assert entry.carrier == "Test Insurance"
        assert entry.participation_pct == 0.25
        assert entry.premium == 100000.0

    def test_create_entry_with_defaults(self):
        """Test CarrierEntry with optional fields as None."""
        entry = CarrierEntry(
            layer_limit="$100M",
            layer_description="",
            carrier="Another Insurer",
            participation_pct=None,
            premium=None,
            premium_share=None,
            terms=None,
            policy_number=None,
            excel_range="B2",
            col_span=2,
            row_span=3,
        )
        assert entry.participation_pct is None
        assert entry.premium is None
        assert entry.fill_color is None
        assert entry.attachment_point is None

    def test_to_dict(self):
        """Test to_dict conversion."""
        entry = CarrierEntry(
            layer_limit="$25M",
            layer_description="Excess",
            carrier="Lloyd's",
            participation_pct=0.5,
            premium=50000.0,
            premium_share=None,
            terms=None,
            policy_number=None,
            excel_range="C3",
            col_span=1,
            row_span=1,
            fill_color="FFFF00",
            attachment_point="$25M",
        )
        d = entry.to_dict()
        assert isinstance(d, dict)
        assert d["layer_limit"] == "$25M"
        assert d["carrier"] == "Lloyd's"
        assert d["participation_pct"] == 0.5
        assert d["fill_color"] == "FFFF00"
        assert d["attachment_point"] == "$25M"


class TestLayerSummary:
    """Tests for LayerSummary dataclass."""

    def test_create_basic_summary(self):
        """Test creating a basic LayerSummary."""
        summary = LayerSummary(
            layer_limit="$50M",
            layer_target=500000.0,
            layer_rate=0.005,
            layer_bound_premium=475000.0,
            excel_range="Z10",
        )
        assert summary.layer_limit == "$50M"
        assert summary.layer_target == 500000.0
        assert summary.layer_rate == 0.005

    def test_create_summary_with_defaults(self):
        """Test LayerSummary with default None values."""
        summary = LayerSummary(layer_limit="$100M")
        assert summary.layer_target is None
        assert summary.layer_rate is None
        assert summary.layer_bound_premium is None
        assert summary.excel_range is None

    def test_to_dict(self):
        """Test to_dict conversion."""
        summary = LayerSummary(
            layer_limit="$75M",
            layer_bound_premium=300000.0,
        )
        d = summary.to_dict()
        assert isinstance(d, dict)
        assert d["layer_limit"] == "$75M"
        assert d["layer_bound_premium"] == 300000.0
        assert d["layer_target"] is None


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_create_verification_result(self):
        """Test creating a VerificationResult."""
        result = VerificationResult(
            score=0.85,
            summary="Good extraction",
            issues=["Minor mismatch on row 10"],
            suggestions=["Review carrier names"],
            raw_response="Raw AI response here",
        )
        assert result.score == 0.85
        assert result.summary == "Good extraction"
        assert len(result.issues) == 1
        assert len(result.suggestions) == 1

    def test_empty_issues_and_suggestions(self):
        """Test with empty lists."""
        result = VerificationResult(
            score=1.0,
            summary="Perfect",
            issues=[],
            suggestions=[],
            raw_response="",
        )
        assert result.issues == []
        assert result.suggestions == []


class TestParseLimitValue:
    """Tests for parse_limit_value function."""

    def test_none_input(self):
        """Test None input returns None."""
        assert parse_limit_value(None) is None

    def test_large_number_millions(self):
        """Test large numbers formatted as millions."""
        assert parse_limit_value(50_000_000) == "$50M"
        assert parse_limit_value(100_000_000) == "$100M"
        assert parse_limit_value(1_000_000) == "$1M"

    def test_large_number_thousands(self):
        """Test numbers in thousands."""
        assert parse_limit_value(500_000) == "$500K"
        assert parse_limit_value(250_000) == "$250K"
        assert parse_limit_value(1_000) == "$1K"

    def test_small_numbers(self):
        """Test small numbers."""
        assert parse_limit_value(500) == "$500"
        assert parse_limit_value(100) == "$100"
        assert parse_limit_value(0) == "$0"

    def test_float_numbers(self):
        """Test float numbers."""
        assert parse_limit_value(50_000_000.0) == "$50M"
        assert parse_limit_value(500_000.5) == "$500K"

    def test_string_with_dollar(self):
        """Test string starting with $."""
        assert parse_limit_value("$50M") == "$50M"
        assert parse_limit_value("$100K") == "$100K"

    def test_string_numeric(self):
        """Test numeric string."""
        assert parse_limit_value("50000000") == "$50M"
        assert parse_limit_value("500,000") == "$500K"
        assert parse_limit_value("1000") == "$1K"

    def test_string_with_commas(self):
        """Test string with comma separators."""
        assert parse_limit_value("50,000,000") == "$50M"
        # Strings already starting with $ are returned as-is
        assert parse_limit_value("$50,000,000") == "$50,000,000"

    def test_invalid_string(self):
        """Test invalid string returns as-is."""
        assert parse_limit_value("Invalid") == "Invalid"
        assert parse_limit_value("abc") == "abc"

    def test_non_numeric_non_string(self):
        """Test other types return None."""
        assert parse_limit_value([1, 2, 3]) is None
        assert parse_limit_value({"key": "value"}) is None


class TestParseExcessNotation:
    """Tests for parse_excess_notation function."""

    def test_none_input(self):
        """Test None input."""
        limit, attachment = parse_excess_notation(None)
        assert limit is None
        assert attachment is None

    def test_empty_string(self):
        """Test empty string."""
        limit, attachment = parse_excess_notation("")
        assert limit is None
        assert attachment is None

    def test_non_string_input(self):
        """Test non-string input."""
        limit, attachment = parse_excess_notation(12345)
        assert limit is None
        assert attachment is None

    def test_xs_dot_notation(self):
        """Test 'xs.' notation."""
        limit, attachment = parse_excess_notation("Umbrella $50M xs. $50M")
        assert limit == "$50M"
        assert attachment == "$50M"

    def test_xs_slash_notation(self):
        """Test 'x/s' notation."""
        limit, attachment = parse_excess_notation("$25M x/s $25M")
        assert limit == "$25M"
        assert attachment == "$25M"

    def test_excess_of_notation(self):
        """Test 'excess of' notation."""
        limit, attachment = parse_excess_notation("$100M excess of $50M")
        assert limit == "$100M"
        assert attachment == "$50M"

    def test_excess_notation(self):
        """Test 'excess' notation."""
        limit, attachment = parse_excess_notation("$75M excess $25M")
        assert limit == "$75M"
        assert attachment == "$25M"

    def test_no_dollar_sign(self):
        """Test values without $ sign."""
        limit, attachment = parse_excess_notation("50M xs. 25M")
        assert limit == "$50M"
        assert attachment == "$25M"

    def test_limit_only(self):
        """Test string with only limit."""
        limit, attachment = parse_excess_notation("Coverage $100M primary")
        assert limit == "$100M"
        assert attachment is None

    def test_no_excess_notation(self):
        """Test string without excess notation."""
        limit, attachment = parse_excess_notation("Some carrier name")
        assert limit is None
        assert attachment is None

    def test_case_insensitive(self):
        """Test case insensitivity."""
        limit, attachment = parse_excess_notation("$50M XS. $25M")
        assert limit == "$50M"
        assert attachment == "$25M"

        limit, attachment = parse_excess_notation("$50M EXCESS $25M")
        assert limit == "$50M"
        assert attachment == "$25M"


class TestParseLimitForSort:
    """Tests for parse_limit_for_sort function."""

    def test_empty_string(self):
        """Test empty string returns 0."""
        assert parse_limit_for_sort("") == 0
        assert parse_limit_for_sort(None) == 0

    def test_millions(self):
        """Test M suffix."""
        assert parse_limit_for_sort("$50M") == 50_000_000
        assert parse_limit_for_sort("$100M") == 100_000_000
        assert parse_limit_for_sort("50M") == 50_000_000

    def test_thousands(self):
        """Test K suffix."""
        assert parse_limit_for_sort("$500K") == 500_000
        assert parse_limit_for_sort("250K") == 250_000

    def test_billions(self):
        """Test B suffix."""
        assert parse_limit_for_sort("$1B") == 1_000_000_000
        assert parse_limit_for_sort("2B") == 2_000_000_000

    def test_plain_number(self):
        """Test plain numbers."""
        assert parse_limit_for_sort("$50000000") == 50_000_000
        assert parse_limit_for_sort("1000") == 1000

    def test_with_commas(self):
        """Test numbers with commas."""
        assert parse_limit_for_sort("$50,000,000") == 50_000_000
        assert parse_limit_for_sort("1,000,000") == 1_000_000

    def test_invalid_string(self):
        """Test invalid string returns 0."""
        assert parse_limit_for_sort("invalid") == 0
        assert parse_limit_for_sort("abc") == 0

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert parse_limit_for_sort("$50m") == 50_000_000
        assert parse_limit_for_sort("$500k") == 500_000
        assert parse_limit_for_sort("$1b") == 1_000_000_000

    def test_decimal_values(self):
        """Test decimal values."""
        assert parse_limit_for_sort("$2.5M") == 2_500_000
        assert parse_limit_for_sort("$1.5B") == 1_500_000_000
