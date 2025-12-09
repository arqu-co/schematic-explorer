# Schematic Explorer - Agent Instructions

This document provides AI agents with the information needed to use the schematic-explorer library effectively.

## Overview

schematic-explorer extracts structured carrier participation data from insurance tower schematic Excel files. It parses complex Excel layouts to identify carriers, their participation percentages, premiums, and layer information.

## Installation

```bash
pip install schematic-explorer
```

## Core Functions

### 1. `extract_schematic(filepath, sheet_name=None) -> list[dict]`

Extract carrier entries from an Excel tower schematic.

**Parameters:**
- `filepath` (str): Path to the Excel file
- `sheet_name` (str, optional): Specific sheet name. Defaults to active sheet.

**Returns:** List of dictionaries, each containing:
- `carrier` (str): Carrier name
- `layer_limit` (str): Layer limit (e.g., "$50M")
- `layer_description` (str): Layer description text
- `participation_pct` (float): Participation percentage (0.0-1.0)
- `premium` (float): Premium amount
- `premium_share` (float): Premium share percentage
- `terms` (str): Terms/conditions text
- `policy_number` (str): Policy number if found
- `excel_range` (str): Source cell reference (e.g., "B5:D8")
- `col_span` (int): Number of columns the cell spans
- `row_span` (int): Number of rows the cell spans
- `fill_color` (str): Cell background color (hex)
- `attachment_point` (str): Attachment point if found

**Example:**
```python
from schematic_explorer import extract_schematic

entries = extract_schematic("tower.xlsx")
for entry in entries:
    print(f"{entry['carrier']}: {entry['participation_pct']:.1%} - ${entry['premium']:,.0f}")
```

### 2. `extract_schematic_with_summaries(filepath, sheet_name=None) -> tuple[list[dict], list[dict]]`

Extract carrier entries along with layer-level summaries.

**Returns:** Tuple of (entries, layer_summaries)
- `entries`: Same as `extract_schematic()`
- `layer_summaries`: List of layer summary dictionaries with aggregate data

**Example:**
```python
from schematic_explorer import extract_schematic_with_summaries

entries, summaries = extract_schematic_with_summaries("tower.xlsx")
for summary in summaries:
    print(f"Layer {summary['layer_limit']}: ${summary['layer_bound_premium']:,.0f}")
```

### 3. `preflight(filepath, sheet_name=None) -> PreflightResult`

Analyze an Excel file before extraction to assess viability and confidence. Use this to determine if a file can be processed before attempting extraction.

**Returns:** `PreflightResult` with attributes:
- `can_extract` (bool): Whether extraction is likely to succeed
- `confidence` (float): Confidence score (0.0-1.0)
- `layers_found` (int): Number of layers detected
- `carriers_found` (int): Number of carriers detected
- `has_percentages` (bool): Whether participation percentages were found
- `has_currency` (bool): Whether premium values were found
- `has_terms` (bool): Whether terms text was found
- `issues` (list[str]): List of detected issues
- `suggestions` (list[str]): List of suggestions for improvement

**Example:**
```python
from schematic_explorer import preflight

result = preflight("tower.xlsx")
if result.can_extract:
    print(f"Ready to extract with {result.confidence:.0%} confidence")
    print(f"Found {result.layers_found} layers, {result.carriers_found} carriers")
else:
    print(f"Cannot extract: {result.issues}")
```

### 4. `verify_file(filepath, sheet_name=None) -> VerificationResult`

Extract and verify a file using AI-powered analysis (requires google-generativeai and GEMINI_API_KEY).

**Returns:** `VerificationResult` with attributes:
- `score` (float): Accuracy score (0.0-1.0)
- `summary` (str): Brief summary of verification
- `issues` (list[str]): List of issues found
- `suggestions` (list[str]): List of improvement suggestions
- `metadata` (dict): Parsing metadata (fallback_used, parsing_method)

**Example:**
```python
from schematic_explorer import verify_file

result = verify_file("tower.xlsx")
print(f"Accuracy: {result.score:.0%}")
if result.issues:
    print(f"Issues: {result.issues}")
```

### 5. `verify_extraction(filepath, entries, sheet_name=None) -> VerificationResult`

Verify already-extracted data against the source file.

**Example:**
```python
from schematic_explorer import extract_schematic, verify_extraction

entries = extract_schematic("tower.xlsx")
result = verify_extraction("tower.xlsx", entries)
```

## Recommended Workflow

1. **Always run preflight first** to check if extraction will succeed:
   ```python
   result = preflight(filepath)
   if not result.can_extract:
       return {"error": "Cannot extract", "issues": result.issues}
   ```

2. **Extract data** if preflight passes:
   ```python
   entries = extract_schematic(filepath)
   ```

3. **Optionally verify** for high-stakes applications:
   ```python
   verification = verify_file(filepath)
   if verification.score < 0.8:
       flag_for_manual_review()
   ```

## Error Handling

The library raises standard Python exceptions:
- `FileNotFoundError`: File doesn't exist
- `ValueError`: Invalid file format or sheet name
- `openpyxl.utils.exceptions.InvalidFileException`: Corrupted Excel file

**Recommended pattern:**
```python
from schematic_explorer import extract_schematic, preflight

def safe_extract(filepath: str) -> dict:
    try:
        check = preflight(filepath)
        if not check.can_extract:
            return {"success": False, "error": "Extraction not viable", "issues": check.issues}

        entries = extract_schematic(filepath)
        return {"success": True, "entries": entries, "confidence": check.confidence}
    except FileNotFoundError:
        return {"success": False, "error": "File not found"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}
```

## Environment Variables

For verification features:
- `GEMINI_API_KEY`: Required for verify_file() and verify_extraction()
- `GEMINI_MODEL_ID`: Optional, defaults to "gemini-2.5-flash"

## Type Exports

All types are available for import:
```python
from schematic_explorer import (
    CarrierEntry,      # Dataclass for carrier data
    LayerSummary,      # Dataclass for layer summaries
    VerificationResult,# Dataclass for verification results
    PreflightResult,   # Dataclass for preflight results
)
```

All dataclasses have a `.to_dict()` method for JSON serialization.

## Requirements

- Python 3.12+
- openpyxl >= 3.1.5
- pyyaml >= 6.0.3

Optional for verification:
- google-generativeai
- python-dotenv
- Pillow
