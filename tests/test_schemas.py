"""Unit tests for Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.request import (
    ExtractionRequest,
    OCRResult,
    LayoutBlock,
    ExtractionResponse,
    ErrorResponse,
    HealthResponse,
)


class TestExtractionRequest:
    """Tests for ExtractionRequest schema."""

    def test_valid_schema(self):
        """Test valid schema creation."""
        schema = {
            "invoice_number": "Invoice identifier",
            "total": "Total amount",
            "date": "Invoice date",
        }

        request = ExtractionRequest(schema_definition=schema)

        assert request.schema_definition == schema

    def test_empty_schema_raises_error(self):
        """Test that empty schema raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition={})

        assert "Schema cannot be empty" in str(exc_info.value)

    def test_schema_too_many_fields(self):
        """Test that schema with too many fields raises error."""
        # Create schema with 51 fields
        schema = {f"field_{i}": "description" for i in range(51)}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        assert "cannot have more than 50 fields" in str(exc_info.value)

    def test_empty_key_raises_error(self):
        """Test that empty key raises validation error."""
        schema = {"": "description", "valid": "description"}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        assert "cannot be empty or whitespace" in str(exc_info.value)

    def test_whitespace_key_raises_error(self):
        """Test that whitespace-only key raises error."""
        schema = {"   ": "description", "valid": "description"}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        assert "cannot be empty or whitespace" in str(exc_info.value)

    def test_key_with_newline_raises_error(self):
        """Test that key with newline raises error."""
        schema = {"valid\nkey": "description"}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        assert "cannot contain newlines" in str(exc_info.value)

    def test_non_string_key_raises_error(self):
        """Test that non-string key raises error."""
        schema = {123: "description"}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        # Pydantic v2 uses "valid string" message
        assert "valid string" in str(exc_info.value).lower()

    def test_non_string_value_raises_error(self):
        """Test that non-string value raises error."""
        schema = {"field": 123}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        # Pydantic v2 uses "valid string" message
        assert "valid string" in str(exc_info.value).lower()


class TestOCRResult:
    """Tests for OCRResult schema."""

    def test_valid_ocr_result(self):
        """Test valid OCR result creation."""
        result = OCRResult(
            text="Sample text", bbox=[10.0, 20.0, 100.0, 50.0], confidence=0.95
        )

        assert result.text == "Sample text"
        assert result.bbox == [10.0, 20.0, 100.0, 50.0]
        assert result.confidence == 0.95

    def test_confidence_out_of_range_high(self):
        """Test that confidence > 1.0 raises error."""
        with pytest.raises(ValidationError):
            OCRResult(text="Sample", bbox=[0, 0, 10, 10], confidence=1.5)

    def test_confidence_out_of_range_low(self):
        """Test that confidence < 0.0 raises error."""
        with pytest.raises(ValidationError):
            OCRResult(text="Sample", bbox=[0, 0, 10, 10], confidence=-0.1)

    def test_confidence_boundary_values(self):
        """Test boundary confidence values."""
        # Should accept 0.0 and 1.0
        result1 = OCRResult(text="Sample", bbox=[0, 0, 10, 10], confidence=0.0)
        assert result1.confidence == 0.0

        result2 = OCRResult(text="Sample", bbox=[0, 0, 10, 10], confidence=1.0)
        assert result2.confidence == 1.0


class TestLayoutBlock:
    """Tests for LayoutBlock schema."""

    def test_valid_layout_block(self):
        """Test valid layout block creation."""
        block = LayoutBlock(
            text="Sample text", bbox=[10, 20, 100, 50], page_num=1, block_type="text"
        )

        assert block.text == "Sample text"
        assert block.bbox == [10, 20, 100, 50]
        assert block.page_num == 1
        assert block.block_type == "text"

    def test_default_values(self):
        """Test default values for optional fields."""
        block = LayoutBlock(text="Sample", bbox=[0, 0, 10, 10])

        assert block.page_num == 1
        assert block.block_type == "text"


class TestExtractionResponse:
    """Tests for ExtractionResponse schema."""

    def test_valid_response(self):
        """Test valid extraction response creation."""
        response = ExtractionResponse(
            success=True,
            data={"field1": "value1", "field2": "value2"},
            metadata={"processing_time": 1.5},
        )

        assert response.success is True
        assert response.data == {"field1": "value1", "field2": "value2"}
        assert response.metadata["processing_time"] == 1.5
        assert "timestamp" in response.metadata

    def test_default_success(self):
        """Test that success defaults to True."""
        response = ExtractionResponse(data={"field": "value"})

        assert response.success is True

    def test_default_metadata(self):
        """Test that metadata defaults to dict with timestamp."""
        response = ExtractionResponse(data={"field": "value"})

        assert isinstance(response.metadata, dict)
        assert "timestamp" in response.metadata
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(response.metadata["timestamp"])


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_valid_error_response(self):
        """Test valid error response creation."""
        response = ErrorResponse(
            success=False, error="validation_error", detail="Invalid input data"
        )

        assert response.success is False
        assert response.error == "validation_error"
        assert response.detail == "Invalid input data"
        # timestamp is a string, check it's not empty
        assert response.timestamp
        assert len(response.timestamp) > 0

    def test_default_success(self):
        """Test that success defaults to False."""
        response = ErrorResponse(error="test_error", detail="test detail")

        assert response.success is False

    def test_timestamp_format(self):
        """Test that timestamp is a valid ISO format string."""
        response = ErrorResponse(error="test", detail="test")

        # Should not raise exception
        datetime.fromisoformat(response.timestamp)


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_valid_health_response(self):
        """Test valid health response creation."""
        response = HealthResponse(
            status="healthy",
            service="ocrion",
            version="1.0.0",
            model="test-model",
            ocr_gpu=False,
            uptime_seconds=123.45,
        )

        assert response.status == "healthy"
        assert response.service == "ocrion"
        assert response.version == "1.0.0"
        assert response.model == "test-model"
        assert response.ocr_gpu is False
        assert response.uptime_seconds == 123.45

    def test_default_values(self):
        """Test default values for health response."""
        response = HealthResponse(model="test-model", ocr_gpu=False)

        assert response.status == "healthy"
        assert response.service == "ocrion"
        assert response.version == "1.0.0"
        assert response.uptime_seconds is None

    def test_optional_uptime(self):
        """Test that uptime_seconds is optional."""
        response1 = HealthResponse(model="test", ocr_gpu=False, uptime_seconds=100.0)
        assert response1.uptime_seconds == 100.0

        response2 = HealthResponse(model="test", ocr_gpu=False)
        assert response2.uptime_seconds is None
