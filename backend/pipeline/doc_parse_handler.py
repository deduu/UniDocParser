import os
import json
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import UploadFile
from typing import Tuple, Optional
from pathlib import Path
import uuid
import logging
import aiofiles
from starlette.concurrency import run_in_threadpool
from fastapi import Depends, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from backend.pipeline.model.schemas import SplitPDFResponse
from backend.pipeline.utils import _save_to_tmp
from backend.pipeline.doc_parse_service import DocParserService
from backend.pipeline.doc_parser_steps.context import DocParserContext
from backend.pipeline.model.schemas_dto import (
    PageOut, ElementOut, ImageMetadataOut, FigureOut, DocParserContextOut
)
from backend.pipeline.utils import pil_to_base64
from backend.core.config import settings

logger = logging.getLogger(__name__)


class DocParserHandler:
    def __init__(self, svc: DocParserService = Depends(DocParserService)):
        self.svc = svc
        # now your handler “knows” where to put files:
        self.upload_dir = settings.UPLOAD_DIR
        self.output_dir = settings.OUTPUT_DIR

    async def _save_upload(self, file: UploadFile) -> str:
        """Save UploadFile to disk under self.upload_dir."""
        await run_in_threadpool(os.makedirs, self.upload_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        dest = os.path.join(self.upload_dir, unique_name)

        print(f"dest: {dest}")
        async with aiofiles.open(dest, "wb") as buf:
            await buf.write(await file.read())
        return dest

    async def ocr(self, file: UploadFile, job_id: Optional[str] = None) -> DocParserContextOut:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.ocr(path)
        except Exception as e:
            raise HTTPException(500, f"OCR failed: {e}")
        return self._dto_from_ctx(ctx)

    async def split(self, file: UploadFile, job_id: Optional[str] = None) -> SplitPDFResponse:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.split(path)
        except Exception as e:
            raise HTTPException(500, f"Split failed: {e}")
        return SplitPDFResponse.from_context(ctx)

    async def extract_only(self, file: UploadFile, job_id: Optional[str] = None) -> DocParserContextOut:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.extract_only(path, job_id=job_id)
        except Exception as e:
            raise HTTPException(500, f"Extract only pipeline failed: {e}")
        return self._dto_from_ctx(ctx, job_id=job_id)

    async def full_pipeline(self, file: UploadFile, job_id: Optional[str] = None) -> DocParserContextOut:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.full(path, job_id=job_id)
        except Exception as e:
            raise HTTPException(500, f"Full pipeline failed: {e}")
        return self._dto_from_ctx(ctx, job_id=job_id)

    async def vlm_extract_pipeline(self, file: UploadFile, job_id: Optional[str] = None) -> DocParserContextOut:
        path = await self._save_upload(file)
        try:
            ctx = await self.svc.vlm_extract(path, job_id=job_id)
        except Exception as e:
            raise HTTPException(500, f"VLM extract pipeline failed: {e}")
        return self._dto_from_ctx(ctx, job_id=job_id)

    def _dto_from_ctx(
        self,
        ctx: DocParserContext,
        job_id: Optional[str] = None,
        save_page_images: bool = True,
        save_figure_images: bool = False,
        include_image_metadata: bool = False,

        include_image_base64: bool = False,
    ) -> DocParserContextOut:
        """Convert internal DocParserContext → API DTO."""
        pages = []
        for p in ctx.pages:
            elements_out = []
            for el in p.elements:
                metadata = None
                if include_image_metadata and el.image_metadata:   # ✅ conditionally include
                    md = el.image_metadata
                    metadata = ImageMetadataOut(
                        image_type=md.image_type,
                        caption=md.caption,
                        description=md.description,
                        ocr_string=md.ocr_string,
                        image_base64=md.image_base64 if include_image_base64 else None,  # ✅ conditional
                    )

                elements_out.append(
                    ElementOut(
                        idx=el.idx,
                        type=el.type,
                        bbox=el.bbox,
                        text=el.text,
                        image_metadata=metadata,   # Will be omitted if None
                    )
                )

            # image_b64 = None
            # if save_page_images:
            #     try:
            #         image_b64 = pil_to_base64(Image.open(p.image))
            #     except (FileNotFoundError, UnidentifiedImageError) as e:
            #         print(f"[WARNING] Image not found for page {p.index}: {e}")
            #         image_b64 = None

            pages.append(
                PageOut(
                    index=p.index,
                    # image_url=f"/jobs/{job_id}/pages/{p.index}",
                    image_url=p.image,
                    text=p.text,
                    markdown=p.markdown,
                    elements=elements_out,
                    # NEW: pass through coord space + orientation
                    coord_width=getattr(p, "coord_width", None),
                    coord_height=getattr(p, "coord_height", None),
                    y_origin=getattr(p, "y_origin", "top-left"),
                    rotation_deg=getattr(p, "rotation_deg", 0),
                )
                # PageOut(
                #     index=p.index,
                #     # image_url=p.image,
                #     image_url=f"/jobs/{job_id}/pages/{p.index}",
                #     text=p.text,
                #     markdown=p.markdown,
                #     elements=elements_out,
                # )
            )

        figures = [
            FigureOut(
                page_num=f.page_num,
                idx=f.idx,
                pil_image=pil_to_base64(
                    f.pil_image) if save_figure_images else None,
                generated_text=f.generated_text,
            )
            for f in ctx.figure_list
        ]
        for po in pages[:3]:
            logger.info(
                f"[dto] page {po.index} url={po.image_url} coord=({po.coord_width},{po.coord_height}) y_origin={po.y_origin} rot={po.rotation_deg}"
            )

        return DocParserContextOut(
            file_path=ctx.file_path,
            # ocr_pdf_path=ctx.ocr_pdf_path,
            pages=pages,
            figure_list=figures,
            processing_time=ctx.processing_time or 0.0,
        )

    async def save_results(
        self,
        dto: DocParserContextOut,
        unique_filename: str,
    ) -> Tuple[str, str]:
        """
        Persist JSONL + Markdown exports under self.output_dir.
        Returns (json_filename, markdown_filename).
        """
        await run_in_threadpool(os.makedirs, self.output_dir, exist_ok=True)

        print(f"unique_filename: {unique_filename}")
        print(f"self.output_dir: {self.output_dir}")
        json_path = Path(self.output_dir) / f"{unique_filename}.jsonl"
        md_path = Path(self.output_dir) / f"{unique_filename}.md"
        print(f"json_path: {json_path}")
        payload = {
            "file_path":        dto.file_path,
            "ocr_pdf_path":    dto.ocr_file_path,
            "processing_time": dto.processing_time,
            "pages":           [p.dict() for p in dto.pages],
            "figure_list":     [f.dict() for f in dto.figure_list],
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
        print(f"json_path_name: {json_path.name}")
        return json_path.name, md_path.name
