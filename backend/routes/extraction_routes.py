import os
import uuid
import traceback
import logging
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from PIL.Image import Image
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import io
import base64
import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

# from backend.services.pipeline import PDFExtractionPipeline
from backend.core.config import settings
from backend.db.base import session_manager

from backend.pipeline.model.schemas_dto import DocParserContextOut
from backend.pipeline.doc_parse_service import DocParserService
from backend.pipeline.doc_parse_handler import DocParserHandler
from backend.pipeline.model.schemas import SplitPDFResponse
from backend.schemas.response import ResponseModel
from backend.utils.unlink_files import unlink_paths
# from backend.services.extractor_services import ExtractJobService, ExtractPageService, ExtractResultService
from backend.schemas.extractor import ExtractJobCreate, ExtractPageCreate, ExtractResultUpsert
from backend.deps.verify import verify_internal_call
from backend.deps import Principal, get_principal_from_headers
from backend.deps.security import Principal, get_verified_principal
from backend.db.services import ExtractJobService, ExtractPageService, ExtractResultService, ExtractorService

logger = logging.getLogger(__name__)
router = APIRouter()


# class PageOut(BaseModel):
#     page:  int
#     text:  str
#     images: List[str]


# class ExtractOut(BaseModel):
#     source:          str
#     pages:           List[Dict[str, Any]]     # ← accept any dict here
#     processing_time: float


# class ResponseModel(BaseModel):
#     message: str
#     job_id: Optional[str]
#     extraction_result: Optional[DocParserContextOut] = None
#     json_output: Optional[str] = None
#     markdown_output: Optional[str] = None


async def get_db_session():
    async with session_manager.create_session() as session:
        yield session


async def get_extract_job(db: AsyncSession = Depends(get_db_session)):
    return ExtractJobService(db)


async def get_extract_page(db: AsyncSession = Depends(get_db_session)):
    return ExtractPageService(db)


async def get_extract_result(db: AsyncSession = Depends(get_db_session)):
    return ExtractResultService(db)


async def get_extractor_service(db: AsyncSession = Depends(get_db_session)) -> ExtractorService:
    return ExtractorService(db)

# ------------------------------------------------------------------------------


@router.post("/ocrpdf", response_model=DocParserContextOut)
async def ocr_pdf(
    file: UploadFile = File(...),
    handler: DocParserHandler = Depends(),
) -> DocParserContextOut:
    return await handler.ocr(file)


@router.post("/splitpdf", response_model=SplitPDFResponse)
async def handle_file(file: UploadFile = File(...), handler: DocParserHandler = Depends()):
    return await handler.split(file)


@router.post("/extractpdf_db", response_model=ResponseModel)
async def extract_pdf_db(
    file: UploadFile = File(...),
    handler: DocParserHandler = Depends(),
    principal: Principal = Depends(get_verified_principal),
    # user: dict = Depends(verify_internal_call),
    extract_job: ExtractJobService = Depends(get_extract_job),
    extract_page: ExtractPageService = Depends(get_extract_page),
    extract_result: ExtractResultService = Depends(get_extract_result),
    extractor_service: ExtractorService = Depends(get_extractor_service),
    background_tasks: BackgroundTasks = None,
) -> ResponseModel:

    job = None

    print(f"Document extracted by user {principal.user_id}")
    # 1) Validate file type
    fname = (file.filename or "").lower()
    if not fname.endswith((
        ".pdf",
        ".xls", ".xlsx",                  # Excel
        ".ppt", ".pptx",                  # PowerPoint
        ".doc", ".docx",                  # Word
        ".jpg", ".jpeg", ".png", ".gif",  # Images
    )):
        raise HTTPException(
            400, "Only PDF, Excel, PowerPoint, Word, or image files are supported"
        )

    try:
        # 1) Create Job: queued
        job = await extract_job.create_job(ExtractJobCreate(
            # fallback if you don't have orgs yet
            tenant_id=principal.tenant_id or principal.user_id,
            created_by_user_id=principal.user_id,
            source_file_name=file.filename,
            options_json={},
            status="queued",
        ))

        await extract_job.set_status(job.id, "running")

        # 2) Upload file to S3
        # 3) Run the full pipeline (upload → OCR, split, extract, etc.)
        if fname.endswith((".xls", ".xlsx")):
            dto: DocParserContextOut = await handler.extract_only(file, job.id)
        else:
            dto: DocParserContextOut = await handler.full_pipeline(file, job.id)

        # 4) Persist JSONL & Markdown on disk
        json_name, md_name = await handler.save_results(
            dto,
            Path(dto.file_path).name,
        )

        await extract_job.update_source_file_name(job.id, Path(dto.file_path).name)

        # 5) Persist per-page rows
        pages = [
            ExtractPageCreate(
                job_id=job.id,
                page_index=p.index,
                image_url=p.image_url,
                text=p.text,
                markdown=p.markdown,
                elements=[e.model_dump(by_alias=True)
                          for e in (p.elements or [])] or None,
            )
            for p in dto.pages
        ]

        await extract_page.replace_pages(job.id, pages)

        # Persist result summary
        await extract_result.upsert(ExtractResultUpsert(
            job_id=job.id,
            json_url=json_name,
            markdown_url=md_name,
            processing_time=int(dto.processing_time or 0),
        ))

        await extract_job.update(job.id,  {"status": "succeeded", "page_count_actual": len(dto.pages)})

        # 6) Return your typed response
        return ResponseModel(
            message="Document extracted successfully",
            job_id=job.id,
            extraction_result=dto,
            json_output=json_name,
            markdown_output=md_name,
        )

    except Exception as e:
        if job:
            try:
                await extract_job.set_status(job.id, "failed", error=str(e))
            except Exception:
                pass
        paths = await extractor_service.collect_job_file_paths(job.id, principal.user_id)

        if paths:
            if background_tasks is not None:
                background_tasks.add_task(
                    unlink_paths, paths)
            else:
                await unlink_paths(paths)

        return JSONResponse(
            status_code=500,
            content={"message": "PDF extraction failed", "error": str(
                e), "traceback": traceback.format_exc()},
        )


