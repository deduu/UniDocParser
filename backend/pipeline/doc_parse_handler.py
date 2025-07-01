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


class DocParserHandler:
    def __init__(self, svc: DocParserService = Depends(DocParserService)):
        self.svc = svc
        # # # now your handler “knows” where to put files:
        # self.upload_dir = settings.UPLOAD_DIR
        # self.output_dir = settings.OUTPUT_DIR

    async def _save_upload(
            self, 
            file: UploadFile, 
            user_id: str,
            folder: str,
        ) -> str:
        """Save UploadFile to disk under self.upload_dir."""
        upload_dir = os.path.join(settings.UPLOAD_DIR, user_id, folder)
        await run_in_threadpool(os.makedirs, upload_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        dest = os.path.join(upload_dir, unique_name)

        print(f"dest: {dest}")
        async with aiofiles.open(dest, "wb") as buf:
            await buf.write(await file.read())
        return dest

    async def ocr(self, user_id: str, folder: str, file: UploadFile) -> DocParserContextOut:
        path = await self._save_upload(file, user_id=user_id, folder=folder)
        try:
            ctx = await self.svc.ocr(user_id=user_id, folder=folder, file_path=path)
        except Exception as e:
            raise HTTPException(500, f"OCR failed: {e}")
        return self._dto_from_ctx(ctx)

    async def split(self, user_id: str, folder: str, file: UploadFile) -> SplitPDFResponse:
        path = await self._save_upload(file, user_id=user_id, folder=folder)
        try:
            ctx = await self.svc.split(user_id=user_id, folder=folder, file_path=path)
        except Exception as e:
            raise HTTPException(500, f"Split failed: {e}")
        return SplitPDFResponse.from_context(ctx)

    async def extract_only(self, user_id: str, folder: str, file: UploadFile) -> DocParserContextOut:
        path = await self._save_upload(file, user_id=user_id, folder=folder)
        try:
            ctx = await self.svc.extract_only(user_id=user_id, folder=folder, file_path=path)
        except Exception as e:
            raise HTTPException(500, f"Extract only pipeline failed: {e}")
        return self._dto_from_ctx(ctx)

    async def full_pipeline(self, user_id: str, folder: str, file: UploadFile) -> DocParserContextOut:
        path = await self._save_upload(file, user_id=user_id, folder=folder)
        try:
            ctx = await self.svc.full(user_id=user_id, folder=folder, file_path=path)
        except Exception as e:
            raise HTTPException(500, f"Full pipeline failed: {e}")
        return self._dto_from_ctx(ctx)

    def _dto_from_ctx(self, ctx: DocParserContext) -> DocParserContextOut:
        """Convert internal DocParserContext → API DTO."""
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
                        status=el.status,
                        type=el.type,
                        bbox=el.bbox,
                        text=el.text,
                        image_metadata=metadata,
                    )
                )

            # ✅ Try to open image and encode it
            try:
                image_b64 = pil_to_base64(Image.open(p.image))
            except (FileNotFoundError, UnidentifiedImageError) as e:
                print(f"[WARNING] Image not found for page {p.index}: {e}")
                image_b64 = None  # Or you can use: pil_to_base64(Image.open("static/placeholder.jpg"))

            pages.append(
                PageOut(
                    index=p.index,
                    status=p.status,
                    image=image_b64,
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
                status=f.status,
            )
            for f in ctx.figure_list
        ]

        return DocParserContextOut(
            user_id=ctx.user_id,
            folder=ctx.folder,
            file_path=ctx.file_path,
            ocr_file_path=ctx.ocr_file_path,
            pages=pages,
            figure_list=figures,
            processing_time=ctx.processing_time or 0.0,
        )

    async def save_results(
        self,
        dto: DocParserContextOut,
        unique_filename: str,
        user_id: str,
        folder: str,
    ) -> Tuple[str, str]:
        """
        Persist JSONL + Markdown exports under settings.OUTPUT_DIR/user_id/folder.
        Returns (json_filename, markdown_filename).
        """
        output_dir = os.path.join(settings.OUTPUT_DIR, user_id, folder)
        await run_in_threadpool(os.makedirs, output_dir, exist_ok=True)

        print(f"unique_filename: {unique_filename}")
        print(f"output_dir: {output_dir}")
        json_path = Path(output_dir) / f"{unique_filename}.jsonl"
        md_path = Path(output_dir) / f"{unique_filename}.md"
        print(f"json_path: {json_path}")
        payload = {
            "user_id":          dto.user_id,
            "folder":           dto.folder,
            "file_name":        unique_filename,
            "file_path":        dto.file_path,
            "ocr_file_path":    dto.ocr_file_path,
            "processing_time":  dto.processing_time,
            "pages":            [p.dict() for p in dto.pages],
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
