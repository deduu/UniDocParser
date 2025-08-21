# backend/extraction/factory.py
from __future__ import annotations

from typing import Dict, Type

from .types import FileType
from .config import ExtractionConfig
from .base import BaseExtractor
from .extractors.image_extractor import ImageExtractor
from .extractors.pdf_extractor import PDFExtractor
from .extractors.excel_extractor import ExcelExtractor


class ExtractorFactory:
    """Factory class to create appropriate extractors."""

    _extractors: Dict[FileType, Type[BaseExtractor]] = {
        FileType.IMAGE: ImageExtractor,
        FileType.PDF: PDFExtractor,
        FileType.EXCEL: ExcelExtractor,
    }

    @classmethod
    def create_extractor(cls, file_type: FileType, config: ExtractionConfig) -> BaseExtractor:
        """Create appropriate extractor for file type."""
        if file_type not in cls._extractors:
            raise ValueError(f"No extractor available for file type: {file_type}")
        return cls._extractors[file_type](config)

    @classmethod
    def register(cls, file_type: FileType, extractor_cls: Type[BaseExtractor]) -> None:
        """Optional: register/override an extractor at runtime."""
        cls._extractors[file_type] = extractor_cls