@router.post(
    "/extractpdf",
    response_model=ResponseModel,
)
async def extract_pdf(
    file: UploadFile = File(...),
    handler: DocParserHandler = Depends(),
    # user: dict = Depends(verify_internal_call),
) -> ResponseModel:

    # print(f"Document extracted by user {user['user_id']}")
    # 1) Validate file type
    fname = (file.filename or "").lower()
    if not fname.endswith((
        ".pdf",
        ".xls", ".xlsx",                  # Excel
        ".ppt", ".pptx",                  # PowerPoint
        ".doc", ".docx",                  # Word
        ".jpg", ".jpeg", ".png", ".gif",  # Images
    )):
        raise HTTPException(
            400, "Only PDF, Excel, PowerPoint, Word, or image files are supported"
        )

    try:
        # 3) Run the full pipeline (upload → OCR, split, extract, etc.)
        if file.filename.lower().endswith((".xls", ".xlsx")):
            dto: DocParserContextOut = await handler.extract_only(file)
        else:
            dto: DocParserContextOut = await handler.full_pipeline(file)

        print(f"dto.pdf_path: {dto.file_path}")

        # 4) Persist JSONL & Markdown on disk
        json_name, md_name = await handler.save_results(
            dto,
            Path(dto.file_path).name,
        )

        # 5) Return your typed response
        return ResponseModel(
            message="Document extracted successfully",
            job_id="None",
            extraction_result=dto,
            json_output=json_name,
            markdown_output=md_name,
        )

    except Exception as e:
        traceback_str = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "message": "PDF extraction failed",
                "error": str(e),
                "traceback": traceback_str,
            },
        )


# ------------------------------------------------------------------------------


