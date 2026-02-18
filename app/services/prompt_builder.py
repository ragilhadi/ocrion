"""Prompt builder for LLM extraction.

Constructs prompts for structured data extraction with schema awareness.
"""

import json
import logging

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds extraction prompts with schema awareness."""

    @staticmethod
    def build_extraction_prompt(
        schema: dict[str, str], ordered_text: str, *, strict: bool = False
    ) -> str:
        """Build prompt for LLM-based structured extraction.

        Args:
            schema: Dictionary mapping field names to descriptions.
            ordered_text: OCR text in reading order.
            strict: If True, use strict mode for retry attempts.

        Returns:
            Formatted prompt string for LLM.
        """
        schema_json = json.dumps(schema, indent=2)

        if strict:
            return PromptBuilder._build_strict_prompt(schema_json, ordered_text)
        return PromptBuilder._build_standard_prompt(schema_json, ordered_text)

    @staticmethod
    def _build_standard_prompt(schema_json: str, ordered_text: str) -> str:
        """Build standard extraction prompt with detailed instructions.

        Args:
            schema_json: JSON string of schema definition.
            ordered_text: Document text to extract from.

        Returns:
            Formatted standard prompt.
        """
        return f"""You are a precise data extraction assistant. Extract structured information from document text.

IMPORTANT REQUIREMENTS:
1. Return ONLY a valid JSON object
2. Use EXACTLY the field names specified in the schema below
3. If a field cannot be found, use null (not empty string, not "N/A")
4. Dates should be in YYYY-MM-DD format when possible
5. Monetary values should be numeric (no currency symbols)
6. Do NOT include any explanations, markdown formatting, or text outside the JSON

SCHEMA:
{schema_json}

DOCUMENT TEXT:
{ordered_text}

Return your response as a JSON object with the exact schema fields: """

    @staticmethod
    def _build_strict_prompt(schema_json: str, ordered_text: str) -> str:
        """Build strict prompt for retry attempts.

        Args:
            schema_json: JSON string of schema definition.
            ordered_text: Document text to extract from.

        Returns:
            Formatted strict prompt with minimal instructions.
        """
        schema_dict = json.loads(schema_json)
        return f"""EXTRACT DATA AS JSON ONLY.

Schema: {schema_json}

Document Text:
{ordered_text}

CRITICAL: Respond with ONLY a raw JSON object. No markdown, no explanation, no preamble.
Output must be valid JSON with exactly these keys: {list(schema_dict.keys())}

JSON: """

    @staticmethod
    def format_schema_for_prompt(schema: dict[str, str]) -> str:
        """Format schema for human-readable prompt display.

        Args:
            schema: Schema dictionary.

        Returns:
            Formatted string representation of schema.
        """
        lines = ["Required fields:"]
        for field, description in schema.items():
            lines.append(f"  - {field}: {description}")
        return "\n".join(lines)
