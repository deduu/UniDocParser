# services/extract_job.py
from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload
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
    ExtractJobFilter,
    ExtractPageFilter
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


class ExtractJobService(BaseService):
    """Enhanced service for ExtractJob with complete CRUD operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ExtractJob)

    @asynccontextmanager
    async def transaction(self):
        """Context manager for manual transaction control"""
        try:
            yield self.db
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def create_job(self, data: ExtractJobCreate) -> ExtractJob:
        """Create a new extraction job with validation"""
        try:
            job_data = data.model_dump() if hasattr(data, "model_dump") else dict(data)

            # Validate options_json if provided
            if 'options_json' in job_data and job_data['options_json']:
                if not isinstance(job_data['options_json'], dict):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="options_json must be a valid JSON object"
                    )

            job = ExtractJob(**job_data)
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)

            logger.info(
                f"Created extract job {job.id} for tenant {job.tenant_id}")
            return job

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating job: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity constraint violation"
            )
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error creating job: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create extraction job"
            )

    async def update_source_file_name(self, job_id: str, new_name: str) -> ExtractJob:
        """
        Update the source_file_name of an extract job.
        """
        update_data = ExtractJobUpdate(source_file_name=new_name)
        return await self.update(job_id, update_data)

    async def get_job_with_pages(self, job_id: str, tenant_id: str) -> ExtractJob:
        """Get job with all pages loaded"""
        try:
            stmt = (
                select(ExtractJob)
                .options(selectinload(ExtractJob.pages))
                .where(
                    and_(
                        ExtractJob.id == job_id,
                        ExtractJob.tenant_id == tenant_id
                    )
                )
            )
            result = await self.db.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job {job_id} not found"
                )
            return job

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching job with pages {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch job details"
            )

    async def get_job_with_result(self, job_id: str, tenant_id: str) -> ExtractJob:
        """Get job with result loaded"""
        try:
            stmt = (
                select(ExtractJob)
                .options(joinedload(ExtractJob.result))
                .where(
                    and_(
                        ExtractJob.id == job_id,
                        ExtractJob.tenant_id == tenant_id
                    )
                )
            )
            result = await self.db.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job {job_id} not found"
                )
            return job

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching job with result {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch job with result"
            )

    async def update_job(self, job_id: str, data: ExtractJobUpdate, tenant_id: str) -> ExtractJob:
        """Update job with tenant validation"""
        try:
            job = await self.assert_access(job_id, tenant_id)

            # Validate status transition if status is being updated
            update_data = data.model_dump(exclude_unset=True)
            if 'status' in update_data:
                new_status = update_data['status']
                if new_status not in _ALLOWED_STATUS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status '{new_status}'"
                    )

                current_status = job.status
                if (current_status in _VALID_TRANSITIONS and
                        new_status not in _VALID_TRANSITIONS[current_status]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot transition from '{current_status}' to '{new_status}'"
                    )

            for key, value in update_data.items():
                setattr(job, key, value)

            await self.db.commit()
            await self.db.refresh(job)

            logger.info(f"Updated job {job_id}: {update_data}")
            return job

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update job"
            )

    async def set_status(
        self, job_id: str, status: str, error: Optional[str] = None,
        page_count: Optional[int] = None
    ) -> ExtractJob:
        if status not in _ALLOWED_STATUS:
            raise HTTPException(400, f"invalid status '{status}'")

        update_data = {"status": status}
        if error is not None:
            update_data["error_message"] = error
        if page_count is not None:
            update_data["page_count_actual"] = page_count

        return await self.update(job_id, ExtractJobUpdate(**update_data))

    async def list_by_tenant(
        self,
        tenant_id: str,
        filters: Optional[ExtractJobFilter] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ExtractJob]:
        """List jobs by tenant with optional filtering"""
        try:
            stmt = select(ExtractJob).where(ExtractJob.tenant_id == tenant_id)

            if filters:
                if filters.status:
                    stmt = stmt.where(ExtractJob.status.in_(filters.status))
                if filters.created_by_user_id:
                    stmt = stmt.where(
                        ExtractJob.created_by_user_id == filters.created_by_user_id)
                if filters.source_file_name:
                    stmt = stmt.where(ExtractJob.source_file_name.ilike(
                        f"%{filters.source_file_name}%"))
                if filters.created_after:
                    stmt = stmt.where(ExtractJob.created_at >=
                                      filters.created_after)
                if filters.created_before:
                    stmt = stmt.where(ExtractJob.created_at <=
                                      filters.created_before)

            stmt = stmt.order_by(ExtractJob.created_at.desc()
                                 ).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error listing jobs for tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list jobs"
            )

    async def count_by_tenant(self, tenant_id: str, status: Optional[str] = None) -> int:
        """Count jobs by tenant and optional status"""
        try:
            stmt = select(func.count(ExtractJob.id)).where(
                ExtractJob.tenant_id == tenant_id)
            if status:
                stmt = stmt.where(ExtractJob.status == status)

            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting jobs for tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to count jobs"
            )

    async def assert_access(self, job_id: str, tenant_id: str) -> ExtractJob:
        """Verify user has access to job"""
        job = await self.get_by_id(job_id)
        print("tenant_id: ", job.tenant_id)
        if job.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        return job

    async def delete_job(self, job_id: str, tenant_id: str) -> bool:
        """Delete job with access validation"""
        try:
            job = await self.assert_access(job_id, tenant_id)

            # Prevent deletion of running jobs
            if job.status == "running":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete running job"
                )

            await self.db.delete(job)
            await self.db.commit()

            logger.info(f"Deleted job {job_id}")
            return True

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete job"
            )

    async def bulk_delete_by_ids(
        self,
        tenant_id: str,
        job_ids: List[str],
        *,
        allow_running: bool = False,
        max_batch: int = 1000,
    ) -> Dict[str, Any]:
        """
        Delete multiple jobs in one transaction, scoped to tenant.

        - Skips jobs in 'running' status (unless allow_running=True)
        - Returns detailed breakdown (deleted ids, skipped_running, not_found)
        - Rolls back on unexpected errors
        - Uses SELECT ... FOR UPDATE to avoid races with concurrent updates/deletes
        """
        # Normalize inputs
        unique_ids = list({jid for jid in (job_ids or []) if jid})
        if not unique_ids:
            return {"requested": 0, "matched": 0, "deleted": 0, "skipped_running": [], "not_found": []}

        if len(unique_ids) > max_batch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many ids in one request (>{max_batch})"
            )

        try:
            # 1) Fetch candidate rows for this tenant and lock to prevent races
            #    (e.g., someone marking a job 'running' while we delete)
            stmt = (
                select(ExtractJob.id, ExtractJob.status)
                .where(
                    ExtractJob.tenant_id == tenant_id,
                    ExtractJob.id.in_(unique_ids),
                )
                # Avoid blocking if another tx is touching rows
                .with_for_update(skip_locked=True)
            )
            res = await self.db.execute(stmt)
            rows = res.all()

            matched_ids = [r[0] for r in rows]
            not_found = sorted(set(unique_ids) - set(matched_ids))

            running_ids = [jid for (jid, st) in rows if st == "running"]
            if allow_running:
                deletable_ids = matched_ids
                skipped_running: List[str] = []
            else:
                deletable_ids = [jid for (jid, st) in rows if st != "running"]
                skipped_running = running_ids

            deleted_count = 0
            deleted_ids: List[str] = []

            # 2) Delete only the deletable subset (fast single statement)
            if deletable_ids:
                del_stmt = (
                    delete(ExtractJob)
                    .where(
                        ExtractJob.tenant_id == tenant_id,
                        ExtractJob.id.in_(deletable_ids),
                    )
                )
                res = await self.db.execute(del_stmt.execution_options(synchronize_session=False))
                deleted_count = res.rowcount or 0
                # For reporting, we assume all matched & non-running rows deleted
                # (PG DELETE rowcount is reliable)
                if deleted_count != len(deletable_ids):
                    # Extremely rare (race on rows not locked due to SKIP LOCKED)
                    logger.warning(
                        "Bulk delete rowcount (%s) != deletable_ids (%s)",
                        deleted_count, len(deletable_ids)
                    )
                deleted_ids = deletable_ids

            # 3) Commit the transaction
            await self.db.commit()

            summary = {
                "requested": len(unique_ids),
                "matched": len(matched_ids),
                "deleted": deleted_count,
                "deleted_ids": deleted_ids or [],
                "skipped_running": skipped_running or [],
                "not_found": not_found or [],
            }
            logger.info(
                "Bulk delete summary tenant=%s: %s",
                tenant_id, {k: v for k, v in summary.items() if k !=
                            "deleted_ids"}
            )
            return summary

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Bulk delete failed tenant=%s ids=%s: %s", tenant_id, unique_ids, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk delete jobs",
            )

    async def bulk_update_status(self, job_ids: List[str], status: str, tenant_id: str) -> int:
        """Bulk update job status with tenant validation"""
        try:
            if status not in _ALLOWED_STATUS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status '{status}'"
                )

            stmt = (
                update(ExtractJob)
                .where(
                    and_(
                        ExtractJob.id.in_(job_ids),
                        ExtractJob.tenant_id == tenant_id
                    )
                )
                .values(status=status, updated_at=func.now())
            )

            result = await self.db.execute(stmt)
            await self.db.commit()

            updated_count = result.rowcount
            logger.info(
                f"Bulk updated {updated_count} jobs to status '{status}'")
            return updated_count

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error bulk updating jobs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk update jobs"
            )

    async def delete_all_for_user(
        self,
        tenant_id: str,
        user_id: str,
        *,
        allow_running: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete all jobs created by `user_id` in a given tenant.

        - Skips jobs in 'running' unless allow_running=True
        - Returns a summary dict including deleted ids and skipped_running
        - Uses row locks with SKIP LOCKED to avoid races
        - Relies on DB-level ON DELETE CASCADE to remove pages/results
        """
        try:
            # 1) Lock matching rows to avoid races with concurrent updates/deletes
            sel = (
                select(ExtractJob.id, ExtractJob.status)
                .where(
                    ExtractJob.tenant_id == tenant_id,
                    ExtractJob.created_by_user_id == user_id,
                )
                .with_for_update(skip_locked=True)
            )
            res = await self.db.execute(sel)
            rows = res.all()

            if not rows:
                return {
                    "requested_user_id": user_id,
                    "matched": 0,
                    "deleted": 0,
                    "deleted_ids": [],
                    "skipped_running": [],
                }

            matched_ids = [jid for (jid, _) in rows]
            running_ids = [jid for (jid, st) in rows if st == "running"]

            if allow_running:
                target_ids = matched_ids
                skipped_running: list[str] = []
            else:
                target_ids = [jid for (jid, st) in rows if st != "running"]
                skipped_running = running_ids

            deleted_ids: list[str] = []
            deleted_count = 0

            if target_ids:
                del_stmt = (
                    delete(ExtractJob)
                    .where(ExtractJob.id.in_(target_ids))
                )
                del_res = await self.db.execute(
                    del_stmt.execution_options(synchronize_session=False)
                )
                deleted_count = del_res.rowcount or 0
                deleted_ids = target_ids  # expected == rowcount on Postgres

            await self.db.commit()

            summary = {
                "requested_user_id": user_id,
                "matched": len(matched_ids),
                "deleted": deleted_count,
                "deleted_ids": deleted_ids,
                "skipped_running": skipped_running,
            }
            logger.info("delete_all_for_user summary: %s", {
                        **summary, "deleted_ids": f"{len(deleted_ids)} ids"})
            return summary

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "delete_all_for_user failed tenant=%s user=%s: %s", tenant_id, user_id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete all jobs for user",
            )
