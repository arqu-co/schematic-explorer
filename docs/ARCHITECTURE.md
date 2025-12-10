# Schematic Explorer Architecture

## Overview

Schematic Explorer extracts structured carrier participation data from insurance tower diagrams in Excel spreadsheets using adaptive pattern recognition and AI-powered verification.

## System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Schematic Explorer                                │
├──────────────────────────────────┬──────────────────────────────────────────┤
│         Python Backend           │          React Frontend (viewer/)        │
├──────────────────────────────────┼──────────────────────────────────────────┤
│  ┌─────────────────────────┐     │     ┌─────────────────────────────────┐  │
│  │     extract_tower.py    │     │     │            App.tsx              │  │
│  │         (CLI)           │     │     │    (Main application shell)     │  │
│  └───────────┬─────────────┘     │     └───────────────┬─────────────────┘  │
│              │                   │                     │                    │
│  ┌───────────▼─────────────┐     │     ┌───────────────▼─────────────────┐  │
│  │  schematic_explorer/    │     │     │         components/             │  │
│  │      __init__.py        │     │     │  FileList, MainContent,         │  │
│  │   (Public API facade)   │     │     │  InsightsSidebar, Icons         │  │
│  └───────────┬─────────────┘     │     └───────────────┬─────────────────┘  │
│              │                   │                     │                    │
│      ┌───────┴────────┐          │            ┌────────┴────────┐           │
│      ▼                ▼          │            ▼                 ▼           │
│  ┌────────┐      ┌─────────┐     │     ┌──────────┐       ┌──────────┐      │
│  │extract │      │ verify/ │     │     │  hooks/  │       │  utils   │      │
│  │  or.py │      │ package │     │     │ useFiles │       │ api.ts   │      │
│  └────┬───┘      └────┬────┘     │     │ useTheme │       │ types.ts │      │
│       │               │          │     └──────────┘       └──────────┘      │
│       ▼               ▼          │                                          │
│  ┌─────────────────────────┐     │                                          │
│  │    Supporting Modules   │     │                                          │
│  │  blocks, carriers,      │     │                                          │
│  │  proximity, types,      │     │                                          │
│  │  preflight, scoring     │     │                                          │
│  └─────────────────────────┘     │                                          │
└──────────────────────────────────┴──────────────────────────────────────────┘
```

## Python Module Hierarchy

### Entry Points

| Module | Purpose |
|--------|---------|
| `extract_tower.py` | CLI for batch extraction |
| `schematic_explorer/__init__.py` | Public API facade |

### Core Extraction (`schematic_explorer/`)

```
schematic_explorer/
├── __init__.py         # Public API: extract_schematic, verify_file, etc.
├── extractor.py        # Main extraction logic - finds blocks, layers, carriers
├── blocks.py           # Block classification (carrier, limit, currency, etc.)
├── carriers.py         # Carrier name detection and validation
├── proximity.py        # Spatial relationship calculations
├── types.py            # Data classes: CarrierEntry, LayerSummary, etc.
├── preflight.py        # Pre-extraction validation
├── scoring.py          # Score calculation utilities
├── utils.py            # Excel helpers: merged cells, cell values, colors
└── verify/             # AI-powered verification package
    ├── __init__.py     # Public API re-exports
    ├── core.py         # Main verification functions
    ├── gemini.py       # Gemini API client
    ├── formatting.py   # Excel to text conversion
    ├── layer_check.py  # Layer total cross-checking
    └── prompts.py      # Verification prompts and schemas
```

### Module Dependencies

```
extractor.py
    ├── blocks.py         (classify_blocks)
    ├── carriers.py       (_is_non_carrier, _looks_like_policy_number)
    ├── proximity.py      (spatial matching, summary detection)
    ├── types.py          (CarrierEntry, Layer, etc.)
    └── utils.py          (Excel cell helpers)

verify/core.py
    ├── verify/gemini.py      (LLM requests)
    ├── verify/formatting.py  (text conversion)
    ├── verify/layer_check.py (validation)
    ├── verify/prompts.py     (prompt templates)
    └── types.py              (VerificationResult)

preflight.py
    ├── blocks.py     (block classification)
    ├── scoring.py    (score calculation)
    └── utils.py      (Excel helpers)
