# backend/extraction/detectors.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from .types import FileType

logger = logging.getLogger(__name__)


class FileTypeDetector:
    """Utility class to detect and validate file types."""

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    PDF_EXTENSIONS = {".pdf"}
    EXCEL_EXTENSIONS = {".xlsx", ".xls"}

    @classmethod
    def get_file_type(cls, file_path: Union[str, Path]) -> FileType:
        """Determine file type from extension."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension in cls.IMAGE_EXTENSIONS:
            return FileType.IMAGE
        if extension in cls.PDF_EXTENSIONS:
            return FileType.PDF
        if extension in cls.EXCEL_EXTENSIONS:
            return FileType.EXCEL

        raise ValueError(f"Unsupported file type: {extension}")

    @classmethod
    def validate_file(cls, file_path: Union[str, Path]) -> Path:
        """Validate file exists and return Path object."""
        if not file_path:
            raise ValueError("file_path must be provided")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.debug("Validated file path: %s", path)
        return path
