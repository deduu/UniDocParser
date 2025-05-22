from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import UploadFile
from fastapi import Depends, HTTPException, UploadFile
from PIL import Image
from backend.pipeline.model.schemas import SplitPDFResponse
from backend.pipeline.utils import _save_to_tmp
from backend.pipeline.pdf_service import PDFService
from backend.pipeline.context import PDFContext
from backend.pipeline.model.schemas_dto import (
    PageOut, ElementOut, ImageMetadataOut, FigureOut, PDFContextOut
)
from backend.pipeline.utils import pil_to_base64


# def context_to_dto(ctx: PDFContext) -> PDFContextOut:
#     return PDFContextOut(
#         pdf_path=ctx.pdf_path,
#         ocr_pdf_path=ctx.ocr_pdf_path,
#         pages=[
#             PageOut(
#                 index=p.index,
#                 # or however you produce the string
#                 image=pil_to_base64(Image.open(p.image)),
#                 text=p.text,
#                 markdown=p.markdown,
#                 elements=p.elements,
#             )
#             for p in ctx.pages
#         ],
#         figure_list=[
#             FigureOut(
#                 page_num=f.page_num,
#                 idx=f.idx,
#                 pil_image=pil_to_base64(f.pil_image),  # or generate a URL
#                 generated_text=f.generated_text,
#             )
#             for f in ctx.figure_list
#         ],
#         processing_time=ctx.processing_time or 0.0,
#     )

def context_to_dto(ctx: PDFContext) -> PDFContextOut:
    pages = []
    for p in ctx.pages:
        elements_out = []
        for el in p.elements:
            metadata = None
            if el.image_metadata:
                md = el.image_metadata
                metadata = ImageMetadataOut(
                    image_type=md.image_type,
                    caption=md.caption,
                    description=md.description,
                    ocr_string=md.ocr_string,
                    image_base64=md.image_base64,
                )
            elements_out.append(
                ElementOut(
                    idx=el.idx,
                    type=el.type,
                    bbox=el.bbox,
                    text=el.text,
                    image_metadata=metadata,
                )
            )

        pages.append(
            PageOut(
                index=p.index,
                image=pil_to_base64(Image.open(p.image)),
                text=p.text,
                markdown=p.markdown,
                elements=elements_out,
            )
        )

    figures = [
        FigureOut(
            page_num=f.page_num,
            idx=f.idx,
            pil_image=pil_to_base64(f.pil_image),
            generated_text=f.generated_text,
        )
        for f in ctx.figure_list
    ]

    return PDFContextOut(
        pdf_path=ctx.pdf_path,
        ocr_pdf_path=ctx.ocr_pdf_path,
        pages=pages,
        figure_list=figures,
        processing_time=ctx.processing_time or 0.0,
    )


class PDFHandler:
    def __init__(self, PDFService: PDFService = Depends(PDFService)):
        self.svc = PDFService

    async def ocr(self, file: UploadFile) -> PDFContextOut:
        path = await _save_to_tmp(file)
        try:
            ctx = await self.svc.ocr(path)
        except Exception as e:
            raise HTTPException(500, f"OCR failed: {e}")
        return context_to_dto(ctx)

    async def split(self, file: UploadFile) -> SplitPDFResponse:
        path = await _save_to_tmp(file)
        try:
            ctx = await self.svc.split(path)
        except Exception as e:
            raise HTTPException(500, f"Split failed: {e}")
        return SplitPDFResponse.from_context(ctx)

    async def full(self, file: UploadFile) -> PDFContextOut:  # ← return the model
        path = await _save_to_tmp(file)
        try:
            ctx = await self.svc.full(path)
        except Exception as e:
            raise HTTPException(500, f"Full failed: {e}")
        return context_to_dto(ctx)
