"""Core verification functions for insurance tower data."""

import json
from pathlib import Path

from PIL import Image

from ..types import CarrierEntry, VerificationResult
from .formatting import entries_to_text, excel_to_text
from .gemini import GENERATION_TEMPERATURE, get_client, make_gemini_request
from .prompts import (
    CROSS_VALIDATION_PROMPT,
    CROSS_VALIDATION_SCHEMA,
    SNAPSHOT_VERIFICATION_PROMPT,
    SNAPSHOT_VERIFICATION_SCHEMA,
    VERIFICATION_PROMPT,
    VERIFICATION_PROMPT_TEXT_ONLY,
    VERIFICATION_SCHEMA,
)

# Output directory for snapshots
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent.parent / "output"


def get_snapshot_path(filepath: str) -> Path | None:
    """Get the snapshot image path for an Excel file."""
    excel_path = Path(filepath)
    snapshot_path = OUTPUT_DIR / f"{excel_path.stem}.png"
    if snapshot_path.exists():
        return snapshot_path
    return None


def create_error_result(error: Exception, context: str) -> VerificationResult:
    """Create a standardized error VerificationResult.

    Args:
        error: The exception that occurred
        context: Description of the operation that failed (e.g., "Verification", "Snapshot verification")

    Returns:
        VerificationResult with error information
    """
    error_str = str(error)
    return VerificationResult(
        score=0.0,
        summary=f"{context} failed: {error_str}",
        issues=[error_str],
        suggestions=[],
        raw_response=error_str,
        metadata={"parsing_method": "error", "fallback_used": True, "error": error_str},
    )


def convert_snapshot_issues(data: dict) -> list[str]:
    """Convert snapshot-specific fields to standard issue format."""
    issues = list(data.get("visual_issues", []))
    issues.extend([f"Missing: {m}" for m in data.get("missing_from_extraction", [])])
    issues.extend([f"False positive: {f}" for f in data.get("false_positives", [])])
    return issues


def verify_extraction(
    filepath: str, entries: list[CarrierEntry], sheet_name: str | None = None
) -> VerificationResult:
    """
    Verify extracted data against original Excel using Gemini with structured output.

    Args:
        filepath: Path to the original Excel file
        entries: Extracted CarrierEntry objects
        sheet_name: Optional sheet name

    Returns:
        VerificationResult with score and details
    """
    model = get_client()

    excel_content = excel_to_text(filepath, sheet_name)
    extracted_content = entries_to_text(entries)

    # Check if we have a snapshot image
    snapshot_path = get_snapshot_path(filepath)

    # Build prompt based on whether we have an image
    if snapshot_path:
        prompt = VERIFICATION_PROMPT.format(
            excel_content=excel_content, extracted_content=extracted_content
        )
        image = Image.open(snapshot_path)
    else:
        prompt = VERIFICATION_PROMPT_TEXT_ONLY.format(
            excel_content=excel_content, extracted_content=extracted_content
        )
        image = None

    try:
        data, raw_response, metadata = make_gemini_request(
            model, prompt, VERIFICATION_SCHEMA, image, "verify_extraction"
        )
        return VerificationResult(
            score=float(data.get("score", 0)),
            summary=data.get("summary", "No summary"),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            raw_response=raw_response,
            metadata=metadata,
        )
    except Exception as e:
        return create_error_result(e, "Verification")


def verify_snapshot(
    filepath: str,
    entries: list[CarrierEntry],
) -> VerificationResult | None:
    """
    Verify extracted data against the visual snapshot only using structured output.

    Args:
        filepath: Path to the original Excel file
        entries: Extracted CarrierEntry objects

    Returns:
        VerificationResult or None if no snapshot available
    """
    snapshot_path = get_snapshot_path(filepath)
    if not snapshot_path:
        return None

    model = get_client()
    extracted_content = entries_to_text(entries)
    prompt = SNAPSHOT_VERIFICATION_PROMPT.format(extracted_content=extracted_content)
    image = Image.open(snapshot_path)

    try:
        data, raw_response, metadata = make_gemini_request(
            model, prompt, SNAPSHOT_VERIFICATION_SCHEMA, image, "verify_snapshot"
        )
        issues = convert_snapshot_issues(data)
        return VerificationResult(
            score=float(data.get("score", 0)),
            summary=data.get("summary", "Visual verification complete"),
            issues=issues,
            suggestions=[],
            raw_response=raw_response,
            metadata=metadata,
        )
    except Exception as e:
        return create_error_result(e, "Snapshot verification")


