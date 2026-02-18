"""API route handlers for document extraction.

Provides endpoints for health checks and structured data extraction from documents.
"""

import io
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image

from app.config import settings
from app.schemas.request import (
    ErrorResponse,
    ExtractionRequest,
    ExtractionResponse,
    HealthResponse,
)
from app.services.layout_service import LayoutService
from app.services.llm_service import get_llm_service
from app.services.ocr_service import OCRService
from app.utils.validators import FileValidator

logger = logging.getLogger(__name__)

router = APIRouter()

_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check if the API is running and get configuration info",
)
async def health_check() -> HealthResponse:
    """Check API health and return service information.

    Returns:
        Health response with service status and configuration.
    """
    uptime = time.time() - _start_time

    return HealthResponse(
        status="healthy",
        service="ocrion",
        version="1.0.0",
        model=settings.model_name,
        ocr_gpu=settings.ocr_use_gpu,
        uptime_seconds=uptime,
    )


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    summary="Extract structured data from document image",
    description="Upload a document image and schema to extract structured data",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Processing error"},
    },
)
async def extract_data(
    file: UploadFile = File(..., description="Document image (JPG, PNG, PDF)"),
    schema: str = Form(..., description="JSON schema for extraction"),
) -> JSONResponse:
    """Extract structured data from document image using OCR and LLM.

    Processes the uploaded document through OCR, layout analysis, and LLM extraction
    to produce structured data matching the provided schema.

    Args:
        file: Uploaded document image file.
        schema: JSON string defining extraction schema (field_name -> description).

    Returns:
        JSON response with extracted data and processing metadata.

    Raises:
        HTTPException: If validation or processing fails at any stage.
    """
    stage = "file_validation"
    try:
        stage = "file_validation"
        file_content = await file.read()

        is_valid, error_msg = FileValidator.validate_file(file_content, file.filename)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        stage = "schema_validation"
        try:
            schema_data = json.loads(schema)
            schema_request = ExtractionRequest(schema_definition=schema_data)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schema JSON: {e!s}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Schema validation error: {e!s}",
            ) from e

        stage = "image_loading"
        try:
            image = Image.open(io.BytesIO(file_content))

            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            elif image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            image_width, image_height = image.size
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to load image: {e!s}",
            ) from e

        stage = "ocr"
        pipeline_start = time.time()
        ocr_start = time.time()

        try:
            ocr_results = OCRService.extract_text(image)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR processing failed: {e!s}",
            ) from e

        ocr_time = time.time() - ocr_start

        if not ocr_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text detected in the uploaded image",
            )

        stage = "layout_analysis"
        layout_start = time.time()

        try:
            layout_blocks = LayoutService.order_blocks(
                ocr_results, image_width, image_height
            )
            ordered_text = LayoutService.combine_text(layout_blocks)
        except Exception as e:
            logger.warning(f"Layout analysis failed, using raw OCR: {e}")
            ordered_text = " ".join(r.text for r in ocr_results)
            layout_blocks = []

        layout_time = time.time() - layout_start

        stage = "llm_extraction"
        llm_start = time.time()

        try:
            llm_service = get_llm_service()
            extracted_data = await llm_service.extract_with_retry(
                schema_request.schema_definition, ordered_text
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM extraction failed: {e!s}",
            ) from e

        llm_time = time.time() - llm_start
        pipeline_time = time.time() - pipeline_start

        metadata: dict[str, Any] = {
            "processing_time_seconds": round(pipeline_time, 3),
            "ocr_time_seconds": round(ocr_time, 3),
            "layout_time_seconds": round(layout_time, 3),
            "llm_time_seconds": round(llm_time, 3),
            "ocr_regions_detected": len(ocr_results),
            "layout_blocks": len(layout_blocks),
            "schema_fields": list(schema_request.schema_definition.keys()),
            "image_size": {"width": image_width, "height": image_height},
            "model": settings.model_name,
        }

        response = ExtractionResponse(
            success=True, data=extracted_data, metadata=metadata
        )

        logger.info(
            f"Extraction completed in {pipeline_time:.2f}s: "
            f"{len(ocr_results)} OCR regions, {len(extracted_data)} fields extracted"
        )

        return JSONResponse(
            content=response.model_dump(), status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error at stage '{stage}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed at stage '{stage}': {e!s}",
        ) from e
