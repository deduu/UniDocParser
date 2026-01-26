import os
import time
import traceback
import logging
import aiofiles
import asyncio
from PIL.Image import Image
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import io
import base64
import json
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

from backend.core.model_manager import model_manager
from backend.config.settings import get_settings
from backend.pipeline.runner import pipeline_runner

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class PageOut(BaseModel):
    page:  int
    text:  str
    images: List[str]


class ExtractOut(BaseModel):
    source: str
    pages: List[Dict[str, Any]]
    processing_time: float


class ResponseModel(BaseModel):
    message: str
    user_id: str
    folder: str
    extraction_result: Dict[str, Any]
    json_output: str
    markdown_output: str


class ModelPreferencesIn(BaseModel):
    agent_mode: Optional[bool] = None
    fig2tab_model_type: Optional[str] = None
    formatter_model_type: Optional[str] = None
    fig2tab_model_id: Optional[str] = None
    formatter_model_id: Optional[str] = None


class ModelPreferencesOut(BaseModel):
    agent_mode: bool
    fig2tab_model_type: str
    formatter_model_type: str
    fig2tab_model_id: Optional[str] = None
    formatter_model_id: Optional[str] = None


# ------------------------------------------------------------------------------
@router.post("/ocrpdf")
async def ocr_pdf(
    request: Request,
    user_id: str = Form(...),
    folder: str = Form(...),
    file: UploadFile = File(...),
):
    file_path = await _save_upload(file, user_id=user_id, folder=folder)
    context = {
        "user_id": user_id,
        "folder": folder,
        "file_path": file_path,
    }
    result = _run_pipeline("ocr_only_pipeline", context)
    return JSONResponse(content=result)


@router.post("/splitpdf")
async def split_pdf(
    request: Request,
    user_id: str = Form(...),
    folder: str = Form(...),
    file: UploadFile = File(...),
):
    file_path = await _save_upload(file, user_id=user_id, folder=folder)
    context = {
        "user_id": user_id,
        "folder": folder,
        "file_path": file_path,
    }
    result = _run_pipeline("default_pdf_pipeline", context)
    return JSONResponse(content=result)


@router.post(
    "/extractpdf",
    response_model=ResponseModel,
)
async def extract_pdf(
    request: Request,
    user_id: str = Form("test_user"),
    folder: str = Form("test_folder"),
    file: UploadFile = File(...),
    fig2tab_type: Optional[str] = Form(None),
    formatter_type: Optional[str] = Form(None),
    fig2tab_model_id: Optional[str] = Form(None),
    formatter_model_id: Optional[str] = Form(None),
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
        preferences = _resolve_model_preferences(
            request,
            fig2tab_type=fig2tab_type,
            formatter_type=formatter_type,
            fig2tab_model_id=fig2tab_model_id,
            formatter_model_id=formatter_model_id,
        )

        file_path = await _save_upload(file, user_id=user_id, folder=folder)

        # 3) Run the pipeline (Split -> Extract -> Format -> Markdown)
        pipeline_name = "excel_pipeline" if file.filename.lower().endswith((".xls", ".xlsx")) else "default_pdf_pipeline"
        context = {
            "user_id": user_id,
            "folder": folder,
            "file_path": file_path,
            "fig2tab_model_type": preferences["fig2tab_model_type"],
            "formatter_model_type": preferences["formatter_model_type"],
            "fig2tab_model_id": preferences.get("fig2tab_model_id"),
            "formatter_model_id": preferences.get("formatter_model_id"),
        }
        result = _run_pipeline(pipeline_name, context)

        # 4) Persist JSON + Markdown on disk
        print(f"Saving results for user {user_id} in folder {folder}")
        json_output, md_output = await _save_results(
            extraction_result=result,
            unique_filename=Path(file_path).name,
            user_id=user_id,
            folder=folder,
        )

        # 5) Return your typed response
        return ResponseModel(
            message="PDF extracted successfully",
            user_id=user_id,
            folder=folder,
            extraction_result=result,
            json_output=json_output,
            markdown_output=md_output,
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
        # unique_filename = f"{uuid.uuid4()}_{file.filename}"
        unique_filename = file.filename
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, unique_filename)
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
async def extract_pdf_legacy(filename: str):
    file_path = os.path.join(settings.upload_dir, filename)

    try:
        context = {
            "user_id": "legacy_user",
            "folder": "legacy_folder",
            "file_path": file_path,
        }
        result = _run_pipeline("default_pdf_pipeline", context)
        extraction = ExtractOut(**result)
        json_output_path, md_output_path = await _save_results(
            extraction_result=result,
            unique_filename=filename,
            user_id="legacy_user",
            folder="legacy_folder",
        )
        return ResponseModel(
            message="PDF extracted successfully",
            user_id="legacy_user",
            folder="legacy_folder",
            extraction_result=extraction.model_dump(),
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
                "traceback": traceback.format_exc(),
            },
        )


