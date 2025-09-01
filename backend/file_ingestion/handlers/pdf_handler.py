# backend/file_ingestion/handlers/pdf_handler.py
from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List
from pdf2image import convert_from_path
from PIL import Image
import logging

from backend.schemas.ingest import PageMetadata
from backend.utils.helpers import ensure_dir, resize_img, save_jpeg
from backend.utils.trackers import log_processing_time
from backend.utils.storage_paths import page_image_key, ensure_parent_dir

logger = logging.getLogger(__name__)


class PDFHandler:
    def __init__(self, img_pages_dir: Path, dpi: int, max_side: int, jpeg_quality: int, threads: int | None, poppler_path: str | None):
        self.img_pages_dir = Path(img_pages_dir)
        self.dpi = dpi
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality
        self.threads = threads
        self.poppler_path = poppler_path
        ensure_dir(self.img_pages_dir)

    @log_processing_time
    def handle(self, pdf_path: Path, job_id: str) -> List[PageMetadata]:
        pil_pages = convert_from_path(
            pdf_path.as_posix(),
            dpi=self.dpi,
            poppler_path=self.poppler_path,
        )
        pages: List[PageMetadata] = []

        def _process_one(idx_img):
            idx, img = idx_img
            try:
                resized = resize_img(img, size=self.max_side)
            except Exception:
                resized = img.copy()
                resized.thumbnail((self.max_side, self.max_side))

            # jobs/<job_id>/pages/0000.jpeg
            storage_key = page_image_key(job_id, idx, ext="jpeg")
            out_path = ensure_parent_dir(storage_key)
            save_jpeg(resized, out_path, quality=self.jpeg_quality)
            return PageMetadata(index=idx, image=storage_key)

        work = list(enumerate(pil_pages))
        max_workers = self.threads or min(32, os.cpu_count() or 8)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_process_one, wi) for wi in work]
            for f in as_completed(futures):
                pages.append(f.result())

        pages.sort(key=lambda m: m.index)
        logger.info("PDF pages processed: %d", len(pages))
        return pages
