# app/models/schemas.py
from pydantic import BaseModel
from typing import List
from backend.pipeline.doc_parser_steps.context import DocParserContext


class PageInfo(BaseModel):
    index: int
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
            source=ctx.pdf_path,
            pages=[PageInfo(**p.dict()) for p in ctx.pages],
            processing_time=ctx.processing_time or 0.0
        )


class FigureOut(BaseModel):
    page_num: int
    idx: int
    image_url: str            # or image_base64: str if you prefer
    generated_text: str


class PageOut(BaseModel):
    index: int
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
            source=ctx.pdf_path,
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
