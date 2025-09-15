# services/extract_orchestrator.py
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload

from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager

from backend.services.base_service import BaseService, PKType
from backend.db.doc_parser import ExtractJob, ExtractPage, ExtractResult
from backend.schemas.extractor import (
    ExtractJobCreate,
    ExtractJobUpdate,
    ExtractPageCreate,
    ExtractPageUpdate,
    ExtractResultCreate,
    ExtractResultUpdate,
    ExtractResultUpsert,
    ExtractResultResponse,
    ExtractJobFilter,
    ExtractPageFilter,

)
from backend.utils.safe_paths import fs_path_from_key, safe_join, output_path_from_key
from backend.db.services import (
    ExtractJobService,
    ExtractPageService,
    ExtractResultService
)

logger = logging.getLogger(__name__)

_ALLOWED_STATUS = {"queued", "running", "succeeded", "failed", "canceled"}
_VALID_TRANSITIONS = {
    "queued": {"running", "canceled"},
    "running": {"succeeded", "failed", "canceled"},
    "succeeded": set(),  # final state
    "failed": {"queued"},  # allow retry
    "canceled": {"queued"}  # allow restart
}


class ExtractorService:
    """Composite service that orchestrates all extraction-related operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_service = ExtractJobService(db)
        self.page_service = ExtractPageService(db)
        self.result_service = ExtractResultService(db)

    async def collect_job_file_paths(self, job_id: str, tenant_id: str) -> list[str]:

        await self.job_service.assert_access(job_id, tenant_id)

        paths: list[str] = []

        # Pages
        rows = await self.db.scalars(
            select(ExtractPage.image_url).where(ExtractPage.job_id == job_id)
        )
        for url in rows.all():
            p = safe_join(url, where="fs")
            if p:
                paths.append(str(p))

        # Result
        result = await self.db.get(ExtractResult, job_id)
        if result:
            for url in (result.json_url, result.markdown_url, result.preview_png_url):
                p = safe_join(url, where="output")
                if p:
                    paths.append(str(p))

        return paths

    async def create_complete_job(
        self,
        job_data: ExtractJobCreate,
        created_by_user_id: str,
        pages: Optional[List[ExtractPageCreate]] = None
    ) -> ExtractJob:
        """Create job with optional pages in a single transaction"""
        try:
            async with self.job_service.transaction():
                # Create job
                job = await self.job_service.create_job(job_data, created_by_user_id)

                # Add pages if provided
                if pages:
                    page_objects = []
                    for i, page_data in enumerate(pages):
                        page_dict = page_data.model_dump()
                        page_dict['job_id'] = job.id
                        if 'page_index' not in page_dict:
                            page_dict['page_index'] = i
                        page_objects.append(ExtractPage(**page_dict))

                    self.db.add_all(page_objects)

                logger.info(
                    f"Created complete job {job.id} with {len(pages or [])} pages")
                return job

        except Exception as e:
            logger.error(f"Error creating complete job: {e}")
            raise

    async def get_job_summary(self, job_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive job summary with counts and status"""
        try:
            job = await self.job_service.assert_access(job_id, tenant_id)
            page_count = await self.page_service.get_page_count(job_id)

            # Check if result exists
            try:
                result = await self.result_service.get_by_job_id(job_id)
                has_result = True
            except HTTPException:
                has_result = False
                result = None

            return {
                "job": job,
                "page_count": page_count,
                "has_result": has_result,
                "result": result,
                "summary": {
                    "id": job.id,
                    "status": job.status,
                    "file_name": job.source_file_name,
                    "page_count": page_count,
                    "created_at": job.created_at,
                    "processing_time": result.processing_time if result else None
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting job summary {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get job summary"
            )

    async def delete_complete_job(self, job_id: str, tenant_id: str) -> bool:
        """Delete job and all related data (pages, results) in a single transaction"""
        try:
            async with self.job_service.transaction():
                job = await self.job_service.assert_access(job_id, tenant_id)

                # Prevent deletion of running jobs
                if job.status == "running":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete running job"
                    )

                # Delete pages (cascades automatically, but explicit for clarity)
                await self.db.execute(
                    delete(ExtractPage).where(ExtractPage.job_id == job_id)
                )

                # Delete result (cascades automatically)
                await self.db.execute(
                    delete(ExtractResult).where(ExtractResult.job_id == job_id)
                )

                # Delete job
                await self.db.delete(job)

                logger.info(
                    f"Completely deleted job {job_id} and all related data")
                return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error completely deleting job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete job completely"
            )

    async def process_job_completion(
        self,
        job_id: str,
        pages: List[ExtractPageCreate],
        result_data: ExtractResultUpsert,
        final_status: str = "succeeded"
    ) -> Dict[str, Any]:
        """Complete job processing: update pages, create result, set status"""
        try:
            async with self.job_service.transaction():
                # Replace pages
                page_count = await self.page_service.replace_pages(job_id, pages)

                # Upsert result
                result = await self.result_service.upsert(result_data)

                # Update job status and page count
                job = await self.job_service.set_status(
                    job_id,
                    final_status,
                    page_count=page_count
                )

                logger.info(f"Completed processing for job {job_id}")
                return {
                    "job": job,
                    "result": result,
                    "page_count": page_count
                }

        except Exception as e:
            logger.error(f"Error processing job completion {job_id}: {e}")
            # Try to set job to failed status
            try:
                await self.job_service.set_status(job_id, "failed", str(e))
            except:
                pass  # Don't fail if we can't update status
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete job processing"
            )

    async def get_tenant_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a tenant"""
        try:
            # Job counts by status
            status_counts = {}
            for status in _ALLOWED_STATUS:
                count = await self.job_service.count_by_tenant(tenant_id, status)
                status_counts[status] = count

            # Total jobs
            total_jobs = await self.job_service.count_by_tenant(tenant_id)

            # Recent jobs (last 10)
            recent_jobs = await self.job_service.list_by_tenant(
                tenant_id, limit=10
            )

            # Total pages processed
            stmt = (
                select(func.sum(ExtractJob.page_count_actual))
                .where(
                    and_(
                        ExtractJob.tenant_id == tenant_id,
                        ExtractJob.page_count_actual.isnot(None)
                    )
                )
            )
            result = await self.db.execute(stmt)
            total_pages = result.scalar() or 0

            # Total storage used
            stmt = (
                select(func.sum(ExtractResult.bytes_stored))
                .join(ExtractJob, ExtractResult.job_id == ExtractJob.id)
                .where(
                    and_(
                        ExtractJob.tenant_id == tenant_id,
                        ExtractResult.bytes_stored.isnot(None)
                    )
                )
            )
            result = await self.db.execute(stmt)
            total_bytes = result.scalar() or 0

            return {
                "tenant_id": tenant_id,
                "total_jobs": total_jobs,
                "status_counts": status_counts,
                "total_pages_processed": total_pages,
                "total_bytes_stored": total_bytes,
                "recent_jobs": [
                    {
                        "id": job.id,
                        "status": job.status,
                        "file_name": job.source_file_name,
                        "created_at": job.created_at
                    }
                    for job in recent_jobs
                ]
            }

        except Exception as e:
            logger.error(
                f"Error getting tenant statistics for {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get tenant statistics"
            )

    async def cleanup_failed_jobs(self, tenant_id: str, older_than_days: int = 7) -> int:
        """Clean up old failed jobs and their data"""
        logger.info(
            f"Starting cleanup for tenant {tenant_id}, older_than_days: {older_than_days}")

        try:
            async with self.job_service.transaction():
                # Build the WHERE clause conditionally
                where_conditions = [
                    ExtractJob.tenant_id == tenant_id,
                    ExtractJob.status == "failed"
                ]

                # Only add date filter if older_than_days > 0
                if older_than_days > 0:
                    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
                    where_conditions.append(
                        ExtractJob.created_at < cutoff_date)
                    logger.info(f"Cutoff date: {cutoff_date}")
                else:
                    logger.info("Cleaning ALL failed jobs (no date filter)")

                # Find failed jobs
                stmt = (
                    select(ExtractJob.id)
                    .where(and_(*where_conditions))
                )

                logger.info(f"Executing query to find failed jobs")
                result = await self.db.execute(stmt)
                job_ids = [row[0] for row in result.fetchall()]

                logger.info(f"Found {len(job_ids)} failed jobs to cleanup")

                if not job_ids:
                    logger.info("No failed jobs found to cleanup")
                    return 0

                # Delete pages first (due to foreign key constraints)
                logger.info(f"Deleting pages for {len(job_ids)} jobs")
                pages_result = await self.db.execute(
                    delete(ExtractPage).where(ExtractPage.job_id.in_(job_ids))
                )
                logger.info(f"Deleted {pages_result.rowcount} pages")

                # Delete results
                logger.info(f"Deleting results for {len(job_ids)} jobs")
                results_result = await self.db.execute(
                    delete(ExtractResult).where(
                        ExtractResult.job_id.in_(job_ids))
                )
                logger.info(f"Deleted {results_result.rowcount} results")

                # Delete jobs last
                logger.info(f"Deleting {len(job_ids)} jobs")
                jobs_result = await self.db.execute(
                    delete(ExtractJob).where(ExtractJob.id.in_(job_ids))
                )
                logger.info(f"Deleted {jobs_result.rowcount} jobs")

                logger.info(
                    f"Successfully cleaned up {len(job_ids)} failed jobs for tenant {tenant_id}")
                return len(job_ids)

        except Exception as e:
            logger.error(
                f"Error cleaning up failed jobs for tenant {tenant_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Re-raise the original exception with more context
            raise RuntimeError(f"Cleanup failed: {str(e)}") from e

    async def cancel_job(self, job_id: str, tenant_id: str) -> ExtractJob:
        """Cancel a running or queued job"""
        try:
            job = await self.job_service.assert_access(job_id, tenant_id)

            if job.status not in {"queued", "running"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel job with status '{job.status}'"
                )

            return await self.job_service.set_status(job_id, "canceled")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error canceling job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel job"
            )

    async def retry_job(self, job_id: str, tenant_id: str) -> ExtractJob:
        """Retry a failed job"""
        try:
            async with self.job_service.transaction():
                job = await self.job_service.assert_access(job_id, tenant_id)

                if job.status != "failed":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot retry job with status '{job.status}'"
                    )

                # Clear error message and reset status
                job.status = "queued"
                job.error_message = None
                job.page_count_actual = None

                # Optionally clear existing pages and results
                await self.db.execute(
                    delete(ExtractPage).where(ExtractPage.job_id == job_id)
                )
                await self.db.execute(
                    delete(ExtractResult).where(ExtractResult.job_id == job_id)
                )

                await self.db.refresh(job)
                logger.info(f"Reset job {job_id} for retry")
                return job

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrying job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retry job"
            )

    async def get_extraction_results(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExtractResultResponse]:
        """
        Orchestrator method to get extract results for a user or tenant,
        returned as Pydantic response models.
        """
        try:
            results = await self.result_service.get_results_by_user_or_tenant(
                user_id=user_id,
                tenant_id=tenant_id,
                limit=limit,
                offset=offset
            )

            return [
                ExtractResultResponse(
                    job_id=r.job_id,
                    json_url=r.json_url,
                    markdown_url=r.markdown_url,
                    preview_png_url=r.preview_png_url,
                    bytes_stored=r.bytes_stored,
                    processing_time=r.processing_time,
                    created_at=r.created_at
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error in get_extraction_results: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve extract results"
            )

# Factory functions for dependency injection


def get_extract_job_service(db: AsyncSession) -> ExtractJobService:
    """Factory function for ExtractJobService"""
    return ExtractJobService(db)


def get_extract_page_service(db: AsyncSession) -> ExtractPageService:
    """Factory function for ExtractPageService"""
    return ExtractPageService(db)


def get_extract_result_service(db: AsyncSession) -> ExtractResultService:
    """Factory function for ExtractResultService"""
    return ExtractResultService(db)


def get_extractor_service(db: AsyncSession) -> ExtractorService:
    """Factory function for composite ExtractorService"""
    return ExtractorService(db)


# Utility functions for common operations
async def get_job_with_access_check(
    db: AsyncSession,
    job_id: str,
    tenant_id: str,
    include_pages: bool = False,
    include_result: bool = False
) -> ExtractJob:
    """Utility to get job with access validation and optional eager loading"""
    try:
        stmt = select(ExtractJob).where(
            and_(
                ExtractJob.id == job_id,
                ExtractJob.tenant_id == tenant_id
            )
        )

        if include_pages:
            stmt = stmt.options(selectinload(ExtractJob.pages))

        if include_result:
            stmt = stmt.options(joinedload(ExtractJob.result))

        result = await db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found or access denied"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch job"
        )


async def validate_job_status_transition(
    current_status: str,
    new_status: str
) -> None:
    """Validate status transition is allowed"""
    if new_status not in _ALLOWED_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'"
        )

    if (current_status in _VALID_TRANSITIONS and
            new_status not in _VALID_TRANSITIONS[current_status]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current_status}' to '{new_status}'"
        )


# Error handling decorators
def handle_service_errors(func):
    """Decorator for consistent error handling across service methods"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except IntegrityError as e:
            logger.error(f"Integrity error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity constraint violation"
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Service operation failed: {func.__name__}"
            )
    return wrapper
