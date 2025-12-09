# Schematic Explorer

Extract insurance tower schematic data from Excel files.

## Installation

```bash
pip install schematic-explorer
```

## Usage

```python
from schematic_explorer import extract_schematic

# Extract carrier participation data from an Excel tower schematic
entries = extract_schematic("tower.xlsx")

for entry in entries:
    print(f"{entry['carrier']}: {entry['participation_pct']:.1%}")
```

## API

### `extract_schematic(filepath, sheet_name=None)`

Extract carrier entries from an Excel file.

**Parameters:**
- `filepath` (str): Path to the Excel file
- `sheet_name` (str, optional): Name of the sheet to extract from. Defaults to the active sheet.

**Returns:**
- `list[dict]`: List of carrier entry dictionaries with keys:
  - `carrier`: Carrier name
  - `participation_pct`: Participation percentage (0.0-1.0)
  - `layer`: Layer name/description
  - `limit`: Policy limit
  - `attachment`: Attachment point
  - `premium`: Premium amount (if available)
  - `source_ref`: Cell reference in the Excel file

### `extract_schematic_with_summaries(filepath, sheet_name=None)`

Extract carrier entries along with layer summaries.

**Returns:**
- Tuple of (entries, summaries) where summaries contains layer-level aggregations.

## License

MIT
