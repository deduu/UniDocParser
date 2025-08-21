# backend/extraction/config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExtractionConfig:
    """Configuration for element extraction."""
    extract_images_in_pdf: bool = True
    extract_image_block_to_payload: bool = False
    infer_table_structure: bool = True
    languages: Optional[List[str]] = None
    image_quality: int = 50
    image_resize: int = 560

    def __post_init__(self) -> None:
        if self.languages is None:
            self.languages = ["eng", "ind"]
