import os
import json
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import UploadFile
from typing import Tuple
from pathlib import Path
import uuid
import aiofiles
from starlette.concurrency import run_in_threadpool
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
from backend.core.config import settings


class PDFHandler:
    def __init__(self, svc: PDFService = Depends(PDFService)):
        self.svc = svc
        # now your handler “knows” where to put files:
        self.upload_dir = settings.UPLOAD_DIR
        self.output_dir = settings.OUTPUT_DIR

    async def _save_upload(self, file: UploadFile) -> str:
        """Save UploadFile to disk under self.upload_dir."""
        await run_in_threadpool(os.makedirs, self.upload_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        dest = os.path.join(self.upload_dir, unique_name)
        async with aiofiles.open(dest, "wb") as buf:
            await buf.write(await file.read())
        return dest

    async def ocr(self, file: UploadFile) -> PDFContextOut:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.ocr(path)
        except Exception as e:
            raise HTTPException(500, f"OCR failed: {e}")
        return self._dto_from_ctx(ctx)

    async def split(self, file: UploadFile) -> SplitPDFResponse:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.split(path)
        except Exception as e:
            raise HTTPException(500, f"Split failed: {e}")
        return SplitPDFResponse.from_context(ctx)

    async def full_pipeline(self, file: UploadFile) -> PDFContextOut:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.full(path)
        except Exception as e:
            raise HTTPException(500, f"Full pipeline failed: {e}")
        return self._dto_from_ctx(ctx)

    def _dto_from_ctx(self, ctx: PDFContext) -> PDFContextOut:
        """Convert internal PDFContext → API DTO."""
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
                image_path=f.image_path,
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

    async def save_results(
        self,
        dto: PDFContextOut,
        unique_filename: str,
    ) -> Tuple[str, str]:
        """
        Persist JSONL + Markdown exports under self.output_dir.
        Returns (json_filename, markdown_filename).
        """
        await run_in_threadpool(os.makedirs, self.output_dir, exist_ok=True)

        json_path = Path(self.output_dir) / f"{unique_filename}.jsonl"
        md_path = Path(self.output_dir) / f"{unique_filename}.md"

        source = unique_filename.split("_", 1)[1]
        payload = {
            "source":        source,
            "pages":           [p.dict() for p in dto.pages],
            # "processing_time": dto.processing_time,
        }

        # --- write JSONL ---
        def _write_json():
            with open(json_path, "w") as f:
                json.dump(payload, f, indent=2)

        await run_in_threadpool(_write_json)

        # --- write Markdown ---
        def _write_md():
            with open(md_path, "w") as md_file:
                for page in payload["pages"]:
                    md_file.write(page["markdown"])
                    md_file.write("\n\n---\n\n")

        await run_in_threadpool(_write_md)

        return json_path.name, md_path.name
