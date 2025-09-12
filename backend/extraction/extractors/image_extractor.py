# # backend/extraction/extractors/image_extractor.py
# from __future__ import annotations

# import logging
# from pathlib import Path
# from typing import Any, List

# from ..base import BaseExtractor

# logger = logging.getLogger(__name__)


# class ImageExtractor(BaseExtractor):
#     """Extractor for image files."""

#     def extract(self, file_path: Path) -> List[Any]:
#         """Extract elements from image file."""
#         # Local import to avoid hard dependency at module import time
#         from unstructured.partition.image import partition_image

#         logger.info("Partitioning image: %s", file_path)
#         return partition_image(
#             filename=str(file_path),
#             extract_images_in_pdf=self.config.extract_images_in_pdf,
#             extract_image_block_to_payload=self.config.extract_image_block_to_payload,
#             extract_image_block_output_dir=self._get_output_directory(file_path),
#             infer_table_structure=self.config.infer_table_structure,
#             languages=self.config.languages,
#         )
# backend/extraction/extractors/image_extractor.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Tuple, Dict

from ..base import BaseExtractor
import backend.utils.unstructured_extractor_helpers as helpers

logger = logging.getLogger(__name__)


class ImageExtractor(BaseExtractor):
    """Extractor for image files."""

    def extract(self, file_path: Path) -> Tuple[List[List[Any]], Dict[int, dict]]:
        """Extract elements from image file, normalized like PDF:
        returns (per_page_elements, page_meta).
        """
        # Local import to avoid hard dependency at module import time
        from unstructured.partition.image import partition_image

        logger.info("Partitioning image: %s", file_path)
        raw_elements = partition_image(
            filename=str(file_path),
            # keep the same knobs you use for PDF so pipeline behaves consistently
            extract_images_in_pdf=self.config.extract_images_in_pdf,
            extract_image_block_to_payload=self.config.extract_image_block_to_payload,
            extract_image_block_output_dir=self._get_output_directory(
                file_path),
            infer_table_structure=self.config.infer_table_structure,
            languages=self.config.languages,
        )

        # Ensure a page_number exists (images are effectively single-page = 1)
        for el in raw_elements:
            if not getattr(el.metadata, "page_number", None):
                try:
                    el.metadata.page_number = 1
                except Exception:
                    # metadata object might be frozen; that's OK if helpers.split_elements
                    # only reads the attribute when present on some elements
                    pass

        # Build page_meta similarly to PDFExtractor
        page_meta: Dict[int, dict] = {}
        for el in raw_elements:
            coords = getattr(el.metadata, "coordinates", None)
            page_num = getattr(el.metadata, "page_number", 1)
            if coords and getattr(coords, "system", None):
                system = coords.system
                w = getattr(system, "width", None)
                h = getattr(system, "height", None)
                if w and h and page_num not in page_meta:
                    page_meta[page_num] = {
                        "coord_width": float(w),
                        "coord_height": float(h),
                    }
                    logger.debug(
                        f"[extract:image] Page {page_num} size={w}x{h}")

        logger.info(
            f"[extract:image] page_meta = {page_meta or {1: {'coord_width': 0, 'coord_height': 0}}}")

        # Split into per-page lists just like PDF
        per_page_elements = helpers.split_elements(raw_elements)

        return per_page_elements, page_meta