@router.get("/ocr-pdf/{filename}", name="ocr_pdf")
async def ocr_pdf_legacy(filename: str):
    file_path = os.path.join(settings.upload_dir, filename)
    try:
        context = {
            "user_id": "legacy_user",
            "folder": "legacy_folder",
            "file_path": file_path,
        }
        result = _run_pipeline("ocr_only_pipeline", context)
        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF OCR completed successfully",
                "ocr_file_path": result.get("ocr_file_path"),
            },
        )
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "message": "File not found",
                "error": str(e),
            },
        )
    except Exception as e:
        logger.error(f"OCR PDF error: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "message": "PDF OCR failed",
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        )


@router.post("/extract-pdf/")
async def extract_pdf_simple(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    unique_filename = file.filename
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)

        preferences = _resolve_model_preferences(request)
        context = {
            "user_id": "simple_user",
            "folder": "simple_folder",
            "file_path": file_path,
            "fig2tab_model_type": preferences["fig2tab_model_type"],
            "formatter_model_type": preferences["formatter_model_type"],
            "fig2tab_model_id": preferences.get("fig2tab_model_id"),
            "formatter_model_id": preferences.get("formatter_model_id"),
        }
        result = _run_pipeline("default_pdf_pipeline", context)
        clean = convert_pil_to_data_uri(result)

        extraction = ExtractOut(**clean)
        json_output_path, md_output_path = await _save_results(
            extraction_result=result,
            unique_filename=unique_filename,
            user_id="simple_user",
            folder="simple_folder",
        )

        return ResponseModel(
            message="PDF extracted successfully",
            user_id="simple_user",
            folder="simple_folder",
            extraction_result=extraction.model_dump(),
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
                "traceback": traceback.format_exc(),
            },
        )


@router.get("/download/{user_id}/{folder}/{filename}", name="download_file")
async def download_file(user_id: str, folder: str, filename: str):
    file_path = os.path.join("outputs", user_id, folder, filename)
    print(f"file_path: {file_path}")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)


@router.get("/extracted-pdf/json-{filename}", name="extracted_pdf_json")
async def extracted_pdf_json(filename: str):
    """
    Get the JSON output of the extracted PDF.
    """
    json_output_path = os.path.join(settings.output_dir, f"{filename}.jsonl")
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
    md_output_path = os.path.join(settings.output_dir, f"{filename}.md")
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


@router.get("/models", response_model=Dict[str, Any])
async def list_models():
    return {
        "fig2tab": {
            "types": model_manager.list_model_types("fig2tab"),
            "default": model_manager.get_default_model_type("fig2tab"),
        },
        "formatter": {
            "types": model_manager.list_model_types("formatter"),
            "default": model_manager.get_default_model_type("formatter"),
        },
    }