@router.post("/upload-pdf/", name="upload_pdf")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    # extraction_model: str = Form("default"),
    # image_model: str = Form("basic"),
    # text_model: str = Form("plain")
):
    """
    Upload and extract PDF with model selections.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported")

    # Create a unique filename and ensure upload directory exists
    try:
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        pdf_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        # Asynchronously save the uploaded PDF
        async with aiofiles.open(pdf_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)
        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF uploaded successfully",
                "filename": unique_filename,
                "pdf_path": pdf_path
            }
        )
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "message": "PDF upload failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/extract-pdf/{filename}", name="extract_pdf")
async def extract_pdf(filename: str):
    pdf_path = os.path.join(settings.UPLOAD_DIR, filename)

    try:
        # Process the PDF via the extraction pipeline
        pipeline = PDFExtractionPipeline(pdf_path)
        extraction_result = pipeline.process()

        extraction = ExtractOut(**extraction_result)
        # Save extraction results (JSON and Markdown outputs)
        json_output_path, md_output_path = pipeline.save_results(
            filename, settings.OUTPUT_DIR)

        return ResponseModel(
            message="PDF extracted successfully",
            extraction_result=extraction,
            json_output=json_output_path,
            markdown_output=md_output_path,
        )
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        logger.error(traceback.format_exc())
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        return JSONResponse(
            status_code=500,
            content={
                "message": "PDF extraction failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/ocr-pdf/{filename}", name="ocr_pdf")
async def ocr_pdf(filename: str):
    pdf_path = os.path.join(settings.UPLOAD_DIR, filename)
    try:
        # Process the PDF via the extraction pipeline
        pipeline = PDFExtractionPipeline(pdf_path)
        ocr_pdf_path = pipeline.ocr_pdf(settings.OUTPUT_DIR)
        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF OCR completed successfully",
                "ocr_pdf_path": ocr_pdf_path
            }
        )
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "message": "File not found",
                "error": str(e)
            }
        )
    except Exception as e:
        logger.error(f"OCR PDF error: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "message": "PDF OCR failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.post("/extract-pdf/")
async def extract_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extraction_model: str = Form("default"),
    image_model: str = Form("basic"),
    text_model: str = Form("plain")
):
    """
    Upload and extract PDF with model selections.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported")

    # Create a unique filename and ensure upload directory exists
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    pdf_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    try:
        # Asynchronously save the uploaded PDF
        async with aiofiles.open(pdf_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)

        # Process the PDF via the extraction pipeline
        pipeline = PDFExtractionPipeline(pdf_path)
        extraction_result = pipeline.process()

        clean = convert_pil_to_data_uri(extraction_result)

        extraction = ExtractOut(**clean)
        # Save extraction results (JSON and Markdown outputs)
        json_output_path, md_output_path = pipeline.save_results(
            unique_filename, settings.OUTPUT_DIR)

        return ResponseModel(
            message="PDF extracted successfully",
            extraction_result=extraction,
            json_output=json_output_path,
            markdown_output=md_output_path,
        )
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        logger.error(traceback.format_exc())
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        return JSONResponse(
            status_code=500,
            content={
                "message": "PDF extraction failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/download/{filename}", name="download_file")
async def download_file(filename: str):
    file_path = os.path.join("outputs", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)


@router.get("/extracted-pdf/json-{filename}", name="extracted_pdf_json")
async def extracted_pdf_json(filename: str):
    """
    Get the JSON output of the extracted PDF.
    """
    json_output_path = os.path.join(settings.OUTPUT_DIR, f"{filename}.jsonl")
    print(json_output_path)
    if not os.path.exists(json_output_path):
        raise HTTPException(status_code=404, detail="File not found")

    async with aiofiles.open(json_output_path, "r") as f:
        content = await f.read()

    # Convert the JSON string to a Python object
    try:
        content = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to decode JSON")

    return JSONResponse(content=content)


@router.get("/extracted-pdf/md-{filename}", name="extracted_pdf_md")
async def extracted_pdf_md(filename: str):
    """
    Get the Markdown output of the extracted PDF.
    """
    md_output_path = os.path.join(settings.OUTPUT_DIR, f"{filename}.md")
    if not os.path.exists(md_output_path):
        raise HTTPException(status_code=404, detail="File not found")

    async with aiofiles.open(md_output_path, "r") as f:
        content = await f.read()

    return PlainTextResponse(content=content)


def convert_pil_to_data_uri(obj: Any) -> Any:
    """
    Recursively walk through dicts/lists/tuples and:
      • for any PIL.Image.Image, return a data-URI string
      • for any dict, list or tuple, recurse into its elements
      • otherwise return the object unchanged
    """
    # 1) If it’s a PIL image, encode to data URI
    if isinstance(obj, Image):
        buffer = io.BytesIO()
        obj.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    # 2) If it’s a dict, recurse on its values
    if isinstance(obj, dict):
        return {k: convert_pil_to_data_uri(v) for k, v in obj.items()}

    # 3) If it’s a list, recurse on each element
    if isinstance(obj, list):
        return [convert_pil_to_data_uri(v) for v in obj]

    # 4) If it’s a tuple, recurse and rebuild a tuple
    if isinstance(obj, tuple):
        return tuple(convert_pil_to_data_uri(v) for v in obj)

    # 5) Otherwise, leave it as-is
    return obj
