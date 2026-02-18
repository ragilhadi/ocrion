"""File validation utilities.

Provides validation for uploaded files including type and size checks.
"""

import magic

from app.config import settings


class FileValidator:
    """Validates uploaded files for type and size constraints."""

    ALLOWED_MIME_TYPES = set(settings.allowed_mime_types)
    MAX_SIZE = settings.max_upload_size

    @staticmethod
    def validate_file(file_content: bytes, filename: str) -> tuple[bool, str | None]:
        """Validate file type and size constraints.

        Uses magic bytes for content-based type detection rather than
        relying on file extensions.

        Args:
            file_content: Raw file bytes.
            filename: Original filename (for logging/error messages).

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        if len(file_content) > FileValidator.MAX_SIZE:
            size_mb = len(file_content) / (1024 * 1024)
            max_mb = FileValidator.MAX_SIZE / (1024 * 1024)
            return (
                False,
                f"File size {size_mb:.2f}MB exceeds maximum {max_mb}MB",
            )

        try:
            mime = magic.from_buffer(file_content, mime=True)
        except Exception as e:
            return False, f"Could not determine file type: {e!s}"

        if mime not in FileValidator.ALLOWED_MIME_TYPES:
            allowed = ", ".join(sorted(FileValidator.ALLOWED_MIME_TYPES))
            return False, f"File type {mime} not allowed. Allowed: {allowed}"

        return True, None

    @staticmethod
    def is_pdf(file_content: bytes) -> bool:
        """Check if file content is a PDF document.

        Args:
            file_content: Raw file bytes.

        Returns:
            True if file is a PDF, False otherwise.
        """
        try:
            mime = magic.from_buffer(file_content, mime=True)
            return mime == "application/pdf"
        except Exception:
            return False
