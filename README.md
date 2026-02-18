# OCRion: OCR → LayoutLM → LLM Structured Extraction API

A production-ready API service that extracts structured data from document images using a multi-stage pipeline: PaddleOCR → Layout Understanding (spatial ordering) → LLM-based extraction via OpenRouter.

## Architecture

```
Client Upload (Image + Schema)
    ↓
FastAPI Validation
    ↓
PaddleOCR (text + bounding boxes)
    ↓
Layout Service (spatial ordering: top-to-bottom, left-to-right)
    ↓
Prompt Builder (schema + ordered OCR text)
    ↓
OpenRouter LLM (structured extraction)
    ↓
Schema Validation → JSON Response
```

## Features

- **PaddleOCR Integration**: State-of-the-art text detection and recognition
- **Spatial Layout Analysis**: Intelligent reading order detection (top-to-bottom, left-to-right)
- **Schema-Aware Extraction**: LLM extracts only the fields you specify
- **Retry Logic**: Automatic fallback prompts for failed extractions
- **Production Ready**: Gunicorn + Uvicorn workers, health checks, structured logging
- **Type Safe**: Full Pydantic validation for requests and responses

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your OpenRouter API key
# OPENROUTER_API_KEY=your_actual_api_key_here
```

### 3. Start Server

```bash
# Using the start script (recommended for production)
./start.sh

# Or directly with uvicorn (for development)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/health

# Extract data from image
curl -X POST "http://localhost:8000/extract" \
  -F "file=@invoice.jpg" \
  -F 'schema={"invoice_number": "Invoice ID", "total": "Final amount", "date": "Invoice date"}'

# View API docs
open http://localhost:8000/docs
```

## API Usage

### POST /extract

Extract structured data from a document image.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Parameters:
  - `file`: Document image (JPG, PNG, PDF) - Max 5MB
  - `schema`: JSON string defining extraction schema

**Example Schema:**
```json
{
  "invoice_number": "Unique invoice identifier",
  "total": "Final amount including tax",
  "date": "Invoice date in YYYY-MM-DD format",
  "vendor": "Company name of the vendor"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "invoice_number": "INV-2024-001",
    "total": "1234.56",
    "date": "2024-01-15",
    "vendor": "Acme Corp"
  },
  "metadata": {
    "processing_time_seconds": 2.345,
    "ocr_time_seconds": 0.456,
    "layout_time_seconds": 0.123,
    "llm_time_seconds": 1.766,
    "ocr_regions_detected": 45,
    "layout_blocks": 12,
    "schema_fields": ["invoice_number", "total", "date", "vendor"],
    "image_size": {"width": 1920, "height": 1080},
    "model": "anthropic/claude-sonnet-4-20250514"
  }
}
```

### GET /health

Check API health and configuration.

**Response:**
```json
{
  "status": "healthy",
  "service": "ocrion",
  "version": "1.0.0",
  "model": "anthropic/claude-sonnet-4-20250514",
  "ocr_gpu": false,
  "uptime_seconds": 1234.567
}
```

## Project Structure

```
app/
├── main.py                 # FastAPI app entry point
├── config.py               # Settings with pydantic-settings
├── api/
│   └── routes.py           # POST /extract, GET /health
├── services/
│   ├── ocr_service.py      # PaddleOCR wrapper (singleton)
│   ├── layout_service.py   # Spatial text ordering
│   ├── llm_service.py      # OpenRouter integration
│   └── prompt_builder.py   # Schema-aware prompt construction
├── schemas/
│   └── request.py          # Pydantic models
└── utils/
    └── validators.py       # File validation
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key (required) | - |
| `MODEL_NAME` | LLM model to use | `anthropic/claude-sonnet-4-20250514` |
| `MAX_TOKENS` | Maximum response tokens | `4096` |
| `API_PORT` | Server port | `8000` |
| `WORKERS` | Worker count | `4` |
| `OCR_USE_GPU` | Enable GPU for OCR | `false` |
| `MAX_UPLOAD_SIZE` | Max upload size in bytes | `5242880` (5MB) |

## Error Handling

| Stage | Failure | Action |
|-------|---------|--------|
| File validation | Invalid type/size | 400 error |
| OCR | No text detected | 400 error |
| OCR | Processing error | 500 error |
| Layout | Analysis fails | Fallback to raw OCR |
| LLM | Invalid JSON | Retry with strict prompt |
| LLM | Schema mismatch | Validation error |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_api.py::TestHealthEndpoint::test_health_check

# Run integration tests (requires API key)
pytest -m integration
```

### Development Server

```bash
# Run with auto-reload
uvicorn app.main:app --reload
```

## Production Deployment

### Using Gunicorn (Recommended)

```bash
./start.sh
```

The `start.sh` script:
- Loads environment variables from `.env`
- Activates the virtual environment
- Installs dependencies if needed
- Starts Gunicorn with configured workers

### Manual Gunicorn

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --config gunicorn.conf.py
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["./start.sh"]
```

## Security

- File type validation via `python-magic` (content-based, not extension)
- 5MB upload limit (configurable)
- API keys only in environment variables
- Input sanitization via Pydantic
- CORS middleware (configure origins for production)

## Troubleshooting

### PaddleOCR initialization fails

```
# If you get errors about PaddleOCR, try:
pip uninstall paddlepaddle
pip install paddlepaddle==3.0.0
```

### GPU support not working

```
# Ensure CUDA is installed and install GPU version:
pip uninstall paddlepaddle
pip install paddlepaddle-gpu==3.0.0
# Set OCR_USE_GPU=true in .env
```

### File validation errors

The API uses content-based file type detection (magic bytes), not file extensions. Ensure your files are actually valid JPEG, PNG, or PDF files.

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request
