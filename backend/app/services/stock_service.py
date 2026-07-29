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
from app.schemas.stock import StockAdjustmentCreate


class StockService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = StockHistoryRepository(db)

    def history(
        self,
        skip: int = 0,
        limit: int = 100,
        product_id: Optional[UUID] = None,
        movement_type: Optional[StockMovementType] = None,
        store_id: Optional[UUID] = None,
    ) -> list[StockHistory]:
        return self.repo.list_recent(skip, limit, product_id, movement_type, store_id)

    def adjust(self, payload: StockAdjustmentCreate, current_user: User) -> StockHistory:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to a store")
        product = self.db.query(Product).filter(Product.id == payload.product_id, Product.store_id == current_user.store_id).first()
        if not product:
            raise not_found("Product")

        if payload.reason == "CUSTOMER_RETURN" and payload.direction != "INCREASE":
            raise bad_request("Customer returns must increase stock")
        if payload.reason in {"SUPPLIER_RETURN", "DAMAGE"} and payload.direction != "DECREASE":
            raise bad_request(f"{payload.reason.replace('_', ' ').title()} must decrease stock")

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
            movement_type=StockMovementType(payload.reason),
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
