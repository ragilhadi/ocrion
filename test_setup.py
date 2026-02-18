#!/usr/bin/env python3
"""Quick validation script to check if all dependencies can be imported."""
import sys

print("Checking Python imports...")
print("-" * 50)

checks = []

# Check FastAPI
try:
    from fastapi import FastAPI
    checks.append(("FastAPI", True))
except ImportError as e:
    checks.append(("FastAPI", False, str(e)))

# Check Pydantic
try:
    from pydantic import BaseModel
    checks.append(("Pydantic", True))
except ImportError as e:
    checks.append(("Pydantic", False, str(e)))

# Check PaddleOCR
try:
    from paddleocr import PaddleOCR
    checks.append(("PaddleOCR", True))
except ImportError as e:
    checks.append(("PaddleOCR", False, str(e)))

# Check OpenAI
try:
    from openai import OpenAI
    checks.append(("OpenAI", True))
except ImportError as e:
    checks.append(("OpenAI", False, str(e)))

# Check PIL
try:
    from PIL import Image
    checks.append(("Pillow", True))
except ImportError as e:
    checks.append(("Pillow", False, str(e)))

# Check python-magic
try:
    import magic
    checks.append(("python-magic", True))
except ImportError as e:
    checks.append(("python-magic", False, str(e)))

# Print results
for check in checks:
    name = check[0]
    status = check[1]
    if status:
        print(f"✓ {name}")
    else:
        error = check[2] if len(check) > 2 else "Unknown error"
        print(f"✗ {name}: {error}")

print("-" * 50)

# Check app imports
print("\nChecking app imports...")
print("-" * 50)

app_checks = [
    ("app.config", "from app.config import settings"),
    ("app.schemas.request", "from app.schemas.request import ExtractionRequest"),
    ("app.services.ocr_service", "from app.services.ocr_service import OCRService"),
    ("app.services.layout_service", "from app.services.layout_service import LayoutService"),
    ("app.services.llm_service", "from app.services.llm_service import LLMService"),
    ("app.services.prompt_builder", "from app.services.prompt_builder import PromptBuilder"),
    ("app.utils.validators", "from app.utils.validators import FileValidator"),
    ("app.api.routes", "from app.api.routes import router"),
    ("app.main", "from app.main import app"),
]

for name, import_stmt in app_checks:
    try:
        exec(import_stmt)
        print(f"✓ {name}")
    except Exception as e:
        print(f"✗ {name}: {e}")

print("-" * 50)

# Check environment variables
print("\nChecking environment...")
print("-" * 50)

import os
env_vars = ["OPENROUTER_API_KEY", "MODEL_NAME", "API_PORT", "OCR_USE_GPU"]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask API keys
        if "KEY" in var or "SECRET" in var:
            display = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        else:
            display = value
        print(f"✓ {var}={display}")
    else:
        print(f"⚠ {var} not set (will use default)")

print("-" * 50)

# Summary
all_good = all(c[1] for c in checks)
if all_good:
    print("\n✓ All dependencies installed successfully!")
    print("\nNext steps:")
    print("1. Set OPENROUTER_API_KEY in .env")
    print("2. Run: ./start.sh")
    print("3. Or for development: uvicorn app.main:app --reload")
    sys.exit(0)
else:
    print("\n✗ Some dependencies are missing.")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)
