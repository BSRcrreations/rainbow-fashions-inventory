from __future__ import annotations

from typing import Generic, Optional, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session


ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, record_id: UUID) -> Optional[ModelType]:
        return self.db.get(self.model, record_id)

    def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def add(self, instance: ModelType) -> ModelType:
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelType) -> None:
        self.db.delete(instance)
        self.db.flush()
