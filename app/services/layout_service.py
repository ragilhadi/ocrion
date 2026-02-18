"""Layout analysis service for spatial text ordering.

Orders OCR text blocks in reading order (top-to-bottom, left-to-right) using
spatial analysis and row grouping.
"""

import logging
from collections import defaultdict

import numpy as np

from app.schemas.request import LayoutBlock, OCRResult

logger = logging.getLogger(__name__)


class LayoutService:
    """Service for spatial ordering of OCR text blocks."""

    @staticmethod
    def order_blocks(
        ocr_results: list[OCRResult], image_width: int, image_height: int
    ) -> list[LayoutBlock]:
        """Order OCR blocks spatially in reading order.

        Groups blocks into rows using median line height, then sorts rows
        top-to-bottom and blocks within rows left-to-right.

        Args:
            ocr_results: List of OCR results with bounding boxes.
            image_width: Image width in pixels.
            image_height: Image height in pixels.

        Returns:
            List of LayoutBlocks sorted in reading order.
        """
        if not ocr_results:
            return []

        try:
            normalized_blocks = LayoutService._normalize_bboxes(
                ocr_results, image_width, image_height
            )

            heights = [b.bbox[3] - b.bbox[1] for b in normalized_blocks]
            median_height = float(np.median(heights)) if heights else 50.0

            rows = LayoutService._group_into_rows(normalized_blocks, median_height)

            sorted_rows = sorted(rows, key=lambda r: r["y_center"])

            ordered_blocks = []
            for row in sorted_rows:
                row_blocks = sorted(row["blocks"], key=lambda b: b.bbox[0])
                ordered_blocks.extend(row_blocks)

            layout_blocks = [
                LayoutBlock(
                    text=block.text, bbox=block.bbox, page_num=1, block_type="text"
                )
                for block in ordered_blocks
            ]

            logger.info(f"Ordered {len(layout_blocks)} blocks into {len(rows)} rows")
            return layout_blocks

        except Exception as e:
            logger.error(f"Layout analysis failed: {e}")
            return [
                LayoutBlock(text=r.text, bbox=r.bbox, page_num=1, block_type="text")
                for r in ocr_results
            ]

    @staticmethod
    def _normalize_bboxes(
        ocr_results: list[OCRResult], image_width: int, image_height: int
    ) -> list[OCRResult]:
        """Normalize bounding boxes to [0, 1000] coordinate space.

        Args:
            ocr_results: List of OCR results with pixel coordinates.
            image_width: Image width in pixels.
            image_height: Image height in pixels.

        Returns:
            List of OCR results with normalized coordinates.
        """
        normalized = []
        for result in ocr_results:
            x1, y1, x2, y2 = result.bbox
            norm_x1 = (x1 / image_width) * 1000
            norm_y1 = (y1 / image_height) * 1000
            norm_x2 = (x2 / image_width) * 1000
            norm_y2 = (y2 / image_height) * 1000
            normalized.append(
                OCRResult(
                    text=result.text,
                    bbox=[norm_x1, norm_y1, norm_x2, norm_y2],
                    confidence=result.confidence,
                )
            )
        return normalized

    @staticmethod
    def _group_into_rows(
        blocks: list[OCRResult], median_height: float, tolerance_factor: float = 0.5
    ) -> list[dict[str, float | list[OCRResult]]]:
        """Group blocks into rows based on vertical proximity.

        Args:
            blocks: List of OCR blocks with normalized coordinates.
            median_height: Median line height for threshold calculation.
            tolerance_factor: Tolerance as fraction of median height.

        Returns:
            List of row dictionaries with y_center and blocks.
        """
        tolerance = median_height * tolerance_factor
        rows: defaultdict[float, list[OCRResult]] = defaultdict(list)

        for block in blocks:
            y_center = (block.bbox[1] + block.bbox[3]) / 2

            matched_row = None
            for row_y_center in rows:
                if abs(y_center - row_y_center) <= tolerance:
                    matched_row = row_y_center
                    break

            if matched_row is not None:
                rows[matched_row].append(block)
            else:
                rows[y_center].append(block)

        return [{"y_center": y, "blocks": blocks} for y, blocks in rows.items()]

    @staticmethod
    def combine_text(blocks: list[LayoutBlock]) -> str:
        """Combine ordered blocks into readable text with intelligent spacing.

        Args:
            blocks: List of layout blocks in reading order.

        Returns:
            Combined text with appropriate line breaks and spacing.
        """
        if not blocks:
            return ""

        try:
            heights = [b.bbox[3] - b.bbox[1] for b in blocks]
            median_height = float(np.median(heights)) if heights else 50.0

            lines = []
            current_line = []
            last_y1: float | None = None

            for block in blocks:
                y1 = block.bbox[1]

                if last_y1 is not None:
                    y_distance = y1 - last_y1
                    if y_distance > median_height * 0.8:
                        if current_line:
                            lines.append(" ".join(current_line))
                            current_line = []

                current_line.append(block.text)
                last_y1 = y1

            if current_line:
                lines.append(" ".join(current_line))

            result = "\n".join(lines)
            logger.info(f"Combined {len(blocks)} blocks into {len(lines)} lines")
            return result

        except Exception as e:
            logger.error(f"Text combination failed: {e}")
            return " ".join(b.text for b in blocks)
