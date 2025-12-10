"""Gemini API client and request handling for verification."""

import json
import logging
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

from ..types import VerificationError

# =============================================================================
# Configuration Constants
# =============================================================================

# Default model for verification (flash-lite has thinking OFF, so use flash)
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# Generation temperature (0 for deterministic output)
GENERATION_TEMPERATURE = 0

# Library logging follows best practice: NullHandler by default
# CLI tools/users can configure logging to see output
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def get_client() -> genai.GenerativeModel:
    """Initialize Gemini client."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    model_id = os.getenv("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL)

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_id)


def parse_json_response(raw_response: str) -> dict:
    """Parse JSON from Gemini response, handling common issues."""
    text = raw_response.strip()

    # Handle markdown code blocks
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to fix common escape issues
    # Replace problematic backslashes that aren't valid escapes
    text_fixed = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)
    try:
        return json.loads(text_fixed)
    except json.JSONDecodeError:
        pass

    # Try to extract just the JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        json_str = match.group()
        # Fix escapes in extracted JSON
        json_str = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Last resort: try to build a minimal valid response
    score_match = re.search(r'"score"\s*:\s*([\d.]+)', text)
    summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text)

    if score_match:
        return {
            "score": float(score_match.group(1)),
            "summary": summary_match.group(1) if summary_match else "Partial parse",
            "issues": [],
            "suggestions": [],
        }

    raise ValueError("Could not parse JSON response")


def make_gemini_request(
    model: genai.GenerativeModel,
    prompt: str,
    schema: dict,
    image: Image.Image | None = None,
    context: str = "request",
) -> tuple[dict, str, dict]:
    """Make a Gemini request with structured output and fallback parsing.

    Args:
        model: Gemini model instance
        prompt: The prompt text
        schema: JSON schema for structured output
        image: Optional PIL Image for multimodal requests
        context: Context string for logging (e.g., "verify_extraction")

    Returns:
        Tuple of (parsed_data, raw_response, metadata)

    Raises:
        VerificationError: If both structured output and fallback parsing fail
    """
    generation_config = {
        "temperature": GENERATION_TEMPERATURE,
        "response_mime_type": "application/json",
        "response_schema": schema,
    }

    content = [prompt, image] if image else prompt
    structured_error_msg = None

    # Try structured output first
    try:
        response = model.generate_content(content, generation_config=generation_config)
        raw_response = response.text
        data = json.loads(raw_response)
        logger.info("%s: structured output parsed successfully", context)
        return data, raw_response, {"parsing_method": "structured", "fallback_used": False}
    except Exception as e:
        structured_error_msg = str(e)
        logger.warning(
            "%s: structured output failed (%s), using fallback parser",
            context,
            structured_error_msg,
        )

    # Fallback: try without schema enforcement
    try:
        response = model.generate_content(content if image else prompt)
        raw_response = response.text
        data = parse_json_response(raw_response)
        logger.info("%s: fallback parser succeeded", context)
        return (
            data,
            raw_response,
            {
                "parsing_method": "fallback",
                "fallback_used": True,
                "structured_error": structured_error_msg,
            },
        )
    except Exception as fallback_error:
        logger.error("%s: fallback parser also failed (%s)", context, str(fallback_error))
        raise VerificationError(
            f"Both structured output and fallback parsing failed: {structured_error_msg}, {fallback_error}"
        ) from fallback_error
