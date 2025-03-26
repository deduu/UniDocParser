# models/extraction_models.py
from pydantic import BaseModel
from typing import List, Optional

class ImageMetadata(BaseModel):
    index: str
    bbox: List[float]
    name: str
    type: str
    data: Optional[str] = None
    description: Optional[str] = None

class PageExtraction(BaseModel):
    index: int
    text: str
    images: List[ImageMetadata] = []

class ExtractionResult(BaseModel):
    source: str
    pages: List[PageExtraction]