# backend/extraction/extractors/excel_extractor.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List

from ..base import BaseExtractor
import backend.utils.unstructured_extractor_helpers as helpers

logger = logging.getLogger(__name__)


class ExcelExtractor(BaseExtractor):
    """Extractor for Excel files."""

    def extract(self, file_path: Path) -> List[Any]:
        """Extract elements from Excel file."""
        from unstructured.partition.xlsx import partition_xlsx

        logger.info("Partitioning Excel: %s", file_path)
        raw_elements = partition_xlsx(
            filename=str(file_path),
            extract_images_in_pdf=self.config.extract_images_in_pdf,
            extract_image_block_to_payload=self.config.extract_image_block_to_payload,
            extract_image_block_output_dir=self._get_output_directory(file_path),
            infer_table_structure=self.config.infer_table_structure,
            languages=self.config.languages,
        )
        return helpers.split_elements(raw_elements)
