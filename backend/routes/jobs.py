from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import shutil
from typing import Optional, List, Dict, Any

from ..celery_app import celery
from ..tasks import run_extraction
from pydantic import BaseModel

router = APIRouter(prefix="/v1/extractions", tags=["extractions"])

# === Models ===


class StartExtractionOptions(BaseModel):
    extract_text: bool = True
    extract_tables: bool = True
    extract_images: bool = False
    page_numbers: List[int] = []
    destination_id: Optional[str] = None


class StartJobResponse(BaseModel):
    job_id: str
    status_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    state: str          # PENDING | STARTED | PROGRESS | SUCCESS | FAILURE | REVOKED
    progress: int = 0   # 0..100 (from meta)
    label: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# === Helpers ===
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_tmp(upload: UploadFile) -> Path:
    ext = Path(upload.filename or "file").suffix.lower()
    if ext not in (".pdf", ".xls", ".xlsx"):
        raise HTTPException(
            400, "Only PDF or Excel files (.xls/.xlsx) are supported")
    tmp_name = f"{uuid.uuid4().hex}{ext}"
    tmp_path = UPLOAD_DIR / tmp_name
    with tmp_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return tmp_path

# === Routes ===


@router.post("", response_model=StartJobResponse, status_code=202)
async def start_job(file: UploadFile = File(...), options: StartExtractionOptions = None):
    """
    1) Store upload to disk
    2) Enqueue Celery job
    3) Return 202 + job_id immediately
    """
    try:
        file_path = save_upload_tmp(file)
    finally:
        await file.close()

    opts = options.model_dump() if options else {}
    task = run_extraction.delay(str(file_path), opts)

    return StartJobResponse(
        job_id=task.id,
        status_url=f"/v1/extractions/{task.id}",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Poll this from the frontend. When state=SUCCESS, `result` holds your payload.
    """
    res = celery.AsyncResult(job_id)
    meta = res.info if isinstance(res.info, dict) else {}
    progress = int(meta.get("progress", 0))
    label = str(meta.get("label", ""))

    if res.state == "PENDING":
        return JobStatusResponse(job_id=job_id, state=res.state, progress=0, label="Pending")
    elif res.state in ("STARTED", "PROGRESS"):
        return JobStatusResponse(job_id=job_id, state=res.state, progress=progress, label=label)
    elif res.state == "SUCCESS":
        return JobStatusResponse(job_id=job_id, state=res.state, progress=100, label="Completed", result=res.result)
    elif res.failed():
        return JobStatusResponse(job_id=job_id, state="FAILURE", progress=100, label="Failed", error=str(res.result))
    else:
        # REVOKED or other terminal
        return JobStatusResponse(job_id=job_id, state=res.state, progress=progress, label=label)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    celery.control.revoke(job_id, terminate=True)
    return {"ok": True}
