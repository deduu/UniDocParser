# services/base_service.py (Enhanced Version)
from typing import Any, Dict, List, Optional, Type, Union, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload
from fastapi import HTTPException, status
from contextlib import asynccontextmanager
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

PKType = Union[str, int]  # Allow UUID strings and integers


class TransactionMixin:
    """Mixin for transaction management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self):
        """Context manager for manual transaction control with rollback"""
        try:
            yield self.db
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise

    async def execute_with_rollback(self, operation: Callable, *args, **kwargs):
        """Execute operation with automatic rollback on failure"""
        try:
            result = await operation(*args, **kwargs)
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Operation failed, rolled back: {e}")
            raise


class BaseService(TransactionMixin):
    """Enhanced base service with comprehensive CRUD operations"""

    def __init__(self, db: AsyncSession, model: Type[Any]):
        super().__init__(db)
        self.model = model
        self._pk_columns = list(self.model.__table__.primary_key.columns)
        self._pk_column = self._pk_columns[0] if len(
            self._pk_columns) == 1 else None

    def _get_pk_filter(self, item_id: PKType):
        """Get primary key filter for single-column PKs"""
        if not self._pk_column:
            raise ValueError(
                f"Model {self.model.__name__} doesn't have a single-column primary key")
        return self._pk_column == item_id

    async def get_by_id(self, item_id: PKType, raise_404: bool = True) -> Optional[Any]:
        """Get item by ID with optional 404 handling"""
        try:
            stmt = select(self.model).where(self._get_pk_filter(item_id))
            result = await self.db.execute(stmt)
            obj = result.scalar_one_or_none()

            if not obj and raise_404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model.__name__} {item_id} not found"
                )
            return obj

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error fetching {self.model.__name__} {item_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch {self.model.__name__}"
            )

    async def get_by_ids(self, item_ids: List[PKType]) -> List[Any]:
        """Get multiple items by IDs"""
        try:
            stmt = select(self.model).where(self._pk_column.in_(item_ids))
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error fetching multiple {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch {self.model.__name__} items"
            )

    async def list(self, filters: Optional[Dict] = None,
                   order_by: Optional[str] = None,
                   skip: int = 0, limit: int = 100) -> List[Any]:
        """Enhanced list with filtering, ordering, and pagination"""
        try:
            stmt = select(self.model)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        column = getattr(self.model, key)
                        if isinstance(value, list):
                            stmt = stmt.where(column.in_(value))
                        elif isinstance(value, dict) and 'operator' in value:
                            # Support for complex filters: {'operator': 'gte', 'value': 10}
                            op = value['operator']
                            val = value['value']
                            if op == 'gte':
                                stmt = stmt.where(column >= val)
                            elif op == 'lte':
                                stmt = stmt.where(column <= val)
                            elif op == 'like':
                                stmt = stmt.where(column.ilike(f"%{val}%"))
                            elif op == 'ne':
                                stmt = stmt.where(column != val)
                            else:
                                stmt = stmt.where(column == val)
                        else:
                            stmt = stmt.where(column == value)

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                stmt = stmt.order_by(order_column)

            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)

            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error listing {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list {self.model.__name__}"
            )

    async def count(self, filters: Optional[Dict] = None) -> int:
        """Count items with optional filters"""
        try:
            stmt = select(func.count(self._pk_column))

            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        column = getattr(self.model, key)
                        if isinstance(value, list):
                            stmt = stmt.where(column.in_(value))
                        else:
                            stmt = stmt.where(column == value)

            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to count {self.model.__name__}"
            )

    async def create(self, schema: Any, commit: bool = True) -> Any:
        """Create with optional commit control"""
        try:
            data = schema.model_dump() if hasattr(schema, "model_dump") else dict(schema)
            obj = self.model(**data)
            self.db.add(obj)

            if commit:
                await self.db.commit()
                await self.db.refresh(obj)

            return obj

        except IntegrityError as e:
            if commit:
                await self.db.rollback()
            logger.error(
                f"Integrity error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity constraint violation"
            )
        except Exception as e:
            if commit:
                await self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {self.model.__name__}"
            )

    async def bulk_create(self, schemas: List[Any], commit: bool = True) -> List[Any]:
        """Bulk create with rollback on any failure"""
        try:
            objects = []
            for schema in schemas:
                data = schema.model_dump() if hasattr(schema, "model_dump") else dict(schema)
                obj = self.model(**data)
                self.db.add(obj)
                objects.append(obj)

            if commit:
                await self.db.commit()
                for obj in objects:
                    await self.db.refresh(obj)

            return objects

        except IntegrityError as e:
            if commit:
                await self.db.rollback()
            logger.error(
                f"Integrity error during bulk create of {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bulk creation failed due to integrity error"
            )
        except Exception as e:
            if commit:
                await self.db.rollback()
            logger.error(
                f"Error during bulk create of {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bulk creation failed"
            )

    async def update(self, item_id: PKType, schema: Any, commit: bool = True) -> Any:
        """Update an existing item"""
        obj = await self.get_by_id(item_id)
        data = schema.model_dump(exclude_unset=True) if hasattr(
            schema, "model_dump") else dict(schema)

        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)

        try:
            if commit:
                await self.db.commit()
                await self.db.refresh(obj)
            return obj
        except IntegrityError as e:
            if commit:
                await self.db.rollback()
            logger.error(
                f"Integrity error updating {self.model.__name__} {item_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity constraint violation"
            )
        except Exception as e:
            if commit:
                await self.db.rollback()
            logger.error(
                f"Error updating {self.model.__name__} {item_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {self.model.__name__}"
            )

    async def delete(self, item_id: PKType, commit: bool = True) -> bool:
        """Delete an item by ID"""
        obj = await self.get_by_id(item_id)
        try:
            await self.db.delete(obj)
            if commit:
                await self.db.commit()
            return True
        except Exception as e:
            if commit:
                await self.db.rollback()
            logger.error(
                f"Error deleting {self.model.__name__} {item_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {self.model.__name__}"
            )

    async def exists(self, filters: Dict[str, Any]) -> bool:
        """Check if a row exists for given filters"""
        try:
            stmt = select(self.model).limit(1)
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(
                f"Error checking existence in {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check existence in {self.model.__name__}"
            )
