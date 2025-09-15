# services/extractor_services.py
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert  # <-- for upsert
from backend.services.base_service import BaseService
from backend.db.doc_parser import ExtractJob, ExtractPage, ExtractResult
from backend.schemas.extractor import (
    ExtractJobCreate, ExtractJobUpdate, ExtractPageCreate, ExtractResultUpsert
)
from backend.deps.deps import Principal

_ALLOWED_STATUS = {"queued", "running", "succeeded", "failed", "canceled"}


class ExtractJobService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExtractJob)

    async def create_job(self, data: ExtractJobCreate) -> ExtractJob:
        return await self.create(data)

    async def update_source_file_name(self, job_id: str, new_name: str) -> ExtractJob:
        """
        Update the source_file_name of an extract job.
        """
        update_data = ExtractJobUpdate(source_file_name=new_name)
        return await self.update(job_id, update_data)

    async def set_status(self, job_id: str, status: str, error: Optional[str] = None) -> ExtractJob:
        if status not in _ALLOWED_STATUS:
            raise HTTPException(
                status_code=400, detail=f"invalid status '{status}'")
        return await self.update(job_id, ExtractJobUpdate(status=status, error_message=error))

    async def list_by_tenant(
        self, tenant_id: str, status: Optional[str] = None, limit: int = 50
    ) -> List[ExtractJob]:
        stmt = select(ExtractJob).where(ExtractJob.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(ExtractJob.status == status)
        stmt = stmt.order_by(ExtractJob.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def assert_access(self, job_id: str, tenant_id: str) -> ExtractJob:
        job = await self.get_by_id(job_id)
        if job.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return job


class ExtractPageService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExtractPage)

    async def replace_pages(self, job_id: str, pages: List[ExtractPageCreate]) -> int:
        # Single transaction: delete old → bulk insert new → commit once
        await self.db.execute(delete(ExtractPage).where(ExtractPage.job_id == job_id))
        if pages:
            objs = [ExtractPage(**p.model_dump()) for p in pages]
            self.db.add_all(objs)
        await self.db.commit()
        return len(pages)


class ExtractResultService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExtractResult)

    async def upsert(self, data: ExtractResultUpsert) -> ExtractResult:
        payload = data.model_dump()
        # Postgres UPSERT on primary key job_id
        stmt = (
            insert(ExtractResult)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=[
                    ExtractResult.__table__.c.job_id],  # explicit
                set_={k: v for k, v in payload.items() if k != "job_id"},
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        # return the fresh row
        obj = await self.db.get(ExtractResult, data.job_id)
        if not obj:
            # extremely unlikely, but keep API honest
            raise HTTPException(status_code=500, detail="upsert failed")
        return obj
