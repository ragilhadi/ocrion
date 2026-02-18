"""OCR service using PaddleOCR for text extraction.

Provides singleton OCR service for extracting text and bounding boxes from images.
"""

import logging
from dataclasses import dataclass

import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

from app.schemas.request import OCRResult

logger = logging.getLogger(__name__)


@dataclass
class _OCRInstance:
    """Singleton wrapper for PaddleOCR instance.

    Ensures only one PaddleOCR instance is created and shared across requests.
    """

    instance: PaddleOCR | None = None
    initialized: bool = False

    def initialize(self) -> None:
        """Initialize PaddleOCR with configuration from settings.

        Raises:
            Exception: If PaddleOCR initialization fails.
        """
        if self.initialized:
            return

        try:
            logger.info("Initializing PaddleOCR ")
            self.instance = PaddleOCR(
                lang="en",
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=True,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                show_log=False,
            )
            self.initialized = True
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise


_ocr_instance = _OCRInstance()


class OCRService:
    """Singleton service for OCR operations using PaddleOCR."""

    @staticmethod
    def get_instance() -> PaddleOCR:
        """Get or initialize the PaddleOCR singleton instance.

        Returns:
            Initialized PaddleOCR instance.

        Raises:
            Exception: If initialization fails.
        """
        if not _ocr_instance.initialized:
            _ocr_instance.initialize()
        return _ocr_instance.instance

    @staticmethod
    def extract_text(image: Image.Image) -> list[OCRResult]:
        """Extract text and bounding boxes from an image.

        Args:
            image: PIL Image object to process.

        Returns:
            List of OCRResult objects with text, bounding boxes, and confidence scores.

        Raises:
            Exception: If OCR processing fails.
        """
        ocr = OCRService.get_instance()

        try:
            img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            result = ocr.ocr(img_array, cls=True)

            if not result or not result[0]:
                logger.warning("No text detected in image")
                return []

            ocr_results = []
            for line in result[0]:
                bbox_points = line[0]
                text_info = line[1]
                text = text_info[0]
                confidence = float(text_info[1])

                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]
                x1, y1 = min(x_coords), min(y_coords)
                x2, y2 = max(x_coords), max(y_coords)

                ocr_results.append(
                    OCRResult(
                        text=text.strip(), bbox=[x1, y1, x2, y2], confidence=confidence
                    )
                )

            logger.info(f"Extracted {len(ocr_results)} text regions")
            return ocr_results

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise


def initialize_ocr() -> None:
    """Initialize OCR service on application startup.

    Raises:
        Exception: If initialization fails.
    """
    logger.info("Initializing OCR service...")
    OCRService.get_instance()
    logger.info("OCR service ready")
