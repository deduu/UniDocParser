# backend/extraction/processors/element_processor.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import markdownify

from ..config import ExtractionConfig
from ..types import FigureData
from backend.utils.helpers import resize_img_from_path, image_to_base64
import backend.utils.unstructured_extractor_helpers as helpers

logger = logging.getLogger(__name__)


class ElementProcessor:
    """Process extracted elements and convert to structured metadata."""

    def __init__(self, config: ExtractionConfig):
        self.config = config

    def process_elements(self, elements: List[Any], page_num: int) -> Tuple[List[Dict], List[FigureData]]:
        """Process elements and extract metadata."""
        element_metadata: List[Dict] = []
        figure_list: List[FigureData] = []
        temp_table = ""
        min_counter = 0

        for i, element in enumerate(elements):
            print(f"element content: {element}")
            try:
                metadata, figure = self._process_single_element(
                    element, i, min_counter, temp_table, page_num
                )

                if metadata:
                    element_metadata.append(metadata)
                if figure:
                    figure_list.append(figure)

                # You can adjust counters here for tables if needed later
            except Exception as e:
                logger.error(
                    "Error processing element %s on page %s: %s", i, page_num, e, exc_info=True)
                continue

        return element_metadata, figure_list

    # ─────────────────────────────────────────────────────────────────────────────

    def _process_single_element(
        self,
        element: Any,
        idx: int,
        min_counter: int,
        temp_table: str,
        page_num: int,
    ) -> Tuple[Optional[Dict], Optional[FigureData]]:
        """Process a single element."""
        unstructured_element = {}
        try:
            # type: ignore[attr-defined]
            unstructured_element = element.metadata.to_dict()
            logger.info(f"Unstructured element: {unstructured_element}")
        except Exception:
            # Fallback if object doesn't have metadata; treat as text
            pass

        element_bbox = self._extract_bbox(unstructured_element)

        if self._is_image_element(element):
            return self._process_image_element(element, unstructured_element, idx, min_counter, element_bbox, page_num)
        if self._is_table_element(element):
            return self._process_table_element(element, unstructured_element, idx, min_counter, temp_table, element_bbox)
        return self._process_text_element(element, idx, min_counter, element_bbox)

    def _extract_bbox(self, metadata: Dict) -> Optional[Dict]:
        """Extract bounding box from metadata."""
        try:
            if "coordinates" in metadata and metadata["coordinates"] and "points" in metadata["coordinates"]:
                return helpers.extract_bbox(metadata["coordinates"]["points"])
        except Exception:
            pass
        return None

    def _is_image_element(self, element: Any) -> bool:
        """Check if element is an image."""
        return "unstructured.documents.elements.Image" in str(type(element))

    def _is_table_element(self, element: Any) -> bool:
        """Check if element is a table."""
        return "unstructured.documents.elements.Table" in str(type(element))

    # ─────────────────────────────────────────────────────────────────────────────

    def _process_image_element(
        self,
        element: Any,
        metadata: Dict,
        idx: int,
        min_counter: int,
        bbox: Optional[Dict],
        page_num: int,
    ) -> Tuple[Dict, FigureData]:
        """Process image element."""
        image_path = metadata.get("image_path")
        pil_image = None
        try:
            if image_path:
                pil_image = resize_img_from_path(
                    image_path, size=self.config.image_resize)
        except Exception as e:
            logger.warning(
                "Failed to open/resize image at %s: %s", image_path, e)

        element_metadata = {
            "idx": idx - min_counter,
            "type": "image",
            "bbox": bbox,
            "text": "",
            "image_metadata": {
                "image_type": "",
                "caption": "",
                "description": "",
                "ocr_string": str(element),
                "image_base64": image_to_base64(
                    image_path=image_path, quality=self.config.image_quality
                ) if image_path else "",
            },
        }

        figure_data = FigureData(
            page_num=page_num,
            idx=idx - min_counter,
            pil_image=pil_image,
            generated_text="",
        )
        return element_metadata, figure_data

    def _process_table_element(
        self,
        element: Any,
        metadata: Dict,
        idx: int,
        min_counter: int,
        temp_table: str,
        bbox: Optional[Dict],
    ) -> Tuple[Optional[Dict], None]:
        """Process table element."""
        try:
            html_text = metadata.get("text_as_html") or ""
            md_table = markdownify.markdownify(html_text)
            md_table = helpers.filter_table(md_table)
            table = helpers.format_table(md_table)
            if len(table) > 0:
                return {
                    "idx": idx - min_counter,
                    "type": "table",
                    "text": table,
                    "bbox": bbox,   # ✅ now included
                }, None
        except Exception as e:
            logger.debug("Failed to parse table element: %s", e)
        return None, None

    # def _process_table_element(
    #     self,
    #     element: Any,
    #     metadata: Dict,
    #     idx: int,
    #     min_counter: int,
    #     temp_table: str,
    # ) -> Tuple[Optional[Dict], None]:
    #     """Process table element."""
    #     try:
    #         html_text = metadata.get("text_as_html") or ""
    #         md_table = markdownify.markdownify(html_text)
    #         md_table = helpers.filter_table(md_table)
    #         table = helpers.format_table(md_table)
    #         if len(table) > 0:
    #             return {
    #                 "idx": idx - min_counter,
    #                 "type": "table",
    #                 "text": table,
    #             }, None
    #     except Exception as e:
    #         logger.debug("Failed to parse table element: %s", e)
    #     return None, None

    def _process_text_element(
        self,
        element: Any,
        idx: int,
        min_counter: int,
        bbox: Optional[Dict],
    ) -> Tuple[Dict, None]:
        """Process text element."""
        try:
            text = str(element)
        except Exception:
            text = ""
        return {
            "idx": idx - min_counter,
            "type": "text",
            "bbox": bbox,
            "text": text,
        }, None
