import os
import uuid
import traceback
import logging
import aiofiles

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse

from backend.services.pipeline import PDFExtractionPipeline
from backend.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

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
        
        # Save extraction results (JSON and Markdown outputs)
        json_output_path, md_output_path = pipeline.save_results(unique_filename, settings.OUTPUT_DIR)

        return {
            "message": "PDF extracted successfully",
            "extraction_result": extraction_result,
            "json_output": json_output_path,
            "markdown_output": md_output_path
        }
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

@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
