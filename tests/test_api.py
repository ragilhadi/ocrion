"""Tests for OCRion API."""

import pytest
import io
from fastapi.testclient import TestClient
from PIL import Image
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new("RGB", (800, 600), color="white")
    # Draw some text on the image
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "Invoice Number: INV-2024-001", fill="black")
    draw.text((50, 100), "Total: $1,234.56", fill="black")
    draw.text((50, 150), "Date: 2024-01-15", fill="black")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes


@pytest.fixture
def sample_schema():
    """Sample extraction schema."""
    return '{"invoice_number": "Invoice identifier", "total": "Final amount", "date": "Invoice date"}'


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health check returns correct structure."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ocrion"
        assert "model" in data
        assert "ocr_gpu" in data
        assert "uptime_seconds" in data


class TestExtractionEndpoint:
    """Tests for /extract endpoint."""

    def test_extract_missing_file(self, client, sample_schema):
        """Test extraction without file returns 422."""
        response = client.post("/extract", data={"schema": sample_schema})
        assert response.status_code == 422

    def test_extract_missing_schema(self, client, sample_image):
        """Test extraction without schema returns 422."""
        response = client.post(
            "/extract", files={"file": ("test.jpg", sample_image, "image/jpeg")}
        )
        assert response.status_code == 422

    def test_extract_invalid_file_type(self, client, sample_schema):
        """Test extraction with invalid file type."""
        invalid_file = io.BytesIO(b"This is not an image")
        response = client.post(
            "/extract",
            files={"file": ("test.txt", invalid_file, "text/plain")},
            data={"schema": sample_schema},
        )
        assert response.status_code in [400, 422]

    def test_extract_invalid_schema_json(self, client, sample_image):
        """Test extraction with invalid schema JSON."""
        response = client.post(
            "/extract",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"schema": "{invalid json}"},
        )
        assert response.status_code == 400

    def test_extract_invalid_schema_structure(self, client, sample_image):
        """Test extraction with invalid schema structure."""
        # Schema with empty keys
        response = client.post(
            "/extract",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"schema": '{"": "description"}'},
        )
        assert response.status_code == 400


class TestExtractionSuccess:
    """Tests for successful extraction flow."""

    @patch("app.services.ocr_service.OCRService.extract_text")
    @patch("app.services.llm_service.get_llm_service")
    def test_successful_extraction(
        self, mock_llm_service, mock_ocr, client, sample_image, sample_schema
    ):
        """Test successful extraction end-to-end."""
        from app.schemas.request import OCRResult

        # Mock OCR to return some text
        mock_ocr.return_value = [
            OCRResult(
                text="Invoice Number: INV-2024-001",
                bbox=[10, 10, 400, 40],
                confidence=0.95,
            ),
            OCRResult(text="Total: $1,234.56", bbox=[10, 50, 200, 80], confidence=0.92),
            OCRResult(
                text="Date: 2024-01-15", bbox=[10, 90, 150, 120], confidence=0.94
            ),
        ]

        # Mock LLM service
        mock_llm_instance = MagicMock()
        mock_llm_service.return_value = mock_llm_instance
        mock_llm_instance.extract_with_retry.return_value = {
            "invoice_number": "INV-2024-001",
            "total": "1234.56",
            "date": "2024-01-15",
        }

        response = client.post(
            "/extract",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"schema": sample_schema},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        assert data["data"]["invoice_number"] == "INV-2024-001"
        assert data["metadata"]["ocr_regions_detected"] == 3
        assert "processing_time_seconds" in data["metadata"]


class TestFileValidation:
    """Tests for file validation."""

    def test_file_size_limit(self, client):
        """Test file size limit enforcement."""
        # Create a file larger than 5MB
        large_file = io.BytesIO(b"x" * (6 * 1024 * 1024))

        response = client.post(
            "/extract",
            files={"file": ("large.jpg", large_file, "image/jpeg")},
            data={"schema": '{"field": "description"}'},
        )

        assert response.status_code == 400
        assert "exceeds maximum" in response.json()["detail"]


class TestSchemaValidation:
    """Tests for schema validation."""

    def test_empty_schema(self, client, sample_image):
        """Test empty schema is rejected."""
        response = client.post(
            "/extract",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"schema": "{}"},
        )

        assert response.status_code == 400

    def test_schema_too_many_fields(self, client, sample_image):
        """Test schema with too many fields is rejected."""
        # Create schema with 51 fields
        schema = {f"field_{i}": "description" for i in range(51)}
        import json

        schema_str = json.dumps(schema)

        response = client.post(
            "/extract",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"schema": schema_str},
        )

        assert response.status_code == 400


@pytest.mark.integration
class TestRealProcessing:
    """Integration tests that require actual OCR and LLM (requires API key)."""

    @pytest.mark.skipif(
        "os.getenv('OPENROUTER_API_KEY') is None or "
        "os.getenv('OPENROUTER_API_KEY') == 'your_openrouter_api_key_here'"
    )
    def test_real_ocr_extraction(self, client, sample_image, sample_schema):
        """Test extraction with real OCR (requires API key)."""
        response = client.post(
            "/extract",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"schema": sample_schema},
        )

        # Should process successfully
        assert response.status_code in [200, 400]  # 400 if no text detected
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "data" in data
