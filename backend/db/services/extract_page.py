# services/extract_page.py
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


class ExtractPageService(BaseService):
    """Enhanced service for ExtractPage with complete CRUD operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ExtractPage)

    async def create_page(self, data: ExtractPageCreate) -> ExtractPage:
        """Create a single page"""
        return await self.create(data)

    async def get_pages_by_job(self, job_id: str, skip: int = 0, limit: int = 100) -> List[ExtractPage]:
        """Get pages for a specific job with pagination"""
        try:
            stmt = (
                select(ExtractPage)
                .where(ExtractPage.job_id == job_id)
                .order_by(ExtractPage.page_index)
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error fetching pages for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch pages"
            )

    async def get_page_by_index(self, job_id: str, page_index: int) -> Optional[ExtractPage]:
        """Get specific page by job and index"""
        try:
            stmt = select(ExtractPage).where(
                and_(
                    ExtractPage.job_id == job_id,
                    ExtractPage.page_index == page_index
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                f"Error fetching page {page_index} for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch page"
            )

    async def update_page(self, page_id: str, data: ExtractPageUpdate) -> ExtractPage:
        """Update a specific page"""
        try:
            page = await self.get_by_id(page_id)

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(page, key, value)

            await self.db.commit()
            await self.db.refresh(page)

            logger.info(f"Updated page {page_id}")
            return page

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating page {page_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update page"
            )

    async def replace_pages(self, job_id: str, pages: List[ExtractPageCreate]) -> int:
        """Replace all pages for a job in a single transaction"""
        try:
            async with self.transaction():
                # Delete existing pages
                await self.db.execute(
                    delete(ExtractPage).where(ExtractPage.job_id == job_id)
                )

                # Insert new pages
                if pages:
                    page_objects = []
                    for i, page_data in enumerate(pages):
                        page_dict = page_data.model_dump()
                        page_dict['job_id'] = job_id
                        # Ensure page_index is set correctly
                        if 'page_index' not in page_dict:
                            page_dict['page_index'] = i
                        page_objects.append(ExtractPage(**page_dict))

                    self.db.add_all(page_objects)

                logger.info(f"Replaced {len(pages)} pages for job {job_id}")
                return len(pages)

        except Exception as e:
            logger.error(f"Error replacing pages for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to replace pages"
            )

    async def bulk_create_pages(self, pages: List[ExtractPageCreate]) -> List[ExtractPage]:
        """Bulk create pages with rollback on any failure"""
        try:
            page_objects = [ExtractPage(**page.model_dump()) for page in pages]
            self.db.add_all(page_objects)
            await self.db.commit()

            # Refresh all objects
            for page in page_objects:
                await self.db.refresh(page)

            logger.info(f"Bulk created {len(page_objects)} pages")
            return page_objects

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error in bulk page creation: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page integrity constraint violation"
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error bulk creating pages: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create pages"
            )

    async def delete_pages_by_job(self, job_id: str) -> int:
        """Delete all pages for a job"""
        try:
            stmt = delete(ExtractPage).where(ExtractPage.job_id == job_id)
            result = await self.db.execute(stmt)
            await self.db.commit()

            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} pages for job {job_id}")
            return deleted_count

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting pages for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete pages"
            )

    async def get_page_count(self, job_id: str) -> int:
        """Get total page count for a job"""
        try:
            stmt = select(func.count(ExtractPage.id)).where(
                ExtractPage.job_id == job_id)
            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting pages for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to count pages"
            )

    async def search_pages_by_content(self, job_id: str, search_term: str) -> List[ExtractPage]:
        """Search pages by text content"""
        try:
            stmt = (
                select(ExtractPage)
                .where(
                    and_(
                        ExtractPage.job_id == job_id,
                        or_(
                            ExtractPage.text.ilike(f"%{search_term}%"),
                            ExtractPage.markdown.ilike(f"%{search_term}%")
                        )
                    )
                )
                .order_by(ExtractPage.page_index)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error searching pages for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search pages"
            )
