# models_dto.py

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ImageMetadataOut(BaseModel):
    image_type: str
    caption: str
    description: str
    ocr_string: str
    image_base64: Optional[str] = None


class ElementOut(BaseModel):
    idx: int
    type: Literal["text", "table", "image"]
    bbox: List[float] = Field(..., alias="bbox")
    text: str = ""
    image_metadata: Optional[ImageMetadataOut] = None


class PageOut(BaseModel):
    index: int
    image_url: Optional[str] = None          # <= default channel
    image_base64: Optional[str] = None       # <= opt-in
    text: Optional[str] = None
    markdown: Optional[str] = None
    elements: List[ElementOut] = Field(default_factory=list)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: Optional[str]):
        if v is None:
            return v
        if v.startswith(("http://", "https://", "/")):
            return v
        # auto-normalize relative → root-absolute
        return "/" + v.lstrip("/")


class FigureOut(BaseModel):
    page_num: int
    idx: int
    pil_image: Optional[str] = None
    generated_text: str


class DocParserContextOut(BaseModel):
    # ✅ auto-omit None fields
    model_config = ConfigDict(ser_json_exclude_none=True)
    file_path: Optional[str] = None
    ocr_file_path: Optional[str] = None
    pages: List[PageOut] = Field(default_factory=list)
    figure_list: List[FigureOut]
    processing_time: float
