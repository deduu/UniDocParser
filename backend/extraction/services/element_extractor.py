# backend/extraction/services/element_extractor.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from backend.utils.safe_paths import ensure_parent_dir
from ..config import ExtractionConfig
from ..detectors import FileTypeDetector
from ..factory import ExtractorFactory
from ..processors import ElementProcessor
from ..types import FigureData

logger = logging.getLogger(__name__)


class DocumentElementExtractor:
    """Main class for document element extraction."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        self.processor = ElementProcessor(self.config)

    def extract_elements_from_file(self, file_path: Union[str, Path]) -> List[Any]:
        """Extract elements from a single file."""
        logger.info(f"Extracting elements from: {file_path}")

        # Validate file and detect type
        validated_path = FileTypeDetector.validate_file(file_path)
        file_type = FileTypeDetector.get_file_type(validated_path)

        logger.info(f"Detected file type: {file_type}")
        # Create appropriate extractor and extract elements
        extractor = ExtractorFactory.create_extractor(file_type, self.config)
        elements, meta = extractor.extract(validated_path)

        logger.info("Extracted %d elements from %s", len(elements), file_path)
        logger.info("[extract_file] meta keys: %s", list(
            meta.keys()) if isinstance(meta, dict) else type(meta))
        return elements, meta

    def extract_elements_from_pages(
        self, pages: List[Dict],
        file_path: Optional[Union[str, Path]] = None
    ) -> Tuple[List[Dict], List[FigureData]]:
        """Extract elements from multiple pages or a single file."""
        figure_list: List[FigureData] = []
        elements_per_page: List[List[Any]] = []
        page_meta_by_index: Dict[int, Dict] = {}

        logger.info("Extract elements path: %s", file_path)

        if not file_path:
            # Per-page images
            for i, page in enumerate(pages):
                img_ref = page.get("image")
                if img_ref:
                    elems, meta_dict = self.extract_elements_from_file(img_ref)
                    elements_per_page.append(elems)

                    # meta_dict is usually {1: {...}} for a single image
                    if isinstance(meta_dict, dict) and meta_dict:
                        # take the only entry (or the first)
                        first_meta = next(iter(meta_dict.values()))
                        page_meta_by_index[i] = {
                            "coord_width": float(first_meta.get("coord_width", 0) or 0),
                            "coord_height": float(first_meta.get("coord_height", 0) or 0),
                        }
                    logger.info("[per-image] page %d elems=%d meta=%s",
                                i, len(elems), page_meta_by_index.get(i))
                else:
                    elements_per_page.append([])
                    logger.warning("No image found for page %d", i)

        else:
            # Single file containing all pages
            all_elems, meta_dict = self.extract_elements_from_file(file_path)
            if all_elems and isinstance(all_elems[0], list):
                # already list-of-lists per page
                elements_per_page = all_elems
            else:
                # flat list -> assign to page 0 and empty for others
                elements_per_page = [all_elems] + [[]
                                                   for _ in range(len(pages) - 1)]

            # Map 1-based page numbers in meta → 0-based indices
            if isinstance(meta_dict, dict):
                for pnum, meta in meta_dict.items():
                    try:
                        idx = int(pnum) - 1
                    except Exception:
                        continue
                    if 0 <= idx < len(pages):
                        page_meta_by_index[idx] = {
                            "coord_width": float(meta.get("coord_width", 0) or 0),
                            "coord_height": float(meta.get("coord_height", 0) or 0),
                        }
            logger.info("[single-file] page_meta_by_index=%s",
                        page_meta_by_index)

        # Process & attach to Page dicts
        for i, page in enumerate(pages):
            elems = elements_per_page[i] if i < len(elements_per_page) else []
            page_elements, figures = self.processor.process_elements(
                elems, page_num=i)
            page["elements"] = page_elements

            meta = page_meta_by_index.get(i)
            if meta:
                page["coord_width"] = meta["coord_width"]
                page["coord_height"] = meta["coord_height"]

            figure_list.extend(figures)

        logger.info("Extracted %d figures from %d pages",
                    len(figure_list), len(pages))
        # Helpful verification logs (first 3 pages)
        for i, page in enumerate(pages[:3]):
            logger.info(
                "[attach] page %d elems=%d coord=(%s,%s)",
                i,
                len(page.get("elements", [])),
                page.get("coord_width"),
                page.get("coord_height"),
            )
        return pages, figure_list
        # else:
        #     # Extract from single file - NOTE: Original code has a logic issue here
        #     # It extracts once but tries to use elements[i] in the loop
        #     # We'll assume the single file extraction returns a list of page elements
        #     single_file_elements, page_meta = self.extract_elements_from_file(
        #         file_path)

        #     # If it's a list of lists (per page), use as is
        #     # If it's a flat list, we need to decide how to split it across pages
        #     if single_file_elements and isinstance(single_file_elements[0], list):
        #         elements = single_file_elements
        #     else:
        #         # For now, assign all elements to first page (may need adjustment based on actual use case)
        #         elements = [single_file_elements] + [[]
        #                                              for _ in range(len(pages) - 1)]

        # # Now process elements in alignment with pages (matching original logic)
        # for i, page in enumerate(pages):
        #     if i < len(elements):
        #         page_elements, figures = self.processor.process_elements(
        #             elements[i], page_num=i
        #         )
        #         page["elements"] = page_elements
        #         # unstructured is 1-based page numbers
        #         meta = page_meta.get(i+1)
        #         if meta:
        #             page["coord_width"] = meta["coord_width"]
        #             page["coord_height"] = meta["coord_height"]
        #         figure_list.extend(figures)
        #     else:
        #         # Handle missing elements appropriately
        #         page["elements"] = []
        #         logger.warning(f"No elements found for page index {i}")

        # logger.info(
        #     f"Extracted {len(figure_list)} figures from {len(pages)} pages")
        # return pages, figure_list

# Convenience functions for backward compatibility


def element_extractor(
    file_path: str, config: Optional[ExtractionConfig] = None
) -> Tuple[List[Any], Dict[int, Dict]]:
    extractor = DocumentElementExtractor(config)
    return extractor.extract_elements_from_file(file_path)


def extract_unstructured_elements(
    elements: List[Any], page_num: int, config: Optional[ExtractionConfig] = None
) -> Tuple[List[Dict], List[FigureData]]:
    processor = ElementProcessor(config or ExtractionConfig())
    return processor.process_elements(elements, page_num)


# def extract_elements(
#     pages: List[Dict], file_path: Optional[str] = None, config: Optional["ExtractionConfig"] = None
# ) -> Tuple[List[Dict], List["FigureData"]]:
#     figure_list: List["FigureData"] = []
#     elements_per_page: List[List[Any]] = []
#     page_meta_by_index: Dict[int, Dict] = {}

#     print("=" * 80)
#     print(
#         f"[extract_elements] Start - file_path: {file_path}, num_pages: {len(pages)}")
#     if config:
#         print(f"[extract_elements] Config: {config}")

#     if not file_path:
#         print("[extract_elements] Running per-page extraction (no global file_path).")
#         for i, page in enumerate(pages):
#             print(
#                 f"  -> Extracting elements from page index {i}, image: {page.get('image')}")
#             elems, meta_dict = element_extractor(
#                 file_path=ensure_parent_dir(page.get("image")), config=config)
#             print(
#                 f"     Returned elems type: {type(elems)}, len: {len(elems) if elems else 0}")
#             print(f"     Returned meta_dict: {meta_dict}")

#             elements_per_page.append(elems if elems else [])

#             if isinstance(meta_dict, dict) and meta_dict:
#                 first_meta = next(iter(meta_dict.values()))
#                 page_meta_by_index[i] = {
#                     "coord_width": float(first_meta.get("coord_width", 0) or 0),
#                     "coord_height": float(first_meta.get("coord_height", 0) or 0),
#                 }
#                 print(f"     Saved meta for page {i}: {page_meta_by_index[i]}")
#     else:
#         print("[extract_elements] Running global extraction (file_path present).")
#         all_elems, meta_dict = element_extractor(
#             file_path=file_path, config=config)
#         print(
#             f"  -> all_elems type: {type(all_elems)}, sample: {all_elems[:1] if all_elems else None}")
#         print(f"  -> meta_dict: {meta_dict}")

#         if all_elems and isinstance(all_elems[0], list):
#             elements_per_page = all_elems
#             print(
#                 f"  -> Interpreted all_elems as per-page list with {len(elements_per_page)} pages.")
#         else:
#             elements_per_page = [all_elems if all_elems else []] + [[]
#                                                                     for _ in range(len(pages) - 1)]
#             print(
#                 f"  -> Wrapped all_elems into first page, rest empty. Total: {len(elements_per_page)}")

#         if isinstance(meta_dict, dict):
#             for pnum, meta in meta_dict.items():
#                 try:
#                     idx = int(pnum) - 1
#                     if 0 <= idx < len(pages):
#                         page_meta_by_index[idx] = {
#                             "coord_width": float(meta.get("coord_width", 0) or 0),
#                             "coord_height": float(meta.get("coord_height", 0) or 0),
#                         }
#                         print(
#                             f"  -> Saved meta for page {idx}: {page_meta_by_index[idx]}")
#                 except Exception as e:
#                     print(
#                         f"  !! Failed to parse page number from meta_dict key={pnum}, error={e}")

#     # Merge results into pages
#     for i, page in enumerate(pages):
#         if i < len(elements_per_page):
#             print(
#                 f"[Page {i}] Processing {len(elements_per_page[i])} elements")
#             try:
#                 page["elements"], figures = extract_unstructured_elements(
#                     elements=elements_per_page[i], page_num=i, config=config
#                 )
#                 print(
#                     f"   -> Extracted {len(page['elements'])} structured elements, {len(figures)} figures")
#             except Exception as e:
#                 print(
#                     f"   !! Error in extract_unstructured_elements for page {i}: {e}")
#                 page["elements"], figures = [], []

#             meta = page_meta_by_index.get(i)
#             if meta:
#                 page["coord_width"] = meta["coord_width"]
#                 page["coord_height"] = meta["coord_height"]
#             figure_list += figures
#         else:
#             page["elements"] = []
#             print(f"   !! Warning: No elements found for page index {i}")

#     print(
#         f"[extract_elements] Done - Extracted {len(figure_list)} figures from {len(pages)} pages.")
#     print("=" * 80)
#     return pages, figure_list

def extract_elements(
    pages: List[Dict], file_path: Optional[str] = None, config: Optional[ExtractionConfig] = None
) -> Tuple[List[Dict], List[FigureData]]:
    figure_list: List[FigureData] = []
    elements_per_page: List[List[Any]] = []
    page_meta_by_index: Dict[int, Dict] = {}

    # print(f"Extract elements path: {file_path}")

    if not file_path:
        for i, page in enumerate(pages):
            elems, meta_dict = element_extractor(
                file_path=ensure_parent_dir(page.get("image")), config=config)
            elements_per_page.append(elems)
            if isinstance(meta_dict, dict) and meta_dict:
                first_meta = next(iter(meta_dict.values()))
                page_meta_by_index[i] = {
                    "coord_width": float(first_meta.get("coord_width", 0) or 0),
                    "coord_height": float(first_meta.get("coord_height", 0) or 0),
                }
    else:
        all_elems, meta_dict = element_extractor(
            file_path=file_path, config=config)
        if all_elems and isinstance(all_elems[0], list):
            elements_per_page = all_elems
        else:
            elements_per_page = [all_elems] + [[]
                                               for _ in range(len(pages) - 1)]
        if isinstance(meta_dict, dict):
            for pnum, meta in meta_dict.items():
                try:
                    idx = int(pnum) - 1
                except Exception:
                    continue
                if 0 <= idx < len(pages):
                    page_meta_by_index[idx] = {
                        "coord_width": float(meta.get("coord_width", 0) or 0),
                        "coord_height": float(meta.get("coord_height", 0) or 0),
                    }
    # print(f"[DEBUG] elements_per_page (len={len(elements_per_page)}): "
    #       f"types={[type(e) for e in elements_per_page]}")
    # print("[DEBUG] elements_per_page full content:", elements_per_page)

    for i, page in enumerate(pages):
        if i < len(elements_per_page):
            page["elements"], figures = extract_unstructured_elements(
                elements=elements_per_page[i], page_num=i, config=config
            )
            meta = page_meta_by_index.get(i)
            if meta:
                page["coord_width"] = meta["coord_width"]
                page["coord_height"] = meta["coord_height"]
            figure_list += figures
        else:
            page["elements"] = []
            print(f"Warning: No elements found for page index {i}")

    print(f"Extracted {len(figure_list)} figure from {len(pages)} pages.")
    return pages, figure_list

# def element_extractor(file_path: str, config: Optional[ExtractionConfig] = None) -> List[Any]:
#     """Extract elements from file (backward compatibility)."""
#     extractor = DocumentElementExtractor(config)
#     return extractor.extract_elements_from_file(file_path)


# def extract_unstructured_elements(elements: List[Any], page_num: int,
#                                   config: Optional[ExtractionConfig] = None) -> Tuple[List[Dict], List[FigureData]]:
#     """Extract metadata from elements (backward compatibility)."""
#     processor = ElementProcessor(config or ExtractionConfig())
#     return processor.process_elements(elements, page_num)


# def extract_elements(pages: List[Dict], file_path: Optional[str] = None,
#                      config: Optional[ExtractionConfig] = None) -> Tuple[List[Dict], List[FigureData]]:
#     """Extract elements from pages (backward compatibility - matches original logic exactly)."""
#     figure_list = []
#     elements = []

#     print(f"Extract elements path: {file_path}")

#     # Build elements array first (matching original logic exactly)
#     if not file_path:
#         for i, page in enumerate(pages):
#             elements.append(element_extractor(
#                 file_path=page["image"], config=config))
#     else:
#         elements = element_extractor(file_path=file_path, config=config)

#     # Process elements in alignment with pages (matching original logic)
#     for i, page in enumerate(pages):
#         if i < len(elements):
#             page["elements"], figures = extract_unstructured_elements(
#                 elements=elements[i], page_num=i, config=config
#             )
#             figure_list += figures
#         else:
#             # Handle missing elements appropriately
#             page["elements"] = []
#             print(f"Warning: No elements found for page index {i}")

#     print(f"Extracted {len(figure_list)} figure from {len(pages)} pages.")
#     return pages, figure_list
