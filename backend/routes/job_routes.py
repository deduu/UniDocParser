# routers/extractor.py
import logging
from uuid import UUID
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func, select

from backend.db.services import (
    ExtractJobService,
    ExtractPageService,
    ExtractResultService,
    ExtractorService,
)
from backend.schemas.extractor import (
    ExtractJobCreate,
    ExtractJobUpdate,
    ExtractJobResponse,
    ExtractJobWithPages,
    ExtractJobWithResult,
    ExtractJobComplete,
    ExtractJobFilter,
    ExtractPageCreate,
    ExtractPageUpdate,
    ExtractPageResponse,
    ExtractPageFilter,
    ExtractResultCreate,
    ExtractResultUpdate,
    ExtractResultUpsert,
    ExtractResultResponse,
    JobProcessingComplete,
    BulkJobStatusUpdate,
    TenantStatistics,
    CompleteJobSummary,
    PaginationParams,
    JobStatus
)
from backend.db.doc_parser import ExtractJob, ExtractPage, ExtractResult
from backend.core.config import settings
from backend.db.base import session_manager
from backend.deps.security import Principal, get_verified_principal

from backend.schemas.response import ResponseModel
from backend.utils.files import load_extraction_result_from_file

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get services


async def get_db_session():
    async with session_manager.create_session() as session:
        yield session


async def get_job_service(db: AsyncSession = Depends(get_db_session)) -> ExtractJobService:
    return ExtractJobService(db)


async def get_page_service(db: AsyncSession = Depends(get_db_session)) -> ExtractPageService:
    return ExtractPageService(db)


async def get_result_service(db: AsyncSession = Depends(get_db_session)) -> ExtractResultService:
    return ExtractResultService(db)


async def get_extractor_service(db: AsyncSession = Depends(get_db_session)) -> ExtractorService:
    return ExtractorService(db)

# === JOB ENDPOINTS ===


