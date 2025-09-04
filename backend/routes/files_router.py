# backend/routes/files.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from backend.deps.security import get_verified_principal, Principal
from backend.services.extractor_services import ExtractJobService
from backend.utils.storage_paths import fs_path_from_key

from backend.db.base import session_manager
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_db_session():
    async with session_manager.create_session() as session:
        yield session


async def get_extract_job(db: AsyncSession = Depends(get_db_session)):
    return ExtractJobService(db)


def _safe_join(storage_key: str) -> Path:
    # basic traversal guard
    p = fs_path_from_key(storage_key).resolve()
    # => resolves to STORAGE_BASE_DIR
    base = Path(fs_path_from_key("")).resolve()
    if base not in p.parents and p != base:
        raise HTTPException(400, "Invalid path")
    return p


@router.get("/{job_id}/pages/{page_index}", response_class=FileResponse)
async def get_page_image(
    job_id: str,
    page_index: int,
    principal: Principal = Depends(get_verified_principal),
    job_service: ExtractJobService = Depends(get_extract_job),
):
    logger.info(f"[extractor] get_page_image {job_id}/{page_index}")

    # Enforce access
    job = await job_service.get_by_id(job_id)
    # Choose your policy: strict tenant, or allow creator
    if principal.tenant_id and job.tenant_id != principal.tenant_id and job.created_by_user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Not found")

    # Build storage key from canonical pattern
    storage_key = f"jobs/{job_id}/pages/{page_index:04d}.jpeg"
    fpath = _safe_join(storage_key)
    logger.info(f"fpath: {fpath}")
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Optionally: add cache headers
    return FileResponse(
        path=fpath,
        media_type="image/jpeg",
        filename=f"{job_id}-{page_index:04d}.jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