```

## Data Flow

### Extraction Pipeline

```
Excel File (.xlsx)
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Block Discovery (extractor._find_all_blocks)                │
│     - Scan merged cell regions                                  │
│     - Identify significant single cells                         │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Block Classification (blocks.classify_blocks)               │
│     - Infer block types: carrier, limit, currency, percentage   │
│     - Use pattern matching and heuristics                       │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Summary Column Detection (proximity.detect_summary_columns) │
│     - Find aggregate columns to exclude from carrier data       │
│     - Identify layer rate, bound premium columns                │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Layer Identification (extractor._identify_layers)           │
│     - Find layer limit values ($50M, $100M, etc.)              │
│     - Determine layer row ranges                                │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Carrier Extraction (extractor._extract_layer_data)          │
│     - Match carrier blocks to layers by proximity               │
│     - Extract participation %, premium, terms                   │
│     - Build CarrierEntry objects                                │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
List[CarrierEntry] + List[LayerSummary]
```

### Verification Pipeline

```
CarrierEntry[] + Excel File
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Format to Text (formatting.excel_to_text, entries_to_text)  │
│     - Convert Excel region to readable text                     │
│     - Format extracted entries as text                          │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Gemini Verification (gemini.make_gemini_request)            │
│     - Send prompt with Excel text + extracted data              │
│     - Parse structured JSON response                            │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Cross-Validation (core.cross_validate)                      │
│     - Filter false positives using LLM                          │
│     - Validate carrier names exist in source                    │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Layer Total Check (layer_check.cross_check_layer_totals)    │
│     - Sum carrier participations per layer                      │
│     - Verify totals against layer summaries                     │
│     - Flag missing carriers or discrepancies                    │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
VerificationResult (score, issues, suggestions)
```

## React Frontend Architecture

### Component Hierarchy

```
App
├── useFiles()           # Fetches and manages schematic files
├── useTheme()           # Light/dark theme toggle
│
├── FileList             # Left sidebar - file selection
│   └── SchematicCard    # Individual file card
│
├── MainContent          # Center - tabbed content views
│   ├── TowerVisualization   # Visual tower diagram
│   ├── CarrierTable         # Tabular data view
│   ├── ExcelViewer          # Original Excel preview
│   └── JSON View            # Raw JSON display
│
└── InsightsSidebar      # Right sidebar - AI insights
    └── InsightsPanel    # Markdown-rendered insights
```

### Data Types

```typescript
// Core data model (matches Python CarrierEntry)
interface CarrierEntry {
  layer_limit: string;       // "$50M"
  carrier: string;           // "Carrier Name"
  participation_pct: number | null;  // 0.25 = 25%
  premium: number | null;    // Dollar amount
  excel_range: string;       // "B5:D7"
  fill_color: string | null; // Excel background color
  // ... additional fields
}

// Grouped for display
interface Layer {
  limit: string;
  entries: CarrierEntry[];
  totalPremium: number;
}

// File metadata
interface SchematicFile {
  name: string;              // "tower.json"
  stem: string;              // "tower"
  entries: CarrierEntry[];
  insights: string | null;   // AI verification markdown
}
```

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/files` | List available JSON files |
| `GET /api/data/{name}` | Get extracted carrier data |
| `GET /api/data/{stem}_insights.txt` | Get AI verification insights |
| `GET /api/input/{stem}.xlsx` | Get original Excel file |

## Key Design Decisions

### 1. Adaptive Pattern Recognition

The extractor makes **no assumptions** about specific labels or column positions. Instead:
- Merged cells define visual blocks
- Spatial proximity determines relationships
- Content patterns infer field types

This allows handling diverse tower diagram formats without format-specific code.

### 2. Immutable Data Classes

All data structures use frozen dataclasses:
```python
@dataclass(frozen=True)
class CarrierEntry:
    ...
```

Benefits:
- Thread safety
- Predictable state
- Hashable for collections

### 3. Lazy LLM Loading

The verification module uses lazy imports to avoid requiring `google-generativeai` for basic extraction:
```python
def verify_file(filepath: str, ...) -> VerificationResult:
    from .verify import verify_file as _verify_file
    return _verify_file(filepath, ...)
```

### 4. Module Separation by Responsibility

The `verify/` package splits by concern:
- `core.py` - Business logic orchestration
- `gemini.py` - External API integration
- `formatting.py` - Data transformation
- `layer_check.py` - Validation rules
- `prompts.py` - LLM prompt templates

### 5. Frontend Component Composition

React components are small, focused, and composable:
- Custom hooks (`useFiles`, `useTheme`) manage state
- Components receive data via props
- Index files provide clean exports

### 6. Type Safety Throughout

- Python: Type hints with mypy strict mode
- TypeScript: Strict mode with explicit interfaces
- Runtime: Pydantic/dataclass validation

## Testing Strategy

### Python Tests (`tests/`)

- Unit tests for each module
- Real openpyxl workbooks (no mocking internal code)
- Fixtures for common test data
- pytest-based with parametrized tests

### TypeScript Tests (`viewer/src/**/*.test.tsx`)

- Vitest + React Testing Library
- Component render tests
- User interaction tests
- Factory functions for type-safe test data

## File Conventions

| Pattern | Purpose |
|---------|---------|
| `*.py` | Python source |
| `*_test.py`, `test_*.py` | Python tests |
| `*.tsx` | React components |
| `*.test.tsx` | Component tests |
| `types.py`, `types.ts` | Type definitions |
| `utils.py`, `utils.ts` | Shared utilities |
| `__init__.py`, `index.ts` | Public exports |
