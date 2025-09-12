
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


class ExtractResultService(BaseService):
    """Enhanced service for ExtractResult with complete CRUD operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ExtractResult)

    async def create_result(self, data: ExtractResultCreate) -> ExtractResult:
        """Create a new extract result"""
        try:
            result = ExtractResult(**data.model_dump())
            self.db.add(result)
            await self.db.commit()
            await self.db.refresh(result)

            logger.info(f"Created result for job {result.job_id}")
            return result

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating result: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Result already exists for this job"
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating result: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create result"
            )

    async def update_result(self, job_id: str, data: ExtractResultUpdate) -> ExtractResult:
        """Update an existing result"""
        try:
            result = await self.get_by_job_id(job_id)

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(result, key, value)

            await self.db.commit()
            await self.db.refresh(result)

            logger.info(f"Updated result for job {job_id}")
            return result

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating result for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update result"
            )

    async def upsert(self, data: ExtractResultUpsert) -> ExtractResult:
        """Upsert result with enhanced error handling"""
        try:
            payload = data.model_dump()

            # PostgreSQL UPSERT
            stmt = (
                insert(ExtractResult)
                .values(**payload)
                .on_conflict_do_update(
                    index_elements=[ExtractResult.job_id],
                    set_={k: v for k, v in payload.items() if k != "job_id"},
                )
            )

            await self.db.execute(stmt)
            await self.db.commit()

            # Fetch the updated/created result
            result = await self.db.get(ExtractResult, data.job_id)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Upsert operation failed"
                )

            logger.info(f"Upserted result for job {data.job_id}")
            return result

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error upserting result for job {data.job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upsert result"
            )

    async def get_by_job_id(self, job_id: str) -> ExtractResult:
        """Get result by job ID"""
        try:
            result = await self.db.get(ExtractResult, job_id)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Result for job {job_id} not found"
                )
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching result for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch result"
            )

    async def delete_result(self, job_id: str) -> bool:
        """Delete result by job ID"""
        try:
            result = await self.get_by_job_id(job_id)
            await self.db.delete(result)
            await self.db.commit()

            logger.info(f"Deleted result for job {job_id}")
            return True

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting result for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete result"
            )

    async def get_results_by_jobs(self, job_ids: List[str]) -> List[ExtractResult]:
        """Get results for multiple jobs"""
        try:
            stmt = select(ExtractResult).where(
                ExtractResult.job_id.in_(job_ids))
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error fetching results for jobs {job_ids}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch results"
            )

    async def get_results_by_user_or_tenant(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ExtractResult]:
        try:
            stmt = (
                select(ExtractResult)
                .join(ExtractResult.job)
                .options(selectinload(ExtractResult.job))
            )

            conditions = []
            if user_id:
                conditions.append(ExtractJob.created_by_user_id == user_id)
            if tenant_id:
                conditions.append(ExtractJob.tenant_id == tenant_id)

            if conditions:
                stmt = stmt.where(or_(*conditions))

            stmt = stmt.order_by(ExtractResult.created_at.desc()).limit(
                limit).offset(offset)

            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error fetching results by user or tenant: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch results"
            )
