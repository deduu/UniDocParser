# models_dto.py

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ImageMetadataOut(BaseModel):
    image_type: str
    caption: str
    description: str
    ocr_string: str
    image_base64: str


class ElementOut(BaseModel):
    idx: int
    type: Literal["text", "table", "image"]
    bbox: List[float] = Field(..., alias="bbox")
    text: str = ""
    image_metadata: Optional[ImageMetadataOut] = None


class PageOut(BaseModel):
    index: int
    image: str
    text: str = ""
    markdown: str = ""
    elements: List[ElementOut] = Field(default_factory=list)


class FigureOut(BaseModel):
    page_num: int
    idx: int
    image_path: str          # base-64 string *or* URL
    generated_text: str


class PDFContextOut(BaseModel):
    pdf_path: str
    ocr_pdf_path: Optional[str] = None
    pages: List[PageOut] = Field(default_factory=list)
    figure_list: List[FigureOut]
    processing_time: float
