# backend/extraction/types.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class FileType(Enum):
    """Supported file types for element extraction."""
    IMAGE = "image"
    PDF = "pdf"
    EXCEL = "excel"


@dataclass
class ElementMetadata:
    """Structured element metadata."""
    idx: int
    type: str
    text: str = ""
    bbox: Optional[Dict] = None
    image_metadata: Optional[Dict] = None


@dataclass
class FigureData:
    """Figure data structure."""
    page_num: int
    idx: int
    pil_image: Any
    generated_text: str = ""
