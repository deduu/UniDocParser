# backend/extraction/extractors/image_extractor.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List

from ..base import BaseExtractor

logger = logging.getLogger(__name__)


class ImageExtractor(BaseExtractor):
    """Extractor for image files."""

    def extract(self, file_path: Path) -> List[Any]:
        """Extract elements from image file."""
        # Local import to avoid hard dependency at module import time
        from unstructured.partition.image import partition_image

        logger.info("Partitioning image: %s", file_path)
        return partition_image(
            filename=str(file_path),
            extract_images_in_pdf=self.config.extract_images_in_pdf,
            extract_image_block_to_payload=self.config.extract_image_block_to_payload,
            extract_image_block_output_dir=self._get_output_directory(file_path),
            infer_table_structure=self.config.infer_table_structure,
            languages=self.config.languages,
        )
