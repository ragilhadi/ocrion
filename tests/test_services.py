"""Unit tests for OCRion services."""

import pytest
from unittest.mock import Mock, patch
from PIL import Image

from app.services.ocr_service import OCRService, OCRResult
from app.services.layout_service import LayoutService
from app.services.prompt_builder import PromptBuilder
from app.schemas.request import LayoutBlock


class TestOCRService:
    """Tests for OCRService."""

    @patch("app.services.ocr_service.PaddleOCR")
    def test_singleton_initialization(self, mock_paddleocr):
        """Test that OCR service uses singleton pattern."""
        # Reset the singleton
        import app.services.ocr_service as ocr_module

        ocr_module._ocr_instance.initialized = False

        mock_instance = Mock()
        mock_paddleocr.return_value = mock_instance

        # First call should initialize
        service1 = OCRService.get_instance()
        assert service1 == mock_instance

        # Second call should return same instance
        service2 = OCRService.get_instance()
        assert service1 == service2

    @patch("app.services.ocr_service.PaddleOCR")
    def test_extract_text_success(self, mock_paddleocr):
        """Test successful text extraction."""
        # Reset singleton
        import app.services.ocr_service as ocr_module

        ocr_module._ocr_instance.initialized = False
        ocr_module._ocr_instance.instance = None

        # Mock OCR result
        mock_ocr = Mock()
        mock_paddleocr.return_value = mock_ocr
        mock_ocr.ocr.return_value = [
            [
                [
                    [[10, 20], [200, 20], [200, 40], [10, 40]],  # bbox
                    ("Sample Text", 0.95),  # (text, confidence)
                ]
            ]
        ]

        # Create test image
        img = Image.new("RGB", (800, 600), color="white")

        # Extract text
        results = OCRService.extract_text(img)

        # Assertions
        assert len(results) == 1
        assert results[0].text == "Sample Text"
        assert results[0].confidence == 0.95
        assert results[0].bbox == [10.0, 20.0, 200.0, 40.0]

    @patch("app.services.ocr_service.PaddleOCR")
    def test_extract_text_no_detection(self, mock_paddleocr):
        """Test OCR when no text is detected."""
        # Reset singleton
        import app.services.ocr_service as ocr_module

        ocr_module._ocr_instance.initialized = False
        ocr_module._ocr_instance.instance = None

        mock_ocr = Mock()
        mock_paddleocr.return_value = mock_ocr
        mock_ocr.ocr.return_value = None

        img = Image.new("RGB", (800, 600), color="white")

        results = OCRService.extract_text(img)

        assert results == []

    @patch("app.services.ocr_service.PaddleOCR")
    def test_extract_text_empty_result(self, mock_paddleocr):
        """Test OCR when result is empty list."""
        # Reset singleton
        import app.services.ocr_service as ocr_module

        ocr_module._ocr_instance.initialized = False
        ocr_module._ocr_instance.instance = None

        mock_ocr = Mock()
        mock_paddleocr.return_value = mock_ocr
        mock_ocr.ocr.return_value = [[]]

        img = Image.new("RGB", (800, 600), color="white")

        results = OCRService.extract_text(img)

        assert results == []


