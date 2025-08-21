# backend/extraction/services/element_extractor.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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
        elements = extractor.extract(validated_path)
        
        logger.info(f"Extracted {len(elements)} elements from {file_path}")
        return elements
    
    def extract_elements_from_pages(self, pages: List[Dict], 
                                  file_path: Optional[Union[str, Path]] = None) -> Tuple[List[Dict], List[FigureData]]:
        """Extract elements from multiple pages or a single file."""
        figure_list = []
        elements = []  # Store elements array to align with pages
        
        logger.info(f"Extract elements path: {file_path}")
        
        if not file_path:
            # Extract elements from each page image and build elements array
            for i, page in enumerate(pages):
                if "image" in page:
                    page_elements = self.extract_elements_from_file(page["image"])
                    elements.append(page_elements)
                else:
                    elements.append([])  # Empty list for missing images
                    logger.warning(f"No image found for page {i}")
        else:
            # Extract from single file - NOTE: Original code has a logic issue here
            # It extracts once but tries to use elements[i] in the loop
            # We'll assume the single file extraction returns a list of page elements
            single_file_elements = self.extract_elements_from_file(file_path)
            
            # If it's a list of lists (per page), use as is
            # If it's a flat list, we need to decide how to split it across pages
            if single_file_elements and isinstance(single_file_elements[0], list):
                elements = single_file_elements
            else:
                # For now, assign all elements to first page (may need adjustment based on actual use case)
                elements = [single_file_elements] + [[] for _ in range(len(pages) - 1)]
        
        # Now process elements in alignment with pages (matching original logic)
        for i, page in enumerate(pages):
            if i < len(elements):
                page_elements, figures = self.processor.process_elements(
                    elements[i], page_num=i
                )
                page["elements"] = page_elements
                figure_list.extend(figures)
            else:
                # Handle missing elements appropriately
                page["elements"] = []
                logger.warning(f"No elements found for page index {i}")
        
        logger.info(f"Extracted {len(figure_list)} figures from {len(pages)} pages")
        return pages, figure_list

# Convenience functions for backward compatibility
def element_extractor(file_path: str, config: Optional[ExtractionConfig] = None) -> List[Any]:
    """Extract elements from file (backward compatibility)."""
    extractor = DocumentElementExtractor(config)
    return extractor.extract_elements_from_file(file_path)


def extract_unstructured_elements(elements: List[Any], page_num: int, 
                                config: Optional[ExtractionConfig] = None) -> Tuple[List[Dict], List[FigureData]]:
    """Extract metadata from elements (backward compatibility)."""
    processor = ElementProcessor(config or ExtractionConfig())
    return processor.process_elements(elements, page_num)


def extract_elements(pages: List[Dict], file_path: Optional[str] = None, 
                   config: Optional[ExtractionConfig] = None) -> Tuple[List[Dict], List[FigureData]]:
    """Extract elements from pages (backward compatibility - matches original logic exactly)."""
    figure_list = []
    elements = []
    
    print(f"Extract elements path: {file_path}")
    
    # Build elements array first (matching original logic exactly)
    if not file_path:
        for i, page in enumerate(pages):
            elements.append(element_extractor(file_path=page["image"], config=config))
    else:
        elements = element_extractor(file_path=file_path, config=config)
    
    # Process elements in alignment with pages (matching original logic)
    for i, page in enumerate(pages):
        if i < len(elements):
            page["elements"], figures = extract_unstructured_elements(
                elements=elements[i], page_num=i, config=config
            )
            figure_list += figures
        else:
            # Handle missing elements appropriately
            page["elements"] = []
            print(f"Warning: No elements found for page index {i}")
    
    print(f"Extracted {len(figure_list)} figure from {len(pages)} pages.")
    return pages, figure_list