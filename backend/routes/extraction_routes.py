import os
import uuid
import traceback
import logging
import aiofiles
from PIL.Image import Image 
from pydantic import BaseModel
from typing   import List, Dict, Any
import io
import base64
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse

from backend.services.pipeline import PDFExtractionPipeline
from backend.core.config import settings

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
    message:           str
    extraction_result: ExtractOut
    json_output:       str
    markdown_output:   str

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
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
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
        json_output_path, md_output_path = pipeline.save_results(unique_filename, settings.OUTPUT_DIR)

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