class TestLayoutService:
    """Tests for LayoutService."""

    def test_order_blocks_empty(self):
        """Test layout ordering with empty results."""
        results = LayoutService.order_blocks([], 800, 600)
        assert results == []

    def test_order_blocks_single(self):
        """Test layout ordering with single block."""
        ocr_results = [OCRResult(text="Hello", bbox=[10, 10, 100, 30], confidence=0.95)]

        results = LayoutService.order_blocks(ocr_results, 800, 600)

        assert len(results) == 1
        assert results[0].text == "Hello"

    def test_order_blocks_vertical_order(self):
        """Test vertical ordering (top to bottom)."""
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
        result = LayoutService.combine_text([])
        assert result == ""

    def test_combine_text_single_line(self):
        """Test text combination with single line."""
        blocks = [
            LayoutBlock(
                text="Hello", bbox=[0, 0, 100, 20], page_num=1, block_type="text"
            ),
            LayoutBlock(
                text="World", bbox=[110, 0, 200, 20], page_num=1, block_type="text"
            ),
        ]

        result = LayoutService.combine_text(blocks)

        assert result == "Hello World"

    def test_combine_text_multiple_lines(self):
        """Test text combination with multiple lines."""
        blocks = [
            LayoutBlock(
                text="Line", bbox=[0, 0, 100, 20], page_num=1, block_type="text"
            ),
            LayoutBlock(
                text="1", bbox=[110, 0, 200, 20], page_num=1, block_type="text"
            ),
            LayoutBlock(
                text="Line", bbox=[0, 50, 100, 70], page_num=1, block_type="text"
            ),
            LayoutBlock(
                text="2", bbox=[110, 50, 200, 70], page_num=1, block_type="text"
            ),
        ]

        result = LayoutService.combine_text(blocks)

        assert "Line 1" in result
        assert "Line 2" in result


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    def test_build_standard_prompt(self):
        """Test standard prompt building."""
        schema = {"invoice_number": "Invoice identifier", "total": "Total amount"}
        text = "Invoice #123 Total: $500"

        prompt = PromptBuilder.build_extraction_prompt(schema, text, strict=False)

        assert "invoice_number" in prompt
        assert "total" in prompt
        assert "Invoice #123 Total: $500" in prompt
        assert "JSON object" in prompt

    def test_build_strict_prompt(self):
        """Test strict prompt building."""
        schema = {"field1": "description"}
        text = "Sample text"

        prompt = PromptBuilder.build_extraction_prompt(schema, text, strict=True)

        assert "JSON ONLY" in prompt
        assert "CRITICAL" in prompt
        assert "field1" in prompt

    def test_format_schema_for_prompt(self):
        """Test schema formatting."""
        schema = {"invoice_number": "Invoice ID", "total": "Total amount"}

        result = PromptBuilder.format_schema_for_prompt(schema)

        assert "invoice_number: Invoice ID" in result
        assert "total: Total amount" in result
        assert "Required fields:" in result


class TestLLMService:
    """Tests for LLMService."""

    def test_initialization(self):
        """Test LLM service initialization."""
        from app.services.llm_service import LLMService
        from app.config import settings

        service = LLMService()

        assert service.client is not None
        assert service.model == settings.model_name
        assert service.max_tokens == settings.max_tokens

    def test_singleton(self):
        """Test LLM service singleton pattern."""
        from app.services.llm_service import get_llm_service

        # Reset singleton
        import app.services.llm_service as llm_module

        llm_module._llm_service = None

        service1 = get_llm_service()
        service2 = get_llm_service()

        assert service1 is service2

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

    def test_validate_extraction_extra_fields(self):
        """Test validation with extra fields (should warn but not fail)."""
        from app.services.llm_service import LLMService

        service = LLMService()
        schema = {"field1": "desc1"}
        extracted = {"field1": "value1", "extra": "extra_value"}

        result = service._validate_extraction(extracted, schema)

        # Extra fields should be filtered out
        assert result == {"field1": "value1"}
        assert "extra" not in result

    def test_validate_extraction_not_dict(self):
        """Test validation when extracted data is not a dict."""
        from app.services.llm_service import LLMService

        service = LLMService()
        schema = {"field1": "desc1"}
        extracted = ["not", "a", "dict"]

        with pytest.raises(ValueError, match="not a JSON object"):
            service._validate_extraction(extracted, schema)


class TestFileValidator:
    """Tests for FileValidator."""

    def test_file_size_validation(self):
        """Test file size validation."""
        from app.utils.validators import FileValidator
        import app.config as config

        # Save original max size
        original_max = config.settings.max_upload_size

        try:
            # Set small max size for testing
            config.settings.max_upload_size = 1000

            # Create file that's too large
            large_content = b"x" * 2000
            is_valid, error = FileValidator.validate_file(large_content, "test.jpg")

            assert not is_valid
            assert "exceeds maximum" in error

        finally:
            # Restore original max size
            config.settings.max_upload_size = original_max

    def test_file_size_pass(self):
        """Test file size validation passes."""
        from app.utils.validators import FileValidator

        # Create small file
        small_content = b"x" * 100
        is_valid, error = FileValidator.validate_file(small_content, "test.jpg")

        # Should pass size check (may fail mime check)
        assert "exceeds maximum" not in (error or "")

    @pytest.mark.parametrize(
        "mime_type", ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
    )
    def test_allowed_mime_types(self, mime_type):
        """Test that allowed MIME types pass."""
        from app.utils.validators import FileValidator

        # This test would require actual file content with proper magic bytes
        # For now, just verify the configuration
        assert mime_type in FileValidator.ALLOWED_MIME_TYPES
