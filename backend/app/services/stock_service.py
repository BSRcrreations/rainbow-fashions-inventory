from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.models.enums import StockMovementType
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.stock_history import StockHistory
from app.models.user import User
from app.repositories.stock import StockHistoryRepository
from app.schemas.stock import StockAdjustmentCreate, StockSaleCreate


class StockService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = StockHistoryRepository(db)

    def history(
        self,
        skip: int = 0,
        limit: int = 100,
        movement_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[StockHistory]:
        return self.repo.list_recent(skip, limit, movement_type=movement_type, from_date=from_date, to_date=to_date)

    def adjust(self, payload: StockAdjustmentCreate, current_user: User) -> StockHistory:
        product = self.db.get(Product, payload.product_id)
        if not product:
            raise not_found("Product")

        before_stock = product.current_stock
        if payload.direction == "INCREASE":
            after_stock = before_stock + payload.qty
        else:
            after_stock = before_stock - payload.qty
            if after_stock < 0:
                raise bad_request("Stock cannot become negative")

        product.current_stock = after_stock
        inventory = self._get_or_create_inventory(product.id, current_user.store_id)
        inventory.current_stock = after_stock

        movement = StockHistory(
            product_id=product.id,
            store_id=current_user.store_id,
            movement_type=StockMovementType.ADJUSTMENT,
            qty=payload.qty,
            before_stock=before_stock,
            after_stock=after_stock,
            reference=payload.reference,
            created_by=current_user.id,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def sell(self, payload: StockSaleCreate, current_user: User) -> StockHistory:
        product = self.db.get(Product, payload.product_id)
        if not product:
            raise not_found("Product")

        before_stock = product.current_stock
        after_stock = before_stock - payload.qty
        if after_stock < 0:
            raise bad_request("Stock cannot become negative")

        product.current_stock = after_stock
        inventory = self._get_or_create_inventory(product.id, current_user.store_id)
        inventory.current_stock = after_stock

        movement = StockHistory(
            product_id=product.id,
            store_id=current_user.store_id,
            movement_type=StockMovementType.SALE,
            qty=payload.qty,
            before_stock=before_stock,
            after_stock=after_stock,
            reference=payload.reference,
            created_by=current_user.id,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def _get_or_create_inventory(self, product_id: UUID, store_id: Optional[UUID]) -> ProductInventory:
        if store_id is None:
            raise bad_request("Current user is not assigned to a store")
        inventory = (
            self.db.query(ProductInventory)
            .filter(ProductInventory.product_id == product_id, ProductInventory.store_id == store_id)
            .first()
        )
        if inventory:
            return inventory
        inventory = ProductInventory(product_id=product_id, store_id=store_id, current_stock=0, minimum_stock=0)
        self.db.add(inventory)
        self.db.flush()
        return inventory
