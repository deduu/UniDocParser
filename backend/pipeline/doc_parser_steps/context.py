# app/services/pipeline/context.py
from typing import List, Optional, Literal, Union
from PIL import Image
from pydantic import BaseModel, Field, ConfigDict, field_validator

from typing import Union
from pydantic import BaseModel, ConfigDict, Field, AliasChoices
# from pydantic.alias_generators import AliasChoices  # pydantic v2
from functools import lru_cache, cached_property
from urllib.parse import urlparse
import io, os, base64, requests  # requests only if you want http(s) support

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


# class Figure(BaseModel):
#     page_num: int
#     idx: int
#     # instead of PIL image, store a path or base64 string
#     pil_image: Image.Image
#     generated_text: str = ""

#     # ➋ Pydantic v2
#     model_config = ConfigDict(
#         arbitrary_types_allowed=True,
#         json_encoders={Image.Image: pil_to_base64}
#     )
def _open_ref(ref: str) -> Image.Image:
    p = urlparse(ref)
    if p.scheme == "data":
        _, b64 = ref.split(",", 1)
        return Image.open(io.BytesIO(base64.b64decode(b64)))
    if p.scheme in ("file", ""):
        path = p.path if p.scheme == "file" else ref
        return Image.open(path)
    if p.scheme in ("http", "https"):
        r = requests.get(ref, timeout=10); r.raise_for_status()
        return Image.open(io.BytesIO(r.content))
    raise ValueError(f"Unsupported scheme: {ref}")

@lru_cache(maxsize=64)
def load_image_cached(ref: str) -> Image.Image:
    return _open_ref(ref)

class Figure(BaseModel):
    page_num: int
    idx: int
    # Accept either PIL now or string ref later.
    image: Union[Image.Image, str] = Field(
        validation_alias=AliasChoices("image", "pil_image")  # reads .pil_image on FigureData
    )
    generated_text: str = ""

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={Image.Image: pil_to_base64},
    )

    @property
    def pil_image(self) -> Image.Image:
        if isinstance(self.image, Image.Image):
            return self.image
        # if it's a str, lazy-load via your cached loader:
        return load_image_cached(self.image)


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
