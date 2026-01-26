from typing import List, Optional, Literal
from pydantic import BaseModel, Field
# app/models/schemas.py
from pydantic import BaseModel
from typing import List
from backend.pipeline.steps.context import DocParserContext


class PageInfo(BaseModel):
    index: int
    status: str # "Success" or "Failed"
    image: str     # path or base64
    text: str
    markdown: str


class SplitPDFResponse(BaseModel):
    source: str
    pages: List[PageInfo]
    processing_time: float

    @classmethod
    def from_context(cls, ctx: DocParserContext) -> "SplitPDFResponse":
        return cls(
            source=ctx.file_path,
            pages=[PageInfo(**p.dict()) for p in ctx.pages],
            processing_time=ctx.processing_time or 0.0
        )

class FigureOut(BaseModel):
    page_num: int
    idx: int
    image_url: str            # or image_base64: str if you prefer
    generated_text: str
    status: str   # "Success" or "Failed"


class PageOut(BaseModel):
    index: int
    status: str               # "Success" or "Failed"
    image: str
    text: str = ""
    markdown: str = ""


class FullPDFResponse(BaseModel):
    source: str
    pages: list[PageOut]
    figures: list[FigureOut]
    processing_time: float

    @classmethod
    def from_context(cls, ctx: DocParserContext) -> "FullPDFResponse":
        return cls(
            source=ctx.file_path,
            pages=[
                PageOut(**p.model_dump(exclude={"image"})) for p in ctx.pages],
            figures=[
                FigureOut(
                    page_num=f.page_num,
                    idx=f.idx,
                    # example
                    image_url=f"/static/figures/{f.page_num}_{f.idx}.png",
                    generated_text=f.generated_text,
                )
                for f in ctx.figure_list
            ],
            processing_time=ctx.processing_time or 0.0,
        )


class ImageMetadataOut(BaseModel):
    image_type: str
    caption: str
    description: str
    ocr_string: str
    image_base64: str


class ElementOut(BaseModel):
    idx: int
    status: Literal["Success", "Failed"]
    type: Literal["text", "table", "image"]
    bbox: List[float] = Field(..., alias="bbox")
    text: str = ""
    image_metadata: Optional[ImageMetadataOut] = None


class PageOut(BaseModel):
    index: int
    status: Literal["Success", "Failed"]
    image: Optional[str]
    text: str = ""
    markdown: str = ""
    elements: List[ElementOut] = Field(default_factory=list)


class FigureOut(BaseModel):
    page_num: int
    idx: int
    pil_image: str          # base-64 string *or* URL
    generated_text: str
    status: Literal["Success", "Failed"]

class DocParserContextOut(BaseModel):
    file_path: str
    ocr_file_path: Optional[str] = None
    pages: List[PageOut] = Field(default_factory=list)
    figure_list: List[FigureOut]
    processing_time: float