@router.get("/session/preferences", response_model=ModelPreferencesOut)
async def get_model_preferences(request: Request):
    prefs = _resolve_model_preferences(request)
    return ModelPreferencesOut(**prefs)


@router.post("/session/preferences", response_model=ModelPreferencesOut)
async def set_model_preferences(request: Request, prefs_in: ModelPreferencesIn):
    session_prefs = request.session.get("model_preferences", {})
    for key, value in prefs_in.model_dump(exclude_unset=True).items():
        if value is not None:
            session_prefs[key] = value
    request.session["model_preferences"] = session_prefs
    prefs = _resolve_model_preferences(request)
    return ModelPreferencesOut(**prefs)


def _resolve_model_preferences(
    request: Request,
    fig2tab_type: Optional[str] = None,
    formatter_type: Optional[str] = None,
    fig2tab_model_id: Optional[str] = None,
    formatter_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    session_prefs = request.session.get("model_preferences", {})

    resolved_fig2tab_type = (
        fig2tab_type
        or session_prefs.get("fig2tab_model_type")
        or model_manager.get_default_model_type("fig2tab")
    )
    resolved_formatter_type = (
        formatter_type
        or session_prefs.get("formatter_model_type")
        or model_manager.get_default_model_type("formatter")
    )

    resolved = {
        "agent_mode": bool(session_prefs.get("agent_mode", False)),
        "fig2tab_model_type": resolved_fig2tab_type,
        "formatter_model_type": resolved_formatter_type,
        "fig2tab_model_id": fig2tab_model_id or session_prefs.get("fig2tab_model_id"),
        "formatter_model_id": formatter_model_id or session_prefs.get("formatter_model_id"),
    }

    _validate_model_types(resolved["fig2tab_model_type"], resolved["formatter_model_type"])
    return resolved


def _validate_model_types(fig2tab_type: Optional[str], formatter_type: Optional[str]) -> None:
    if fig2tab_type and fig2tab_type not in model_manager.list_model_types("fig2tab"):
        raise HTTPException(
            status_code=400, detail=f"Unknown fig2tab model type: {fig2tab_type}"
        )
    if formatter_type and formatter_type not in model_manager.list_model_types("formatter"):
        raise HTTPException(
            status_code=400, detail=f"Unknown formatter model type: {formatter_type}"
        )


async def _save_upload(file: UploadFile, user_id: str, folder: str) -> str:
    upload_dir = os.path.join(settings.upload_dir, user_id, folder)
    os.makedirs(upload_dir, exist_ok=True)
    dest = os.path.join(upload_dir, file.filename)
    async with aiofiles.open(dest, "wb") as buf:
        await buf.write(await file.read())
    return dest


def _run_pipeline(pipeline_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    result = pipeline_runner.run(pipeline_name, context)
    result["processing_time"] = time.time() - start
    if "source" not in result:
        file_path = context.get("file_path", "")
        result["source"] = os.path.basename(file_path) if file_path else ""
    if "pages" not in result:
        result["pages"] = []
    return result


async def _save_results(
    extraction_result: Dict[str, Any],
    unique_filename: str,
    user_id: str,
    folder: str,
) -> tuple[str, str]:
    output_dir = os.path.join(settings.output_dir, user_id, folder)
    os.makedirs(output_dir, exist_ok=True)

    json_path = Path(output_dir) / f"{unique_filename}.jsonl"
    md_path = Path(output_dir) / f"{unique_filename}.md"

    safe_result = convert_pil_to_data_uri(extraction_result)

    def _write_json():
        with open(json_path, "w") as f:
            json.dump(safe_result, f, indent=2)

    await _run_in_thread(_write_json)

    def _write_md():
        with open(md_path, "w") as md_file:
            for page in safe_result.get("pages", []):
                md_file.write(page.get("markdown", ""))
                md_file.write("\n\n---\n\n")

    await _run_in_thread(_write_md)
    return json_path.name, md_path.name


async def _run_in_thread(fn):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, fn)
