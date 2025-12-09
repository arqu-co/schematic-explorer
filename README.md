# Schematic Explorer

[![CI](https://github.com/arqu-co/schematic-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/arqu-co/schematic-explorer/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Extract structured carrier participation data from insurance tower schematic Excel files.

## Features

- **Extract carrier data** from Excel tower schematics (layer limits, participation %, premiums)
- **Preflight analysis** to assess extraction viability before processing
- **AI-powered verification** using Google Gemini to validate extraction accuracy
- **CLI tools** for batch processing and verification

## Installation

```bash
pip install schematic-explorer
```

For development:

```bash
git clone https://github.com/arqu-co/schematic-explorer.git
cd schematic-explorer
pip install -e ".[dev]"
```

## Quick Start

```python
from schematic_explorer import extract_schematic

# Extract carrier data from an Excel tower schematic
entries = extract_schematic("tower.xlsx")

for entry in entries:
    print(f"{entry['carrier']}: {entry['participation_pct']:.1%} - ${entry['premium']:,.0f}")
```

## API Reference

### Extraction

#### `extract_schematic(filepath, sheet_name=None) -> list[dict]`

Extract carrier entries from an Excel file.

```python
from schematic_explorer import extract_schematic

entries = extract_schematic("tower.xlsx")
# Returns list of dicts with carrier data
```

**Returns** a list of dictionaries with:
- `carrier` - Carrier name
- `layer_limit` - Layer limit (e.g., "$50M")
- `layer_description` - Layer description text
- `participation_pct` - Participation percentage (0.0-1.0)
- `premium` - Premium amount
- `premium_share` - Premium share percentage
- `terms` - Terms/conditions text
- `policy_number` - Policy number if found
- `excel_range` - Source cell reference
- `col_span`, `row_span` - Cell dimensions
- `fill_color` - Cell background color
- `attachment_point` - Attachment point if found

#### `extract_schematic_with_summaries(filepath, sheet_name=None) -> tuple[list[dict], list[dict]]`

Extract carrier entries along with layer-level summaries.

```python
from schematic_explorer import extract_schematic_with_summaries

entries, layer_summaries = extract_schematic_with_summaries("tower.xlsx")

for summary in layer_summaries:
    print(f"Layer {summary['layer_limit']}: ${summary['layer_bound_premium']:,.0f}")
```

### Preflight Check

#### `preflight(filepath, sheet_name=None) -> PreflightResult`

Analyze an Excel file before extraction to assess viability and confidence.

```python
from schematic_explorer import preflight

result = preflight("tower.xlsx")

if result.can_extract:
    print(f"Ready to extract with {result.confidence:.0%} confidence")
    print(f"Found {result.layers_found} layers, {result.carriers_found} carriers")
else:
    print("Issues detected:")
    for issue in result.issues:
        print(f"  - {issue}")
```

**PreflightResult attributes:**
- `can_extract` - Whether extraction is likely to succeed
- `confidence` - Confidence score (0.0-1.0)
- `layers_found` - Number of layers detected
- `carriers_found` - Number of carriers detected
- `has_percentages` - Whether participation % were found
- `has_currency` - Whether premium values were found
- `has_terms` - Whether terms text was found
- `issues` - List of detected issues
- `suggestions` - List of suggestions

### Verification (Optional)

Requires `google-generativeai` and a Gemini API key.

#### `verify_file(filepath, sheet_name=None) -> VerificationResult`

Extract and verify a file using AI-powered analysis.

```python
from schematic_explorer import verify_file

result = verify_file("tower.xlsx")

print(f"Accuracy: {result.score:.0%}")
print(f"Summary: {result.summary}")

if result.issues:
    print("Issues found:")
    for issue in result.issues:
        print(f"  - {issue}")
```

#### `verify_extraction(filepath, entries, sheet_name=None) -> VerificationResult`

Verify already-extracted data against the source file.

```python
from schematic_explorer import extract_schematic, verify_extraction

entries = extract_schematic("tower.xlsx")
result = verify_extraction("tower.xlsx", entries)
```

**VerificationResult attributes:**
- `score` - Accuracy score (0.0-1.0)
- `summary` - Brief summary of verification
- `issues` - List of issues found
- `suggestions` - List of improvement suggestions
- `metadata` - Parsing metadata (fallback_used, parsing_method)

## Integration Examples

### Flask/FastAPI Web Service

```python
from flask import Flask, request, jsonify
from schematic_explorer import extract_schematic, preflight

app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def extract():
    file = request.files["file"]
    filepath = f"/tmp/{file.filename}"
    file.save(filepath)

    # Check viability first
    check = preflight(filepath)
    if not check.can_extract:
        return jsonify({"error": "Cannot extract", "issues": check.issues}), 400

    # Extract data
    entries = extract_schematic(filepath)
    return jsonify({"entries": entries, "confidence": check.confidence})
```

### Django Integration

```python
# views.py
from django.http import JsonResponse
from schematic_explorer import extract_schematic, preflight

def extract_tower(request):
    uploaded_file = request.FILES["file"]

    # Save temporarily
    with open(f"/tmp/{uploaded_file.name}", "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    filepath = f"/tmp/{uploaded_file.name}"

    # Preflight check
    result = preflight(filepath)
    if not result.can_extract:
        return JsonResponse({"success": False, "issues": result.issues})

    # Extract
    entries = extract_schematic(filepath)
    return JsonResponse({
        "success": True,
        "entries": entries,
        "layers_found": result.layers_found,
        "carriers_found": result.carriers_found,
    })
```

### Batch Processing Script

```python
from pathlib import Path
from schematic_explorer import extract_schematic_with_summaries, preflight
import json

def process_directory(input_dir: str, output_dir: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for xlsx_file in input_path.glob("*.xlsx"):
        if xlsx_file.name.startswith("~$"):  # Skip temp files
            continue

        print(f"Processing {xlsx_file.name}...")

        # Preflight check
        check = preflight(str(xlsx_file))
        if not check.can_extract:
            print(f"  Skipping: {check.issues}")
            continue

        # Extract
        entries, summaries = extract_schematic_with_summaries(str(xlsx_file))

        # Save JSON output
        output_file = output_path / f"{xlsx_file.stem}.json"
        output_file.write_text(json.dumps({
            "entries": entries,
            "summaries": [s.to_dict() for s in summaries],
        }, indent=2))

        print(f"  Extracted {len(entries)} entries -> {output_file.name}")

if __name__ == "__main__":
    process_directory("./input", "./output")
```

### With Pandas

```python
import pandas as pd
from schematic_explorer import extract_schematic

entries = extract_schematic("tower.xlsx")

# Convert to DataFrame
df = pd.DataFrame(entries)

# Analyze by layer
layer_summary = df.groupby("layer_limit").agg({
    "carrier": "count",
    "participation_pct": "sum",
    "premium": "sum"
}).rename(columns={"carrier": "num_carriers"})

print(layer_summary)
```

### Async Processing

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor
from schematic_explorer import extract_schematic

async def extract_async(filepath: str):
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as pool:
        return await loop.run_in_executor(pool, extract_schematic, filepath)

async def process_files(filepaths: list[str]):
    tasks = [extract_async(fp) for fp in filepaths]
    return await asyncio.gather(*tasks)

# Usage
results = asyncio.run(process_files(["tower1.xlsx", "tower2.xlsx"]))
```

## CLI Tools

The package includes CLI tools for development and batch processing:

```bash
# Process files
bin/process all              # Process all files in input/
bin/process random           # Process a random file
bin/process tower.xlsx       # Process a specific file
bin/process all --verify     # Process and verify

# Verify extractions
bin/verify all               # Verify all files
bin/verify tower.xlsx        # Verify a specific file
bin/verify --verbose         # Show detailed metadata

# Preflight check
bin/preflight tower.xlsx     # Check extraction viability
```

## Environment Variables

For verification features:

```bash
export GEMINI_API_KEY="your-api-key"
export GEMINI_MODEL_ID="gemini-2.5-flash"  # Optional, defaults to gemini-2.5-flash
```

## Type Definitions

```python
from schematic_explorer import CarrierEntry, LayerSummary, VerificationResult, PreflightResult

# All types are dataclasses with .to_dict() methods
entry = CarrierEntry(...)
data = entry.to_dict()
```

## Requirements

- Python 3.12+
- openpyxl >= 3.1.5
- pyyaml >= 6.0.3

Optional for verification:
- google-generativeai
- python-dotenv
- Pillow

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=schematic_explorer --cov-report=term-missing

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## License

MIT
