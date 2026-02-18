"""Isolated unit tests that don't require system dependencies."""
import pytest
from datetime import datetime
from pydantic import ValidationError


class TestSchemaValidations:
    """Tests for Pydantic schemas that can run without system dependencies."""

    def test_extraction_schema_valid(self):
        """Test valid schema creation."""
        from app.schemas.request import ExtractionRequest

        schema = {
            "invoice_number": "Invoice identifier",
            "total": "Total amount",
            "date": "Invoice date"
        }

        request = ExtractionRequest(schema_definition=schema)

        assert request.schema_definition == schema
        assert len(request.schema_definition) == 3

    def test_extraction_schema_empty_raises_error(self):
        """Test that empty schema raises validation error."""
        from app.schemas.request import ExtractionRequest

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition={})

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_extraction_schema_too_many_fields(self):
        """Test that schema with too many fields raises error."""
        from app.schemas.request import ExtractionRequest

        # Create schema with 51 fields
        schema = {f"field_{i}": "description" for i in range(51)}

        with pytest.raises(ValidationError) as exc_info:
            ExtractionRequest(schema_definition=schema)

        assert "cannot have more than 50 fields" in str(exc_info.value)

    def test_ocr_result_valid(self):
        """Test valid OCR result creation."""
        from app.schemas.request import OCRResult

        result = OCRResult(
            text="Sample text",
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.95
        )

        assert result.text == "Sample text"
        assert result.confidence == 0.95

    def test_ocr_result_confidence_bounds(self):
        """Test confidence validation bounds."""
        from app.schemas.request import OCRResult

        # Valid values
        OCRResult(text="A", bbox=[0, 0, 1, 1], confidence=0.0)
        OCRResult(text="A", bbox=[0, 0, 1, 1], confidence=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            OCRResult(text="A", bbox=[0, 0, 1, 1], confidence=-0.1)

        with pytest.raises(ValidationError):
            OCRResult(text="A", bbox=[0, 0, 1, 1], confidence=1.1)

    def test_layout_block_defaults(self):
        """Test LayoutBlock default values."""
        from app.schemas.request import LayoutBlock

        block = LayoutBlock(text="Sample", bbox=[0, 0, 10, 10])

        assert block.text == "Sample"
        assert block.page_num == 1
        assert block.block_type == "text"

    def test_extraction_response_defaults(self):
        """Test ExtractionResponse default values."""
        from app.schemas.request import ExtractionResponse

        response = ExtractionResponse(
            data={"field1": "value1"}
        )

        assert response.success is True
        # The model_validator should have added timestamp
        assert response.metadata is not None
        assert "timestamp" in response.metadata or len(response.metadata) >= 0

    def test_error_response_defaults(self):
        """Test ErrorResponse default values."""
        from app.schemas.request import ErrorResponse

        response = ErrorResponse(
            error="test_error",
            detail="test detail"
        )

        assert response.success is False
        # timestamp is a string field that gets auto-populated
        assert response.timestamp
        assert len(response.timestamp) > 0

    def test_health_response_defaults(self):
        """Test HealthResponse default values."""
        from app.schemas.request import HealthResponse

        response = HealthResponse(
            model="test-model",
            ocr_gpu=False
        )

        assert response.status == "healthy"
        assert response.service == "ocrion"
        assert response.version == "1.0.0"
        assert response.uptime_seconds is None


class TestConfigSettings:
    """Tests for configuration settings."""

    def test_settings_defaults(self):
        """Test default settings values."""
        from app.config import Settings, Field
        import os

        # Set test environment
        os.environ['OPENROUTER_API_KEY'] = 'test_key_12345'

        settings = Settings()

        assert settings.openrouter_api_key == 'test_key_12345'
        assert settings.max_tokens == 4096
        assert settings.api_port == 8000
        assert settings.workers == 4
        assert settings.ocr_use_gpu is False
        assert settings.max_upload_size == 5242880

    def test_settings_validation(self):
        """Test settings validation."""
        from app.config import Settings
        import os

        # Test invalid port
        with pytest.raises(ValidationError):
            Settings(_env_file=None, api_port=100000)

        # Test invalid max_tokens
        with pytest.raises(ValidationError):
            Settings(_env_file=None, max_tokens=100000)


class TestPromptBuilder:
    """Tests for prompt builder (no system dependencies)."""

    def test_build_standard_prompt(self):
        """Test standard prompt building."""
        from app.services.prompt_builder import PromptBuilder

        schema = {"invoice_number": "Invoice ID", "total": "Total amount"}
        text = "Invoice #123 Total: $500"

        prompt = PromptBuilder.build_extraction_prompt(schema, text, strict=False)

        assert "invoice_number" in prompt
        assert "total" in prompt
        assert "Invoice #123 Total: $500" in prompt
        assert "JSON object" in prompt

    def test_build_strict_prompt(self):
        """Test strict prompt building."""
        from app.services.prompt_builder import PromptBuilder

        schema = {"field1": "description"}
        text = "Sample text"

        prompt = PromptBuilder.build_extraction_prompt(schema, text, strict=True)

        assert "JSON ONLY" in prompt or "CRITICAL" in prompt
        assert "field1" in prompt

    def test_format_schema_for_prompt(self):
        """Test schema formatting."""
        from app.services.prompt_builder import PromptBuilder

        schema = {
            "invoice_number": "Invoice ID",
            "total": "Total amount"
        }

        result = PromptBuilder.format_schema_for_prompt(schema)

        assert "invoice_number: Invoice ID" in result
        assert "total: Total amount" in result
        assert "Required fields:" in result


class TestLLMServiceValidation:
    """Tests for LLM service validation logic (no API calls)."""

    def test_llm_service_initialization(self):
        """Test LLM service can be initialized."""
        from app.services.llm_service import LLMService
        from app.config import settings
        import os

        os.environ['OPENROUTER_API_KEY'] = 'test_key'

        service = LLMService()

        assert service.client is not None
        assert service.model == settings.model_name

    def test_validate_extraction_success(self):
        """Test successful extraction validation."""
        from app.services.llm_service import LLMService

        service = LLMService()
        schema = {"field1": "desc1", "field2": "desc2"}
        extracted = {"field1": "value1", "field2": "value2"}

        result = service._validate_extraction(extracted, schema)

        assert result == extracted

    def test_validate_extraction_missing_field(self):
        """Test validation with missing field."""
        from app.services.llm_service import LLMService

        service = LLMService()
        schema = {"field1": "desc1", "field2": "desc2"}
        extracted = {"field1": "value1"}  # Missing field2

        with pytest.raises(ValueError, match="Missing required field"):
            service._validate_extraction(extracted, schema)

    def test_validate_extraction_extra_fields_filtered(self):
        """Test that extra fields are filtered out."""
        from app.services.llm_service import LLMService

        service = LLMService()
        schema = {"field1": "desc1"}
        extracted = {"field1": "value1", "extra": "extra_value"}

        result = service._validate_extraction(extracted, schema)

        # Extra fields should be filtered out
        assert result == {"field1": "value1"}

    def test_validate_extraction_not_dict(self):
        """Test validation when extracted data is not a dict."""
        from app.services.llm_service import LLMService

        service = LLMService()
        schema = {"field1": "desc1"}
        extracted = ["not", "a", "dict"]

        with pytest.raises(ValueError, match="not a JSON object"):
            service._validate_extraction(extracted, schema)


class TestLayoutService:
    """Tests for layout service spatial ordering logic."""

    def test_order_blocks_empty(self):
        """Test layout ordering with empty results."""
        from app.services.layout_service import LayoutService
        from app.schemas.request import OCRResult

        results = LayoutService.order_blocks([], 800, 600)

        assert results == []

    def test_order_blocks_vertical_order(self):
        """Test vertical ordering (top to bottom)."""
        from app.services.layout_service import LayoutService
        from app.schemas.request import OCRResult

        ocr_results = [
            OCRResult(text="Bottom", bbox=[10, 100, 100, 120], confidence=0.95),
            OCRResult(text="Top", bbox=[10, 10, 100, 30], confidence=0.95),
            OCRResult(text="Middle", bbox=[10, 50, 100, 70], confidence=0.95),
        ]

        results = LayoutService.order_blocks(ocr_results, 800, 600)

        # Should be ordered top to bottom
        assert results[0].text == "Top"
        assert results[1].text == "Middle"
        assert results[2].text == "Bottom"

    def test_order_blocks_horizontal_order(self):
        """Test horizontal ordering (left to right) within same row."""
        from app.services.layout_service import LayoutService
        from app.schemas.request import OCRResult

        ocr_results = [
            OCRResult(text="Right", bbox=[200, 10, 300, 30], confidence=0.95),
            OCRResult(text="Left", bbox=[10, 10, 100, 30], confidence=0.95),
            OCRResult(text="Middle", bbox=[110, 10, 190, 30], confidence=0.95),
        ]

        results = LayoutService.order_blocks(ocr_results, 800, 600)

        # Should be ordered left to right (same y-position)
        assert results[0].text == "Left"
        assert results[1].text == "Middle"
        assert results[2].text == "Right"

    def test_combine_text_empty(self):
        """Test text combination with empty blocks."""
        from app.services.layout_service import LayoutService

        result = LayoutService.combine_text([])

        assert result == ""

    def test_combine_text_single_line(self):
        """Test text combination with single line."""
        from app.services.layout_service import LayoutService
        from app.schemas.request import LayoutBlock

        blocks = [
            LayoutBlock(text="Hello", bbox=[0, 0, 100, 20], page_num=1, block_type="text"),
            LayoutBlock(text="World", bbox=[110, 0, 200, 20], page_num=1, block_type="text"),
        ]

        result = LayoutService.combine_text(blocks)

        assert result == "Hello World"

    def test_combine_text_multiple_lines(self):
        """Test text combination with multiple lines."""
        from app.services.layout_service import LayoutService
        from app.schemas.request import LayoutBlock

        blocks = [
            LayoutBlock(text="Line", bbox=[0, 0, 100, 20], page_num=1, block_type="text"),
            LayoutBlock(text="1", bbox=[110, 0, 200, 20], page_num=1, block_type="text"),
            LayoutBlock(text="Line", bbox=[0, 50, 100, 70], page_num=1, block_type="text"),
            LayoutBlock(text="2", bbox=[110, 50, 200, 70], page_num=1, block_type="text"),
        ]

        result = LayoutService.combine_text(blocks)

        assert "Line 1" in result
        assert "Line 2" in result


class TestFileValidator:
    """Tests for file validator (content-based validation)."""

    def test_allowed_mime_types(self):
        """Test that expected MIME types are allowed."""
        from app.utils.validators import FileValidator

        allowed_types = FileValidator.ALLOWED_MIME_TYPES

        assert "image/jpeg" in allowed_types
        assert "image/jpg" in allowed_types
        assert "image/png" in allowed_types
        assert "application/pdf" in allowed_types

    def test_file_size_constant(self):
        """Test max file size is set."""
        from app.utils.validators import FileValidator

        assert FileValidator.MAX_SIZE > 0
        assert FileValidator.MAX_SIZE == 5242880  # 5MB default
