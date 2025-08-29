# services/base_service.py
from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

PKType = Union[str, int]  # <-- allow UUID strings

class BaseService:
    def __init__(self, db: AsyncSession, model: Type[Any]):
        self.db = db
        self.model = model

    async def get_by_id(self, item_id: PKType) -> Optional[Any]:
        # Works for any single-column PK (UUID string or int)
        pk_col = list(self.model.__table__.primary_key.columns)[0]
        try:
            stmt = select(self.model).where(pk_col == item_id)
            res = await self.db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model.__name__} {item_id} not found",
                )
            return obj
        except Exception as e:
            logger.error(f"Error fetching {self.model.__name__} {item_id}: {e}")
            raise

    async def list(self, filters: Dict = None) -> List[Any]:
        try:
            stmt = select(self.model)
            if filters:
                for k, v in filters.items():
                    stmt = stmt.where(getattr(self.model, k) == v)
            res = await self.db.execute(stmt)
            return res.scalars().all()
        except Exception as e:
            logger.error(f"Error listing {self.model.__name__}: {e}")
            raise

    async def get(self, obj_id: PKType) -> Any:
        try:
            obj = await self.db.get(self.model, obj_id)
            if not obj:
                raise HTTPException(status_code=404, detail=f"{self.model.__name__} {obj_id} not found")
            return obj
        except Exception as e:
            logger.error(f"Error get {self.model.__name__} {obj_id}: {e}")
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Any]:
        try:
            stmt = select(self.model).offset(skip).limit(limit)
            res = await self.db.execute(stmt)
            return res.scalars().all()
        except Exception as e:
            logger.error(f"Error get_all {self.model.__name__}: {e}")
            raise

    async def create(self, schema: Any) -> Any:
        try:
            data = schema.model_dump() if hasattr(schema, "model_dump") else dict(schema)
            obj = self.model(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            return obj
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail="Integrity error")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Create {self.model.__name__} failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update(self, item_id: PKType, schema: Any) -> Any:
        obj = await self.get_by_id(item_id)
        data = schema.model_dump(exclude_unset=True) if hasattr(schema, "model_dump") else dict(schema)
        for k, v in data.items():
            setattr(obj, k, v)
        try:
            await self.db.commit()
            await self.db.refresh(obj)
            return obj
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail="Constraint violation")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Update {self.model.__name__} {item_id} failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete(self, item_id: PKType) -> bool:
        obj = await self.get_by_id(item_id)
        try:
            await self.db.delete(obj)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Delete {self.model.__name__} {item_id} failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def filter_by(self, filters: Dict[str, Union[str, int, float]]) -> List[Any]:
        try:
            stmt = select(self.model)
            for k, v in filters.items():
                stmt = stmt.where(getattr(self.model, k) == v)
            res = await self.db.execute(stmt)
            return res.scalars().all()
        except Exception as e:
            logger.error(f"Filter {self.model.__name__} {filters} failed: {e}")
            raise
