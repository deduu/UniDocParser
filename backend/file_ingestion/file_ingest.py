# backend/file_ingestion/file_ingest.py
from __future__ import annotations
from pathlib import Path
from typing import Callable, Dict, List, Optional
import logging
import time
import hashlib

from backend.core.config import settings
from backend.schemas.ingest import PageMetadata
from backend.file_ingestion.handlers.pdf_handler import PDFHandler
from backend.file_ingestion.handlers.image_handler import ImageHandler
from backend.file_ingestion.handlers.excel_handler import ExcelHandler

logger = logging.getLogger(__name__)

HandlerFn = Callable[[Path, str], List[PageMetadata]]


def _adhoc_job_id(for_path: Path) -> str:
    # deterministic-ish but time-salted key
    h = hashlib.sha1(
        f"{for_path.resolve()}::{time.time()}".encode()).hexdigest()[:12]
    return f"adhoc-{h}"


class FileIngestor:
    def __init__(self):
        self._handlers: Dict[str, HandlerFn] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        pdf = PDFHandler(
            img_pages_dir=settings.IMG_PAGES_DIR,
            dpi=settings.PDF_DPI,
            max_side=settings.PDF_MAX_SIDE,
            jpeg_quality=settings.JPEG_QUALITY,
            threads=None,
            poppler_path=settings.POPPLER_PATH,
        )
        image = ImageHandler(
            img_pages_dir=settings.IMG_PAGES_DIR,
            max_side=settings.IMG_MAX_SIDE,
            jpeg_quality=settings.JPEG_QUALITY,
        )
        excel = ExcelHandler(
            img_pages_dir=settings.IMG_PAGES_DIR,
            max_side=settings.IMG_MAX_SIDE,
            jpeg_quality=settings.JPEG_QUALITY,
        )
        for ext in [".pdf"]:
            self._handlers[ext] = pdf.handle
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            self._handlers[ext] = image.handle
        for ext in [".xls", ".xlsx"]:
            self._handlers[ext] = excel.handle

    def handle_file(self, file_path: str | Path, job_id: Optional[str] = None) -> List[PageMetadata]:
        p = Path(file_path)
        if not p.exists():
            logger.error("File not found: %s", p)
            return []
        handler = self._handlers.get(p.suffix.lower())
        if not handler:
            logger.warning("Unsupported file type: %s", p.suffix)
            return []
        concrete_job_id = job_id or _adhoc_job_id(p)
        try:
            return handler(p, concrete_job_id)
        except Exception as e:
            logger.exception("Error while handling %s: %s", p, e)
            return []


ingest = FileIngestor()
