# app/services/pipeline/context.py
from typing import List, Optional, Literal
from PIL import Image
from pydantic import BaseModel, Field, ConfigDict, field_validator
from backend.pipeline.utils import pil_to_base64


class ImageMetadata(BaseModel):
    image_type: str = ""
    caption: str = ""
    description: str = ""
    ocr_string: str
    image_base64: str


class Element(BaseModel):
    idx: int
    type: Literal["text", "table", "image"]
    bbox: Optional[List[float]] = Field(default=None, serialization_alias="bbox")  # Allow missing
    text: str = ""
    image_metadata: Optional["ImageMetadata"] = None

    @field_validator("bbox", mode="before")
    @classmethod
    def validate_or_default_bbox(cls, v):
        if isinstance(v, list) and len(v) == 4:
            return v
        return [0.0, 0.0, 0.0, 0.0]  # fallback if missing or invalid


class Figure(BaseModel):
    page_num: int
    idx: int
    # instead of PIL image, store a path or base64 string
    pil_image: Image.Image
    generated_text: str = ""

    # ➋ Pydantic v2
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={Image.Image: pil_to_base64}
    )


class Page(BaseModel):
    index: int
    image: str | None = None
    text: str = ""
    markdown: str = ""
    elements: List[Element] = Field(default_factory=list)


class DocParserContext(BaseModel):
    pdf_path: str
    ocr_pdf_path: Optional[str] = None
    pages: List[Page] = Field(default_factory=list)
    figure_list: List[Figure] = Field(default_factory=list)
    processing_time: Optional[float] = None