@router.post("/jobs", response_model=ExtractJobResponse)
async def create_job(
    job_data: ExtractJobCreate,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Create a new extraction job"""
    return await service.create_job(job_data, principal.user_id)


@router.get("/jobs", response_model=List[ExtractJobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    file_name: Optional[str] = Query(None, description="Filter by file name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """List jobs for current tenant with filtering"""
    filters = ExtractJobFilter()
    if status:
        filters.status = [JobStatus(status)]
    if created_by:
        filters.created_by_user_id = created_by
    if file_name:
        filters.source_file_name = file_name

    return await service.list_by_tenant(
        principal.tenant_id,
        filters=filters,
        skip=skip,
        limit=limit
    )


@router.get("/jobs/{job_id}", response_model=ExtractJobResponse)
async def get_job(
    job_id: str,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get a specific job"""
    return await service.assert_access(job_id, principal.tenant_id)


@router.get("/jobs/{job_id}/complete", response_model=ExtractJobComplete)
async def get_job_complete(
    job_id: str,
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get job with pages and result"""
    job = await extractor_service.job_service.get_job_with_pages(job_id, principal.tenant_id)
    try:
        result = await extractor_service.result_service.get_by_job_id(job_id)
    except HTTPException:
        result = None

    # Temporarily attach result to the job object (or pass separately)
    job.result = result

    # Now Pydantic can walk relationships
    return ExtractJobComplete.model_validate(job)


@router.get("/jobs/{job_id}/summary", response_model=CompleteJobSummary)
async def get_job_summary(
    job_id: str,
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get comprehensive job summary"""
    return await extractor_service.get_job_summary(job_id, principal.tenant_id)


@router.put("/jobs/{job_id}", response_model=ExtractJobResponse)
async def update_job(
    job_id: str,
    job_data: ExtractJobUpdate,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Update a specific job"""
    return await service.update_job(job_id, job_data, principal.tenant_id)


@router.patch("/jobs/{job_id}/status")
async def update_job_status(
    job_id: str,
    status: JobStatus,
    error_message: Optional[str] = None,
    page_count: Optional[int] = None,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Update job status with optional error and page count"""
    # Verify access first
    await service.assert_access(job_id, principal.tenant_id)
    return await service.set_status(job_id, status.value, error_message, page_count)


@router.post("/jobs/{job_id}/cancel", response_model=ExtractJobResponse)
async def cancel_job(
    job_id: str,
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Cancel a running or queued job"""
    return await extractor_service.cancel_job(job_id, principal.tenant_id)


@router.post("/jobs/{job_id}/retry", response_model=ExtractJobResponse)
async def retry_job(
    job_id: str,
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Retry a failed job"""
    return await extractor_service.retry_job(job_id, principal.tenant_id)


@router.delete("/jobs/{job_id:uuid}")
async def delete_job(
    job_id: UUID,
    complete: bool = Query(False, description="Delete all related data"),
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Delete a job (optionally with all related data)"""

    job_id_str = str(job_id)  # your DB PK is a string
    if complete:
        await extractor_service.delete_complete_job(job_id_str, principal.tenant_id)
    else:
        await extractor_service.job_service.delete_job(job_id_str, principal.tenant_id)

    return {"message": "Job deleted successfully"}

# === PAGE ENDPOINTS ===


@router.get("/jobs/{job_id}/pages", response_model=List[ExtractPageResponse])
async def get_job_pages(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get pages for a specific job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)
    return await service.get_pages_by_job(job_id, skip, limit)


@router.get("/jobs/{job_id}/pages/{page_index}", response_model=ExtractPageResponse)
async def get_job_page(
    job_id: str,
    page_index: int,
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get a specific page by index"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    page = await service.get_page_by_index(job_id, page_index)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_index} not found for job {job_id}"
        )
    return page


@router.post("/jobs/{job_id}/pages", response_model=List[ExtractPageResponse])
async def create_job_pages(
    job_id: str,
    pages: List[ExtractPageCreate],
    replace_existing: bool = Query(
        False, description="Replace all existing pages"),
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Create or replace pages for a job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    if replace_existing:
        # Set job_id for all pages
        for page in pages:
            page.job_id = job_id
        await service.replace_pages(job_id, pages)
        return await service.get_pages_by_job(job_id)
    else:
        # Add job_id and create pages
        for page in pages:
            page.job_id = job_id
        return await service.bulk_create_pages(pages)


@router.put("/pages/{page_id}", response_model=ExtractPageResponse)
async def update_page(
    page_id: str,
    page_data: ExtractPageUpdate,
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Update a specific page"""
    # Get page and verify job access
    page = await service.get_by_id(page_id)
    await job_service.assert_access(page.job_id, principal.tenant_id)

    return await service.update_page(page_id, page_data)


@router.delete("/jobs/{job_id}/pages")
async def delete_job_pages(
    job_id: str,
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Delete all pages for a job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    deleted_count = await service.delete_pages_by_job(job_id)
    return {"message": f"Deleted {deleted_count} pages"}


@router.get("/jobs/{job_id}/pages/search", response_model=List[ExtractPageResponse])
async def search_pages(
    job_id: str,
    q: str = Query(..., min_length=1, description="Search term"),
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Search pages by content"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    return await service.search_pages_by_content(job_id, q)

# === RESULT ENDPOINTS ===


@router.get("/jobs/{job_id}/result", response_model=ExtractResultResponse)
async def get_job_result(
    job_id: str,
    service: ExtractResultService = Depends(get_result_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get result for a specific job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    return await service.get_by_job_id(job_id)


@router.post("/jobs/{job_id}/result", response_model=ExtractResultResponse)
async def create_job_result(
    job_id: str,
    result_data: ExtractResultCreate,
    service: ExtractResultService = Depends(get_result_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Create result for a job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    # Ensure job_id matches
    result_data.job_id = job_id
    return await service.create_result(result_data)


@router.put("/jobs/{job_id}/result", response_model=ExtractResultResponse)
async def upsert_job_result(
    job_id: str,
    result_data: ExtractResultUpsert,
    service: ExtractResultService = Depends(get_result_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Create or update result for a job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    # Ensure job_id matches
    result_data.job_id = job_id
    return await service.upsert(result_data)


@router.delete("/jobs/{job_id}/result")
async def delete_job_result(
    job_id: str,
    service: ExtractResultService = Depends(get_result_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Delete result for a job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    await service.delete_result(job_id)
    return {"message": "Result deleted successfully"}


@router.get("/jobs/{job_id}/extract-summary", response_model=ResponseModel)
async def get_extracted_summary(
    job_id: str,
    job_service: ExtractJobService = Depends(get_job_service),
    result_service: ExtractResultService = Depends(get_result_service),
    principal: Principal = Depends(get_verified_principal)
):
    """
    Get extracted result summary from DB + JSON file (as DocParserContextOut).
    """
    # Step 1: Enforce access
    job = await job_service.assert_access(job_id, principal.tenant_id)

    # Step 2: Fetch extract result
    try:
        result = await result_service.get_by_job_id(job_id)
    except HTTPException:
        raise HTTPException(
            status_code=404, detail="Extraction result not found.")

    # Step 3: Load structured content from saved JSON
    extraction_result = None
    if result.json_url:
        try:
            extraction_result = load_extraction_result_from_file(
                result.json_url)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, detail="Result file not found.")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to load result: {str(e)}")

    # Step 4: Return response
    return ResponseModel(
        message="Document previously extracted",
        job_id=job_id,
        extraction_result=extraction_result,
        json_output=result.json_url,
        markdown_output=result.markdown_url,
    )

# === COMPOSITE OPERATIONS ===


@router.post("/jobs/complete", response_model=ExtractJobResponse)
async def create_complete_job(
    job_data: ExtractJobCreate,
    pages: Optional[List[ExtractPageCreate]] = None,
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Create a job with optional pages in a single transaction"""
    return await extractor_service.create_complete_job(
        job_data,
        principal.user_id,
        pages or []
    )


@router.post("/jobs/{job_id}/complete-processing")
async def complete_job_processing(
    job_id: str,
    completion_data: JobProcessingComplete,
    extractor_service: ExtractorService = Depends(get_extractor_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Complete job processing with pages and result"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    # Ensure job_id is set in result data
    completion_data.result.job_id = job_id

    return await extractor_service.process_job_completion(
        job_id,
        completion_data.pages,
        completion_data.result,
        completion_data.final_status.value
    )

# === BULK OPERATIONS ===


@router.post("/jobs/bulk-status-update")
async def bulk_update_job_status(
    bulk_update: BulkJobStatusUpdate,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Bulk update job status"""
    updated_count = await service.bulk_update_status(
        bulk_update.job_ids,
        bulk_update.status.value,
        principal.tenant_id
    )
    return {"message": f"Updated {updated_count} jobs"}


@router.delete("/jobs/bulk-delete")
async def bulk_delete_jobs(
    job_ids: List[str] = Body(...),
    allow_running: bool = False,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal),
):
    tenant_id = principal.tenant_id or principal.user_id
    result = await service.bulk_delete_by_ids(tenant_id, job_ids, allow_running=allow_running)
    return result

# === STATISTICS AND MONITORING ===


@router.get("/stats", response_model=TenantStatistics)
async def get_tenant_statistics(
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get comprehensive statistics for current tenant"""
    return await extractor_service.get_tenant_statistics(principal.tenant_id)


@router.get("/jobs/count")
async def get_job_count(
    status: Optional[str] = Query(None),
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get job count by status"""
    count = await service.count_by_tenant(principal.tenant_id, status)
    return {"count": count, "status": status}


@router.post("/cleanup/failed-jobs")
async def cleanup_failed_jobs(
    older_than_days: int = Query(
        7, ge=0, description="Delete failed jobs older than N days (use 0 to delete all failed jobs)"),
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Clean up old failed jobs and their data"""
    try:
        logger.info(
            f"Cleanup request: tenant_id={principal.tenant_id}, older_than_days={older_than_days}")

        cleaned_count = await extractor_service.cleanup_failed_jobs(
            principal.tenant_id,
            older_than_days
        )

        return {"message": f"Cleaned up {cleaned_count} failed jobs"}

    except Exception as e:
        logger.error(f"Cleanup endpoint error: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Provide more specific error message
        if isinstance(e, RuntimeError):
            detail = str(e)
        else:
            detail = f"Failed to cleanup failed jobs: {str(e)}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
# backend/routes/jobs.py


@router.delete("/jobs/by-user/{user_id}")
async def delete_jobs_by_user(
    user_id: str,
    allow_running: bool = Query(False),
    principal: Principal = Depends(get_verified_principal),
    service: ExtractJobService = Depends(get_job_service),
):
    # enforce tenant scope from principal
    return await service.delete_all_for_user(
        tenant_id=principal.tenant_id,
        user_id=user_id,
        allow_running=allow_running,
    )


# === HEALTH AND MONITORING ===


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session)
):
    """Health check endpoint"""
    try:
        # Simple query to test database connectivity
        result = await db.execute(select(func.now()))
        db_time = result.scalar()

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": db_time
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@router.get("/jobs/{job_id}/validate")
async def validate_job(
    job_id: str,
    job_service: ExtractJobService = Depends(get_job_service),
    page_service: ExtractPageService = Depends(get_page_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Validate job data integrity"""
    # Verify job access
    job = await job_service.assert_access(job_id, principal.tenant_id)

    errors = []
    warnings = []

    # Check page count consistency
    actual_page_count = await page_service.get_page_count(job_id)
    if job.page_count_actual and job.page_count_actual != actual_page_count:
        errors.append(
            f"Page count mismatch: expected {job.page_count_actual}, found {actual_page_count}")

    # Check status consistency
    if job.status == "succeeded" and actual_page_count == 0:
        warnings.append("Job marked as succeeded but has no pages")

    # Check for gaps in page indices
    pages = await page_service.get_pages_by_job(job_id, limit=1000)
    page_indices = sorted([p.page_index for p in pages])
    expected_indices = list(range(len(page_indices)))

    if page_indices != expected_indices:
        missing = set(expected_indices) - set(page_indices)
        if missing:
            errors.append(f"Missing page indices: {sorted(missing)}")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "page_count": actual_page_count,
        "validation_timestamp": func.now()
    }

# === BACKGROUND TASK ENDPOINTS ===


@router.post("/jobs/{job_id}/process")
async def start_job_processing(
    job_id: str,
    background_tasks: BackgroundTasks,
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Start background processing for a job"""
    # Verify job access and status
    job = await service.assert_access(job_id, principal.tenant_id)

    if job.status != "queued":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process job with status '{job.status}'"
        )

    # Update status to running
    await service.set_status(job_id, "running")

    # Add background task (you would implement the actual processing function)
    # background_tasks.add_task(process_document_extraction, job_id)

    return {"message": "Job processing started", "job_id": job_id}

# === ADVANCED FILTERING ===


@router.post("/jobs/search", response_model=List[ExtractJobResponse])
async def search_jobs(
    filters: ExtractJobFilter,
    pagination: PaginationParams = Depends(),
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Advanced job search with complex filtering"""
    return await service.list_by_tenant(
        principal.tenant_id,
        filters=filters,
        skip=pagination.skip,
        limit=pagination.limit
    )


@router.get("/jobs/{job_id}/pages/count")
async def get_page_count(
    job_id: str,
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get page count for a job"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    count = await service.get_page_count(job_id)
    return {"job_id": job_id, "page_count": count}

# === EXPORT OPERATIONS ===


@router.get("/extract/results", response_model=List[ExtractResultResponse])
async def list_results(
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    extractor_service: ExtractorService = Depends(get_extractor_service),
):
    return await extractor_service.get_extraction_results(
        user_id=user_id,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset
    )


@router.get("/jobs/{job_id}/export/markdown")
async def export_job_markdown(
    job_id: str,
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Export all pages as combined markdown"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    pages = await service.get_pages_by_job(job_id, limit=10000)

    # Combine all markdown content
    combined_markdown = []
    for page in sorted(pages, key=lambda p: p.page_index):
        if page.markdown:
            combined_markdown.append(
                f"## Page {page.page_index + 1}\n\n{page.markdown}\n\n")

    return {
        "job_id": job_id,
        "markdown": "\n".join(combined_markdown),
        "page_count": len(pages)
    }


@router.get("/jobs/{job_id}/export/text")
async def export_job_text(
    job_id: str,
    service: ExtractPageService = Depends(get_page_service),
    job_service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Export all pages as combined plain text"""
    # Verify job access
    await job_service.assert_access(job_id, principal.tenant_id)

    pages = await service.get_pages_by_job(job_id, limit=10000)

    # Combine all text content
    combined_text = []
    for page in sorted(pages, key=lambda p: p.page_index):
        if page.text:
            combined_text.append(
                f"=== Page {page.page_index + 1} ===\n\n{page.text}\n\n")

    return {
        "job_id": job_id,
        "text": "\n".join(combined_text),
        "page_count": len(pages)
    }

# === ADMINISTRATIVE ENDPOINTS ===


@router.get("/admin/jobs", response_model=List[ExtractJobResponse])
async def admin_list_all_jobs(
    tenant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    service: ExtractJobService = Depends(get_job_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Admin endpoint to list jobs across tenants"""
    # This would need additional permission checking in a real app
    if not principal.is_admin:  # Assuming you have admin role checking
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    filters = {}
    if tenant_id:
        filters['tenant_id'] = tenant_id
    if status:
        filters['status'] = status

    return await service.filter_by(filters, skip=skip, limit=limit, order_by="created_at")


@router.get("/admin/stats")
async def admin_global_statistics(
    extractor_service: ExtractorService = Depends(get_extractor_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Admin endpoint for global statistics"""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # This would aggregate stats across all tenants
    # Implementation depends on your specific requirements
    db = extractor_service.db

    # Total jobs across all tenants
    total_jobs_result = await db.execute(select(func.count(ExtractJob.id)))
    total_jobs = total_jobs_result.scalar() or 0

    # Jobs by status across all tenants
    from sqlalchemy import case
    status_query = select(
        ExtractJob.status,
        func.count(ExtractJob.id).label('count')
    ).group_by(ExtractJob.status)

    status_result = await db.execute(status_query)
    status_counts = {row.status: row.count for row in status_result.fetchall()}

    return {
        "total_jobs": total_jobs,
        "status_counts": status_counts,
        "timestamp": func.now()
    }

# # === ERROR HANDLERS ===


# @router.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     """Custom HTTP exception handler"""
#     return {
#         "error": exc.detail,
#         "status_code": exc.status_code,
#         "timestamp": func.now()
#     }


# @router.exception_handler(ValueError)
# async def value_error_handler(request, exc):
#     """Handle validation errors"""
#     return HTTPException(
#         status_code=status.HTTP_400_BAD_REQUEST,
#         detail=f"Validation error: {str(exc)}"
#     )

# === UTILITY ENDPOINTS ===


@router.get("/jobs/{job_id}/progress")
async def get_job_progress(
    job_id: str,
    service: ExtractJobService = Depends(get_job_service),
    page_service: ExtractPageService = Depends(get_page_service),
    principal: Principal = Depends(get_verified_principal)
):
    """Get job processing progress"""
    job = await service.assert_access(job_id, principal.tenant_id)

    if job.status in ["succeeded", "failed", "canceled"]:
        progress = 100 if job.status == "succeeded" else 0
    elif job.status == "running":
        if job.page_count_est:
            actual_pages = await page_service.get_page_count(job_id)
            progress = min(100, int((actual_pages / job.page_count_est) * 100))
        else:
            progress = 50  # Indeterminate progress
    else:
        progress = 0  # Queued

    return {
        "job_id": job_id,
        "status": job.status,
        "progress_percentage": progress,
        "estimated_pages": job.page_count_est,
        "processed_pages": job.page_count_actual,
        "error_message": job.error_message
    }

# === WEBHOOK ENDPOINTS (for external integrations) ===


@router.post("/webhooks/job-status")
async def job_status_webhook(
    job_id: str,
    status: JobStatus,
    error_message: Optional[str] = None,
    processing_time: Optional[int] = None,
    service: ExtractJobService = Depends(get_job_service),
    # Add webhook authentication here
):
    """Webhook endpoint for external services to update job status"""
    # This would need proper webhook authentication in a real app

    await service.set_status(
        job_id,
        status.value,
        error_message
    )

    return {"message": "Status updated", "job_id": job_id, "status": status}