def cross_validate(
    filepath: str,
    entries: list[CarrierEntry],
    initial_result: VerificationResult,
    sheet_name: str | None = None,
) -> VerificationResult:
    """
    Cross-validate the first-pass verification to filter false positives.

    Args:
        filepath: Path to the original Excel file
        entries: Extracted CarrierEntry objects
        initial_result: Result from first verification pass
        sheet_name: Optional sheet name

    Returns:
        VerificationResult with refined findings
    """
    snapshot_path = get_snapshot_path(filepath)
    if not snapshot_path:
        # No snapshot available, return initial result as-is
        return initial_result

    model = get_client()
    excel_content = excel_to_text(filepath, sheet_name)
    extracted_content = entries_to_text(entries)

    # Format issues for the prompt
    issues_list = (
        "\n".join(f"- {issue}" for issue in initial_result.issues)
        if initial_result.issues
        else "None identified"
    )

    prompt = CROSS_VALIDATION_PROMPT.format(
        excel_content=excel_content,
        extracted_content=extracted_content,
        initial_score=initial_result.score,
        initial_summary=initial_result.summary,
        issues_list=issues_list,
    )

    generation_config = {
        "temperature": GENERATION_TEMPERATURE,
        "response_mime_type": "application/json",
        "response_schema": CROSS_VALIDATION_SCHEMA,
    }

    try:
        image = Image.open(snapshot_path)
        response = model.generate_content([prompt, image], generation_config=generation_config)
        raw_response = response.text
        data = json.loads(raw_response)

        # Combine confirmed and new issues
        all_issues = list(data.get("confirmed_issues", []))
        all_issues.extend(data.get("new_issues", []))

        # Build summary noting how many issues were dismissed
        dismissed_count = len(data.get("dismissed_issues", []))
        summary = data.get("summary", "Cross-validation complete")
        if dismissed_count > 0:
            summary += f" ({dismissed_count} false positives filtered)"

        return VerificationResult(
            score=float(data.get("adjusted_score", initial_result.score)),
            summary=summary,
            issues=all_issues,
            suggestions=data.get("suggestions", []),
            raw_response=f"INITIAL:\n{initial_result.raw_response}\n\nCROSS-VALIDATION:\n{raw_response}",
        )
    except Exception as e:
        # If cross-validation fails, return initial result
        return VerificationResult(
            score=initial_result.score,
            summary=f"{initial_result.summary} (cross-validation failed: {e})",
            issues=initial_result.issues,
            suggestions=initial_result.suggestions,
            raw_response=initial_result.raw_response,
        )


def verify_file(filepath: str, sheet_name: str | None = None) -> VerificationResult:
    """
    Extract and verify a single file using two-pass cross-validation.

    Pass 1: Initial verification comparing extracted data to source
    Pass 2: Cross-validation to filter false positives and confirm real issues
    Pass 3: Layer total cross-check using summary columns (if available)

    Args:
        filepath: Path to Excel file
        sheet_name: Optional sheet name

    Returns:
        VerificationResult with cross-validated findings
    """
    from ..extractor import extract_schematic_with_summaries
    from .layer_check import cross_check_layer_totals

    entries, layer_summaries = extract_schematic_with_summaries(filepath, sheet_name)
    if not entries:
        return VerificationResult(
            score=0.0,
            summary="No data extracted from file",
            issues=["Extraction returned empty results"],
            suggestions=["Check if file format is supported"],
            raw_response="",
        )

    # Pass 1: Initial verification (text + image if available)
    initial_result = verify_extraction(filepath, entries, sheet_name)

    # Pass 2: Cross-validation to filter false positives
    final_result = cross_validate(filepath, entries, initial_result, sheet_name)

    # Pass 3: Cross-check layer totals against summary columns (if available)
    if layer_summaries:
        final_result = cross_check_layer_totals(entries, layer_summaries, final_result)

    return final_result
