# Quick Start Guide

## Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# 4. Verify installation
python test_setup.py
```

## Running the Server

### Development Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode
```bash
./start.sh
```

## Testing

### 1. Create Test Image
```bash
python create_test_image.py
```

### 2. Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### 3. Test Extraction
```bash
curl -X POST "http://localhost:8000/extract" \
  -F "file=@test_invoice.png" \
  -F 'schema={"invoice_number": "Invoice number", "total": "Total amount", "date": "Invoice date", "vendor": "Company name"}'
```

### 4. Run Tests
```bash
pytest
```

## API Endpoints

### POST /extract
Extract structured data from document images.

**Request:**
- `file`: Image file (JPG, PNG, PDF) - max 5MB
- `schema`: JSON string with field definitions

**Response:**
```json
{
  "success": true,
  "data": {
    "field1": "value1",
    "field2": "value2"
  },
  "metadata": {
    "processing_time_seconds": 2.5,
    "ocr_regions_detected": 45
  }
}
```

### GET /health
Check API health.

## Troubleshooting

**PaddleOCR download takes long on first run:**
- First run downloads models (~50MB) - be patient
- Models are cached after first download

**GPU support:**
- Install: `pip install paddlepaddle-gpu==3.0.0`
- Set: `OCR_USE_GPU=true` in .env

**File type errors:**
- Validation is content-based, not extension-based
- Ensure files are actually valid JPEG/PNG/PDF

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application entry |
| `app/config.py` | Configuration management |
| `app/api/routes.py` | API endpoints |
| `app/services/ocr_service.py` | PaddleOCR wrapper |
| `app/services/layout_service.py` | Spatial text ordering |
| `app/services/llm_service.py` | OpenRouter LLM integration |
| `requirements.txt` | Dependencies |
| `start.sh` | Production startup script |
