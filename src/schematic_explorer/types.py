"""Type definitions for insurance tower extraction."""

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

# =============================================================================
# Magnitude Constants
# =============================================================================

THOUSAND = 1_000
MILLION = 1_000_000
BILLION = 1_000_000_000

# =============================================================================
# Compiled Regex Patterns
# =============================================================================

# Patterns for parsing "xs." / "x/s" / "excess" notation
_EXCESS_PATTERN_DOLLAR = re.compile(
    r"(\$[\d,.]+[KMBkmb]?)\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*(\$[\d,.]+[KMBkmb]?)",
    re.IGNORECASE,
)
_EXCESS_PATTERN_NO_DOLLAR = re.compile(
    r"([\d,.]+[KMBkmb])\s*(?:xs\.?|x/s|excess(?:\s+of)?)\s*([\d,.]+[KMBkmb])",
    re.IGNORECASE,
)
_LIMIT_PATTERN = re.compile(r"(\$[\d,.]+[KMBkmb]?)")


# =============================================================================
# Carrier Detection Configuration
# =============================================================================


@dataclass(frozen=True)
class CarrierEntity:
    """A carrier with its canonical name and aliases.

    Used for alias resolution - multiple aliases map to one canonical name.
    Example: ACE, ACE American, Westchester all resolve to "Chubb".
    """

    canonical: str
    aliases: frozenset[str]

    @classmethod
    def from_dict(cls, data: dict) -> "CarrierEntity":
        """Create from YAML dict with 'canonical' and 'aliases' keys."""
        return cls(
            canonical=data["canonical"],
            aliases=frozenset(data.get("aliases", [data["canonical"]])),
        )


@dataclass(frozen=True)
class MatchRules:
    """Configuration for carrier matching behavior.

    Controls case sensitivity, punctuation handling, alias matching strategy,
    and context-aware gating for short/ambiguous carrier names.
    """

    case_insensitive: bool = True
    ignore_punctuation: bool = True
    longest_alias_wins: bool = True
    gate_short_aliases: bool = True
    short_alias_max_len: int = 5
    short_alias_keywords: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "carrier",
                "insurer",
                "market",
                "underwriter",
                "syndicate",
                "layer",
                "xs",
                "excess",
                "limit",
                "attachment",
                "premium",
                "share",
            }
        )
    )

    @classmethod
    def from_dict(cls, data: dict) -> "MatchRules":
        """Create from YAML match_rules section."""
        gate_config = data.get("gate_short_aliases", {})
        keywords = gate_config.get("require_any_nearby_keywords", [])

        # Build kwargs, only including short_alias_keywords if explicitly provided
        kwargs: dict = {
            "case_insensitive": data.get("case_insensitive", True),
            "ignore_punctuation": data.get("ignore_punctuation", True),
            "longest_alias_wins": data.get("longest_alias_wins", True),
            "gate_short_aliases": gate_config.get("enabled", True),
            "short_alias_max_len": gate_config.get("max_len", 5),
        }

        # Only override default keywords if explicitly provided
        if keywords:
            kwargs["short_alias_keywords"] = frozenset(kw.lower() for kw in keywords)

        return cls(**kwargs)


