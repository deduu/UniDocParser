import os
import uuid
import traceback
import logging
from fastapi import (
    APIRouter, 
    File, 
    UploadFile, 
    HTTPException, 
    BackgroundTasks,
    Form
)
import json
from fastapi.responses import JSONResponse, FileResponse
from backend.services.pdf_extractor import PDFExtractor


logging.basicConfig(level=logging.INFO)
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
    Upload and extract PDF with model selections
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    pdf_path = os.path.join(upload_dir, unique_filename)

    try:
        # Save file
        with open(pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        extraction_result = PDFExtractor.extract_pdf(pdf_path)

        json_output_path, md_output_path = PDFExtractor.save_extraction_results(extraction_result, os.path.join("outputs", f"{unique_filename}"))
        # Simulate extraction with model selections
        # extraction_result = {
        #     "source": unique_filename,
        #     "extraction_model": extraction_model,
        #     "image_model": image_model,
        #     "text_model": text_model,
        #     "pages": [
        #         {
        #             "index": 0, 
        #             "text": "Sample page content extracted using " + extraction_model,
        #             "images": []
        #         }
        #     ]
        # }

        # # Save JSON output
        # json_output_path = os.path.join("outputs", f"{unique_filename}.json")
        # with open(json_output_path, "w") as f:
        #     json.dump(extraction_result, f, indent=2)

        # # Save Markdown output
        # md_output_path = os.path.join("outputs", f"{unique_filename}.md")
        # with open(md_output_path, "w") as f:
        #     f.write(f"# Extracted PDF: {unique_filename}\n\n")
        #     f.write(f"## Extraction Details\n")
        #     f.write(f"- Extraction Model: {extraction_model}\n")
        #     f.write(f"- Image Processing: {image_model}\n")
        #     f.write(f"- Text Processing: {text_model}\n\n")
        #     f.write("## Page Contents\n")
        #     for page in extraction_result["pages"]:
        #         f.write(f"### Page {page['index']}\n")
        #         f.write(page['text'] + "\n\n")

        return {
            "message": "PDF extracted successfully",
            "extraction_result": extraction_result,
            "json_output": json_output_path,
            "markdown_output": md_output_path
        }

    except Exception as e:
        # Error handling
        logger.error(f"Extraction error: {str(e)}")
        logger.error(traceback.format_exc())

        # Clean up potential partial file
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
    file_path = os.path.join("outputs", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
