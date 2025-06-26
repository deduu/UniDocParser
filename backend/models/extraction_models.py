# models/extraction_models.py
from pydantic import BaseModel
from typing import List, Optional, Literal

class ImageMetadata(BaseModel):
    image_type: str
    caption: str
    description: str
    ocr_string: str
    image_path: str
    image_base64: str

class ElementMetadata(BaseModel):
    index: str
    status: Literal["Success", "Failed"]
    type: str
    bbox: List[float]
    text: Optional[str] = None
    image_metadata: Optional[List[ImageMetadata]] = []

class PageExtraction(BaseModel):
    index: int
    status: Literal["Success", "Failed"]
    markdown: str
    text: str
    elements: List[ElementMetadata] = []

class ExtractionResult(BaseModel):
    source: str
    pages: List[PageExtraction]
    processing_time: Optional[float] = None