@dataclass(frozen=True)
class CarrierConfig:
    """Complete carrier detection configuration.

    Loaded from carriers.yml and used by CarrierMatcher.
    Includes pre-built lookup maps for O(1) matching performance.
    """

    match_rules: MatchRules
    legal_suffixes: frozenset[str]
    normalize_terms: Mapping[str, str]  # "ins" -> "insurance"
    entities: tuple[CarrierEntity, ...]
    structural_labels: frozenset[str]
    brokers_wholesalers: frozenset[str]
    # Pre-built lookup maps (built at load time)
    alias_to_canonical: Mapping[str, str]  # normalized alias -> canonical
    all_non_carriers: frozenset[str]

    @classmethod
    def from_dict(cls, data: dict) -> "CarrierConfig":
        """Create from full YAML config."""
        match_rules = MatchRules.from_dict(data.get("match_rules", {}))

        # Parse normalization config
        norm_config = data.get("normalization", {})
        legal_suffixes = frozenset(
            s.lower() for s in norm_config.get("legal_suffixes", [])
        )

        # Build normalize_terms from list of {from: [...], to: "..."} dicts
        normalize_terms: dict[str, str] = {}
        for term_mapping in norm_config.get("normalize_common_terms", []):
            to_val = term_mapping.get("to", "")
            for from_val in term_mapping.get("from", []):
                normalize_terms[from_val.lower()] = to_val.lower()

        # Parse carrier entities
        entities = tuple(
            CarrierEntity.from_dict(e) for e in data.get("carrier_entities", [])
        )

        # Parse non-carriers
        non_carriers_config = data.get("non_carriers", {})
        structural_labels = frozenset(
            s.lower() for s in non_carriers_config.get("structural_labels", [])
        )
        brokers_wholesalers = frozenset(
            s.lower() for s in non_carriers_config.get("brokers_wholesalers", [])
        )
        all_non_carriers = structural_labels | brokers_wholesalers

        # Build alias lookup map (normalized alias -> canonical)
        # Must apply same normalization as CarrierMatcher.normalize()
        alias_to_canonical: dict[str, str] = {}
        for entity in entities:
            for alias in entity.aliases:
                # Apply full normalization chain
                normalized = alias.lower() if match_rules.case_insensitive else alias

                # Strip legal suffixes
                for suffix in legal_suffixes:
                    pattern = rf"[\s,.]?{re.escape(suffix)}\.?$"
                    normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

                # Expand common terms (e.g., "ins" -> "insurance")
                for from_term, to_term in normalize_terms.items():
                    pattern = rf"\b{re.escape(from_term)}\b"
                    normalized = re.sub(pattern, to_term, normalized, flags=re.IGNORECASE)

                # Strip punctuation
                if match_rules.ignore_punctuation:
                    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

                normalized = normalized.strip()
                alias_to_canonical[normalized] = entity.canonical

        return cls(
            match_rules=match_rules,
            legal_suffixes=legal_suffixes,
            normalize_terms=normalize_terms,
            entities=entities,
            structural_labels=structural_labels,
            brokers_wholesalers=brokers_wholesalers,
            alias_to_canonical=alias_to_canonical,
            all_non_carriers=all_non_carriers,
        )


# =============================================================================
# Carrier Matching Context
# =============================================================================


@dataclass
class CarrierMatchContext:
    """Context for matching carrier blocks to related data.

    Groups related parameters used when building CarrierEntry objects,
    reducing the parameter count of proximity-matching functions.
    """

    layer: "Layer"  # The layer being processed
    data_blocks: list  # List of data blocks to search for matches
    column_headers: dict = None  # Dict mapping column types to column numbers
    row_labels: dict = None  # Dict mapping row types to row numbers

    def __post_init__(self):
        """Set default empty dicts if None provided."""
        if self.column_headers is None:
            self.column_headers = {}
        if self.row_labels is None:
            self.row_labels = {}


@dataclass(frozen=True)
class CurrencyMatchState:
    """Immutable state for currency matching during carrier entry building.

    Holds the current matched premium and premium_share values
    as we iterate through currency blocks. Being frozen (immutable)
    ensures thread-safety and clear state transitions.
    """

    premium: float | None = None
    premium_share: float | None = None

    def with_premium(self, value: float) -> "CurrencyMatchState":
        """Return new state with updated premium."""
        return CurrencyMatchState(premium=value, premium_share=self.premium_share)

    def with_premium_share(self, value: float) -> "CurrencyMatchState":
        """Return new state with updated premium_share."""
        return CurrencyMatchState(premium=self.premium, premium_share=value)

    @property
    def has_value(self) -> bool:
        """Check if any value has been matched."""
        return self.premium is not None or self.premium_share is not None

    def as_tuple(self) -> tuple[float | None, float | None]:
        """Return values as tuple for backward compatibility."""
        return (self.premium, self.premium_share)


