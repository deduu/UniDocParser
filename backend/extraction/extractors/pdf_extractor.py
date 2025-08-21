# backend/extraction/extractors/pdf_extractor.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List

from ..base import BaseExtractor
import backend.utils.unstructured_extractor_helpers as helpers

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extractor for PDF files."""

    def extract(self, file_path: Path) -> List[Any]:
        """Extract elements from PDF file."""
        from unstructured.partition.pdf import partition_pdf

        logger.info("Partitioning PDF: %s", file_path)
        raw_elements = partition_pdf(
            filename=str(file_path),
             strategy="hi_res",                         # required for model-based (GPU-capable) path
            hi_res_model_name="yolox",
            extract_images_in_pdf=self.config.extract_images_in_pdf,
            extract_image_block_to_payload=self.config.extract_image_block_to_payload,
            extract_image_block_output_dir=self._get_output_directory(file_path),
            infer_table_structure=self.config.infer_table_structure,
            languages=self.config.languages,
        )
        # Normalize/split into per-page lists if your helpers provide that
        return helpers.split_elements(raw_elements)
