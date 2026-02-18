"""Request and response schemas for the extraction API.

Defines Pydantic models for API requests, responses, and data structures.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ExtractionRequest(BaseModel):
    """Schema for structured data extraction requests.

    Defines the fields to extract and their descriptions for LLM guidance.
    """

    schema_definition: dict[str, str] = Field(
        ...,
        description="Schema mapping field names to descriptions",
        json_schema_extra={
            "example": {
                "invoice_number": "Unique invoice identifier",
                "total": "Final amount including tax",
                "date": "Invoice date in YYYY-MM-DD format",
            }
        },
    )

    @field_validator("schema_definition")
    @classmethod
    def validate_schema(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate schema definition structure and content.

        Args:
            v: Schema dictionary to validate.

        Returns:
            Validated schema dictionary.

        Raises:
            ValueError: If schema is invalid.
        """
        if not v:
            msg = "Schema cannot be empty"
            raise ValueError(msg)
        if len(v) > 50:
            msg = "Schema cannot have more than 50 fields"
            raise ValueError(msg)
        for key, description in v.items():
            if not key.strip():
                msg = "Schema keys cannot be empty or whitespace"
                raise ValueError(msg)
            if not isinstance(key, str):
                msg = "Schema keys must be strings"
                raise ValueError(msg)
            if not isinstance(description, str):
                msg = "Schema values must be strings"
                raise ValueError(msg)
            if any(c in key for c in "\n\r\t"):
                msg = "Schema keys cannot contain newlines or tabs"
                raise ValueError(msg)
        return v


class OCRResult(BaseModel):
    """OCR detection result with text and bounding box."""

    text: str = Field(..., description="Extracted text content")
    bbox: list[float] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="OCR confidence score (0-1)"
    )


class LayoutBlock(BaseModel):
    """Text block after layout analysis and ordering."""

    text: str = Field(..., description="Block text content")
    bbox: list[float] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    page_num: int = Field(default=1, description="Page number (1-indexed)")
    block_type: str = Field(default="text", description="Block type classification")


class ExtractionResponse(BaseModel):
    """Successful extraction response with data and metadata."""

    success: bool = Field(default=True, description="Request succeeded")
    data: dict[str, Any] = Field(..., description="Extracted data matching schema")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Processing metadata and timing"
    )

    @model_validator(mode="after")
    def add_defaults(self) -> "ExtractionResponse":
        """Add default metadata fields.

        Returns:
            Self with updated metadata.
        """
        self.metadata.setdefault("timestamp", datetime.utcnow().isoformat())
        return self


class ErrorResponse(BaseModel):
    """Error response for failed requests."""

    success: bool = Field(default=False, description="Request failed")
    error: str = Field(..., description="Error category")
    detail: str = Field(..., description="Detailed error message")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp",
    )


class HealthResponse(BaseModel):
    """Health check response with service status."""

    status: str = Field(default="healthy", description="Service health status")
    service: str = Field(default="ocrion", description="Service name")
    version: str = Field(default="1.0.0", description="API version")
    model: str = Field(..., description="LLM model in use")
    ocr_gpu: bool = Field(..., description="Whether OCR is using GPU acceleration")
    uptime_seconds: float | None = Field(
        None, description="Server uptime in seconds"
    )
