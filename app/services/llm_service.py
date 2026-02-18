"""LLM service for structured data extraction.

Uses OpenRouter API to extract structured data from OCR text based on schemas.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-based structured data extraction using OpenRouter."""

    def __init__(self) -> None:
        """Initialize OpenAI client configured for OpenRouter."""
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        self.model = settings.model_name
        self.max_tokens = settings.max_tokens

    async def extract_with_retry(
        self, schema: dict[str, str], ordered_text: str
    ) -> dict[str, Any]:
        """Extract structured data with automatic retry logic.

        Attempts standard prompt first, then strict prompt on failure.

        Args:
            schema: Extraction schema mapping field names to descriptions.
            ordered_text: OCR text in reading order.

        Returns:
            Extracted data as dictionary matching schema.

        Raises:
            Exception: If extraction fails after all retry attempts.
        """
        try:
            logger.info("Attempting extraction with standard prompt")
            return await self._extract(schema, ordered_text, strict=False)
        except Exception as e:
            logger.warning(f"Standard extraction failed: {e}")

        try:
            logger.info("Retrying with strict prompt")
            return await self._extract(schema, ordered_text, strict=True)
        except Exception as e:
            logger.error(f"Strict extraction also failed: {e}")
            raise Exception(f"Failed to extract data after retries: {e!s}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def _extract(
        self, schema: dict[str, str], ordered_text: str, *, strict: bool = False
    ) -> dict[str, Any]:
        """Perform extraction with retry on connection errors.

        Args:
            schema: Extraction schema.
            ordered_text: OCR text to extract from.
            strict: Whether to use strict prompt mode.

        Returns:
            Extracted data dictionary.

        Raises:
            ValueError: If response is invalid or doesn't match schema.
            ConnectionError: If API connection fails.
            TimeoutError: If API request times out.
        """
        prompt = PromptBuilder.build_extraction_prompt(
            schema, ordered_text, strict=strict
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data extraction assistant. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
                timeout=60.0,
            )

            content = response.choices[0].message.content

            if not content:
                msg = "Empty response from LLM"
                raise ValueError(msg)

            try:
                extracted_data = json.loads(content)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON response: {content[:200]}... Error: {e}"
                raise ValueError(msg) from e

            validated = self._validate_extraction(extracted_data, schema)

            logger.info(f"Successfully extracted {len(validated)} fields")
            return validated

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            raise

    def _validate_extraction(
        self, extracted: dict[str, Any], schema: dict[str, str]
    ) -> dict[str, Any]:
        """Validate extracted data against schema.

        Args:
            extracted: Data returned from LLM.
            schema: Expected schema definition.

        Returns:
            Validated data dictionary with only schema fields.

        Raises:
            ValueError: If validation fails or required fields are missing.
        """
        if not isinstance(extracted, dict):
            msg = "LLM response is not a JSON object"
            raise ValueError(msg)

        missing_keys = set(schema.keys()) - set(extracted.keys())
        if missing_keys:
            msg = f"Missing required fields: {missing_keys}"
            raise ValueError(msg)

        extra_keys = set(extracted.keys()) - set(schema.keys())
        if extra_keys:
            logger.warning(f"LLM returned extra fields: {extra_keys}")

        validated = {}
        for key in schema:
            if key not in extracted:
                msg = f"Missing required field: {key}"
                raise ValueError(msg)
            validated[key] = extracted[key]

        return validated


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton.

    Returns:
        Initialized LLM service instance.
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def initialize_llm() -> None:
    """Initialize LLM service on application startup.

    Raises:
        Exception: If initialization fails.
    """
    logger.info(f"Initializing LLM service with model: {settings.model_name}")
    get_llm_service()
    logger.info("LLM service ready")
