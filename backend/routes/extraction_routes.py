import os
import uuid
import traceback
import logging
import aiofiles
from PIL.Image import Image
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import io
import base64
import json
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

from backend.services.pipeline import PDFExtractionPipeline
from backend.core.config import settings

from backend.pipeline.model.schemas_dto import DocParserContextOut

from backend.pipeline.doc_parse_service import DocParserService
from backend.pipeline.doc_parse_handler import DocParserHandler
from backend.pipeline.model.schemas import SplitPDFResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class PageOut(BaseModel):
    page:  int
    text:  str
    images: List[str]


class ExtractOut(BaseModel):
    source:          str
    pages:           List[Dict[str, Any]]     # ← accept any dict here
    processing_time: float


class ResponseModel(BaseModel):
    message: str
    extraction_result: DocParserContextOut
    json_output: str
    markdown_output: str


# ------------------------------------------------------------------------------
@router.post("/ocrpdf", response_model=DocParserContextOut)
async def ocr_pdf(
    user_id: str = Form(...),
    folder: str = Form(...),
    file: UploadFile = File(...),
    handler: DocParserHandler = Depends(),
) -> DocParserContextOut:
    return await handler.ocr(user_id=user_id, folder=folder, file=file)


@router.post("/splitpdf", response_model=SplitPDFResponse)
async def handle_file(
    user_id: str = Form(...),
    folder: str = Form(...),
    file: UploadFile = File(...),
    handler: DocParserHandler = Depends(),
):
    return await handler.split(user_id=user_id, folder=folder, file=file)


@router.post(
    "/extractpdf",
    response_model=ResponseModel,
)
async def extract_pdf(
    user_id: str = Form(...),
    folder: str = Form(...),
    file: UploadFile = File(...),
    handler: DocParserHandler = Depends(),
) -> ResponseModel:
    # check if the user token is available
    if not user_id:
        raise HTTPException(
            status_code=400, detail="User token is required for extraction"
        )
    # check if the folder is available
    if not folder:
        raise HTTPException(
            status_code=400, detail="Folder is required for extraction"
        )
    
    # create the upload and output directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, user_id, folder)
    output_dir = os.path.join(settings.OUTPUT_DIR, user_id, folder)
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 1) Validate file type
    if not file.filename or not (
        file.filename.lower().endswith(".pdf")
        or file.filename.lower().endswith(".xls")
        or file.filename.lower().endswith(".xlsx")
    ):
        raise HTTPException(
            status_code=400, detail="Only PDF or Excel files (.xls/.xlsx) are supported"
        )

    try:
        # 3) Run the full pipeline (upload → OCR, split, extract, etc.)
        if file.filename.lower().endswith((".xls", ".xlsx")):
            dto: DocParserContextOut = await handler.extract_only(user_id=user_id, folder=folder, file=file)
        else:
            dto: DocParserContextOut = await handler.full_pipeline(user_id=user_id, folder=folder, file=file)

        print(f"dto.file_path: {dto.file_path}")

        # 4) Persist JSONL & Markdown on disk
        json_name, md_name = await handler.save_results(
            dto=dto,
            unique_filename=Path(dto.file_path).name,
            user_id=user_id, 
            folder=folder,
        )

        # 5) Return your typed response
        return ResponseModel(
            message="PDF extracted successfully",
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
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        # Asynchronously save the uploaded PDF
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)
        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF uploaded successfully",
                "filename": unique_filename,
                "file_path": file_path
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
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    try:
        # Process the PDF via the extraction pipeline
        pipeline = PDFExtractionPipeline(file_path)
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
        if os.path.exists(file_path):
            os.unlink(file_path)
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
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    try:
        # Process the PDF via the extraction pipeline
        pipeline = PDFExtractionPipeline(file_path)
        ocr_file_path = pipeline.ocr_pdf(settings.OUTPUT_DIR)
        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF OCR completed successfully",
                "ocr_file_path": ocr_file_path
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
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    try:
        # Asynchronously save the uploaded PDF
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)

        # Process the PDF via the extraction pipeline
        pipeline = PDFExtractionPipeline(file_path)
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
        if os.path.exists(file_path):
            os.unlink(file_path)
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
