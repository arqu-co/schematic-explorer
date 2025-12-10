"""Verification prompts and schemas for Gemini API."""

# Schema for structured output (Gemini-compatible format)
VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number", "description": "Accuracy score from 0.0 to 1.0"},
        "summary": {
            "type": "string",
            "description": "Brief 1-2 sentence summary of extraction quality",
        },
        "issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific issues found",
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of improvement suggestions",
        },
    },
    "required": ["score", "summary", "issues", "suggestions"],
}

SNAPSHOT_VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "number",
            "description": "Accuracy score from 0.0 to 1.0 based on visual comparison",
        },
        "summary": {"type": "string", "description": "Brief assessment based on visual comparison"},
        "visual_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Discrepancies between image and extracted data",
        },
        "missing_from_extraction": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Data visible in image but not in extraction",
        },
        "false_positives": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Data in extraction that doesn't appear in image",
        },
    },
    "required": ["score", "summary", "visual_issues", "missing_from_extraction", "false_positives"],
}

# Schema for cross-validation pass
CROSS_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "adjusted_score": {
            "type": "number",
            "description": "Revised accuracy score from 0.0 to 1.0 after reviewing issues",
        },
        "summary": {
            "type": "string",
            "description": "Brief summary of the cross-validation findings",
        },
        "confirmed_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Issues from the first pass that are confirmed as real problems",
        },
        "dismissed_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Issues from the first pass that were false positives (with brief reason)",
        },
        "new_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Any additional issues discovered during cross-validation",
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Refined suggestions for improving extraction",
        },
    },
    "required": [
        "adjusted_score",
        "summary",
        "confirmed_issues",
        "dismissed_issues",
        "new_issues",
        "suggestions",
    ],
}

VERIFICATION_PROMPT = """Compare extracted insurance data against Excel source.

## Excel Data
{excel_content}

## Extracted Data
{extracted_content}

## CRITICAL: Cell Reference Verification
Each extracted entry has a cell reference like [cell:H47].
ALWAYS verify by checking the SAME COLUMN in Excel data.
Do NOT compare values from different columns or different layers.

## VALUE EQUIVALENCE - DO NOT FLAG THESE AS ISSUES:
- Percentages: 0.1 = 10% = 0.10 = 0.1000
- Currency: 100000.0 = 100000 = $100,000 = $100,000.0
- Decimals: 3500000.0 = 3500000 = $3,500,000

## LAYER ISOLATION
Same carrier name may appear in multiple layers with DIFFERENT values.
Only compare within the SAME layer. Different layers = different entries.

## HIDDEN ROWS
Hidden rows contain grouping metadata. Carriers in hidden rows have no participation.

## ONLY REPORT GENUINE ISSUES:
- Mathematically different values (0.1 vs 0.2)
- Missing data that should exist
- Wrong carrier-layer assignments

Score: 0.0 to 1.0"""


VERIFICATION_PROMPT_TEXT_ONLY = """Compare extracted insurance data against Excel source.

## Excel Data
{excel_content}

## Extracted Data
{extracted_content}

## CRITICAL: Cell Reference Verification
Each extracted entry has a cell reference like [cell:H47].
ALWAYS verify by checking the SAME COLUMN in Excel data.
Do NOT compare values from different columns or different layers.

## VALUE EQUIVALENCE - DO NOT FLAG THESE AS ISSUES:
- Percentages: 0.1 = 10% = 0.10 = 0.1000
- Currency: 100000.0 = 100000 = $100,000 = $100,000.0
- Decimals: 3500000.0 = 3500000 = $3,500,000

## LAYER ISOLATION
Same carrier name may appear in multiple layers with DIFFERENT values.
Only compare within the SAME layer. Different layers = different entries.

## HIDDEN ROWS
Hidden rows contain grouping metadata. Carriers in hidden rows have no participation.

## ONLY REPORT GENUINE ISSUES:
- Mathematically different values (0.1 vs 0.2)
- Missing data that should exist
- Wrong carrier-layer assignments

Score: 0.0 to 1.0"""


SNAPSHOT_VERIFICATION_PROMPT = """You are verifying extracted insurance tower data against this Excel spreadsheet image.

## Extracted Data
{extracted_content}

## IMPORTANT RULES

### Rule 1: Decimal = Percentage (NEVER flag as error)
- 0.1 = 10%, 0.5 = 50%, 0.25 = 25%
- If extraction shows "50%" and image shows "0.5" → CORRECT
- If extraction shows "10.0%" and image shows "0.1" → CORRECT

### Rule 2: Only flag ACTUAL differences
- 10% vs 20% → ERROR (different numbers)
- 10% vs 0.1 → NOT AN ERROR (same number)

### Rule 3: Don't flag identical values
If extraction matches Excel exactly, it's NOT an issue.

## Your Task
Look at the image and verify the extracted data. Only report genuine discrepancies where values are mathematically different or data is missing/wrong.

Score: 0.0 (completely wrong) to 1.0 (perfect)"""


CROSS_VALIDATION_PROMPT = """Second-pass cross-validation of extracted insurance data.

## Excel Data
{excel_content}

## Extracted Data
{extracted_content}

## First-Pass Findings
Score: {initial_score:.0%}
Summary: {initial_summary}

Issues identified:
{issues_list}

## CRITICAL VERIFICATION RULES

### Rule 1: Cell Reference Matching (MOST IMPORTANT)
Each extracted entry includes a cell reference like [cell:H47].
To verify a carrier's participation:
1. Find the carrier's cell reference (e.g., H47)
2. Look at the SAME COLUMN in the % SHARE row (e.g., H48)
3. Compare ONLY that specific cell's value
4. Do NOT compare to values in different columns (J48, K48, etc.)

### Rule 2: Layer Isolation
Insurance towers have multiple layers ($250M, $150M, $100M, $50M, $25M).
- The SAME carrier may appear in MULTIPLE layers with DIFFERENT values
- "Lexington" in $25M layer (H47/H48) is DIFFERENT from "Lexington" in $250M layer (J7/J8)
- ONLY compare values within the SAME layer
- DISMISS any issue comparing a carrier across different layers

### Rule 3: Hidden Rows
Hidden rows (often rows 60+) contain grouping metadata, not carrier data.
- Carriers in hidden rows should have NULL/N/A participation
- DISMISS any issue about hidden row carriers having wrong values

### Rule 4: Value Equivalence - ALWAYS DISMISS
- 0.1 = 10% = 0.10 = 0.1000 (ALL EQUIVALENT)
- 0.225 = 22.5% = 0.2250 (ALL EQUIVALENT)
- 100000 = 100000.0 (EQUIVALENT)
- DISMISS any issue comparing equivalent values

### Rule 5: Column Alignment Check
If an issue claims "carrier X has 0.2 but Excel shows 0.09":
1. Find carrier X's cell reference in extracted data
2. Verify the "Excel shows" value comes from the SAME column
3. If comparing different columns, DISMISS the issue

## VERIFICATION PROTOCOL
For EACH issue:
1. Identify the carrier and its cell reference [cell:XX]
2. Find that exact cell's participation (same column, % SHARE row)
3. Compare: extracted value vs that specific cell
4. DISMISS if: values match, different columns, different layers, or equivalent formats

Be AGGRESSIVE about dismissing false positives. When in doubt, DISMISS."""
