"""FastAPI application entry point.

Provides OCR-based structured data extraction API with health checks,
error handling, and service initialization.
"""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.config import settings
from app.services.llm_service import initialize_llm
from app.services.ocr_service import initialize_ocr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("ocrion.log")],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    Handles service initialization on startup and cleanup on shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        None during application runtime.

    Raises:
        Exception: If service initialization fails.
    """
    logger.info("=" * 60)
    logger.info("Starting OCRion API")
    logger.info("=" * 60)

    try:
        logger.info("Initializing OCR service...")
        initialize_ocr()

        logger.info("Initializing LLM service...")
        await initialize_llm()

        logger.info("All services initialized successfully")
        logger.info(f"Model: {settings.model_name}")
        logger.info(
            f"Max upload size: {settings.max_upload_size / 1024 / 1024:.2f}MB"
        )
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    logger.info("Shutting down OCRion API")


app = FastAPI(
    title="OCRion API",
    description="OCR → LayoutLM → LLM Structured Extraction API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions with structured error responses.

    Args:
        request: Incoming request that caused the exception.
        exc: HTTP exception raised.

    Returns:
        JSON response with error details.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": "http_error",
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors.

    Args:
        request: Incoming request that failed validation.
        exc: Validation error raised.

    Returns:
        JSON response with validation error details.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "validation_error",
            "detail": exc.errors(),
            "status_code": 422,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions.

    Args:
        request: Incoming request that caused the exception.
        exc: Unhandled exception raised.

    Returns:
        JSON response with error details.
    """
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "internal_error",
            "detail": str(exc),
            "status_code": 500,
        },
    )


app.include_router(router, tags=["extraction"])


@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str | dict[str, str] | bool]:
    """Provide API information and available endpoints.

    Returns:
        Dictionary with service metadata and endpoint information.
    """
    return {
        "service": "OCRion API",
        "version": "1.0.0",
        "description": "OCR → LayoutLM → LLM Structured Extraction",
        "endpoints": {"health": "/health", "extract": "/extract", "docs": "/docs"},
        "model": settings.model_name,
        "ocr_gpu": settings.ocr_use_gpu,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=settings.api_port, reload=True
    )