@dataclass
class SummaryColumnInfo:
    """Information about summary/aggregate columns detected in a worksheet.

    Summary columns contain layer-level totals rather than per-carrier data.
    They are excluded from carrier extraction but used for cross-checking.
    """

    columns: set[int]  # Set of column numbers to exclude from carrier extraction
    bound_premium_col: int | None = None  # Column with Layer Bound Premiums
    layer_target_col: int | None = None  # Column with Layer Target
    layer_rate_col: int | None = None  # Column with Layer Rate

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Layer:
    """Represents a layer boundary in an insurance tower.

    Layers are identified by their limit values and define row ranges
    in the spreadsheet that contain carrier participation data.
    """

    limit: str  # Formatted limit (e.g., "$50M")
    limit_row: int  # Row where the limit was found
    limit_col: int  # Column where the limit was found
    start_row: int  # First row of layer data
    end_row: int  # Last row of layer data

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CarrierEntry:
    """Represents a single carrier's participation in a layer.

    The carrier field contains the original text from the spreadsheet,
    while canonical_carrier contains the resolved canonical name if available.
    """

    layer_limit: str
    layer_description: str
    carrier: str  # Original text from spreadsheet (e.g., "ACE American")
    participation_pct: float | None
    premium: float | None
    premium_share: float | None
    terms: str | None
    policy_number: str | None
    excel_range: str
    col_span: int
    row_span: int
    fill_color: str | None = None
    attachment_point: str | None = None
    canonical_carrier: str | None = None  # Resolved canonical name (e.g., "Chubb")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LayerSummary:
    """Layer-level aggregate data extracted from summary columns.

    Used for cross-checking: the sum of carrier premiums
    in a layer should match the layer_bound_premium.
    """

    layer_limit: str
    layer_target: float | None = None
    layer_rate: float | None = None
    layer_bound_premium: float | None = None
    excel_range: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class VerificationError(Exception):
    """Raised when verification parsing fails after all retry attempts."""

    pass


@dataclass
class VerificationResult:
    """Result of verification check."""

    score: float  # 0.0 to 1.0
    summary: str
    issues: list[str]
    suggestions: list[str]
    raw_response: str
    metadata: dict | None = None  # Additional info (e.g., fallback_used, parsing_method)


def parse_limit_value(val: int | float | str | None) -> str | None:
    """Parse various limit formats into standardized string."""
    if val is None:
        return None

    if isinstance(val, int | float):
        if val >= MILLION:
            return f"${int(val / MILLION)}M"
        elif val >= THOUSAND:
            return f"${int(val / THOUSAND)}K"
        return f"${int(val)}"

    if isinstance(val, str):
        if val.startswith("$"):
            return val
        cleaned = val.replace(",", "").replace("$", "")
        try:
            num = float(cleaned)
            return parse_limit_value(num)
        except ValueError:
            return val

    return None


def parse_excess_notation(text: str | None) -> tuple[str | None, str | None]:
    """Parse 'xs.' or 'x/s' or 'excess' notation from policy description.

    Examples:
        "Umbrella $50M xs. $50M" -> (limit="$50M", attachment="$50M")
        "$25M x/s $25M" -> (limit="$25M", attachment="$25M")

    Returns:
        Tuple of (limit, attachment_point) - either may be None
    """
    if not text or not isinstance(text, str):
        return None, None

    # Try dollar-prefixed pattern first
    match = _EXCESS_PATTERN_DOLLAR.search(text)
    if match:
        return match.group(1).upper(), match.group(2).upper()

    # Try non-dollar pattern (adds $ prefix to results)
    match = _EXCESS_PATTERN_NO_DOLLAR.search(text)
    if match:
        limit = "$" + match.group(1)
        attachment = "$" + match.group(2)
        return limit.upper(), attachment.upper()

    # Fall back to extracting just a limit
    match = _LIMIT_PATTERN.search(text)
    if match:
        return match.group(1).upper(), None

    return None, None


def parse_limit_for_sort(limit_str: str | None) -> float:
    """Parse limit string to numeric value for sorting."""
    if not limit_str:
        return 0
    cleaned = limit_str.replace("$", "").replace(",", "").upper()
    multiplier = 1
    if cleaned.endswith("M"):
        multiplier = MILLION
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = THOUSAND
        cleaned = cleaned[:-1]
    elif cleaned.endswith("B"):
        multiplier = BILLION
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return 0
