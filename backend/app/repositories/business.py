from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.expense import Expense, ExpenseCategory
from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    def get_for_store(self, supplier_id: UUID, store_id: UUID) -> Optional[Supplier]:
        return self.db.query(Supplier).options(selectinload(Supplier.payments)).filter(Supplier.id == supplier_id, or_(Supplier.store_id == store_id, Supplier.store_id.is_(None))).first()

    def get_by_name(self, store_id: UUID, name: str) -> Optional[Supplier]:
        return self.db.query(Supplier).filter(or_(Supplier.store_id == store_id, Supplier.store_id.is_(None)), func.lower(Supplier.name) == name.strip().lower()).first()

    def list_for_store(self, store_id: UUID, search: Optional[str], include_inactive: bool, skip: int, limit: int) -> list[Supplier]:
        query = self.db.query(Supplier).filter(or_(Supplier.store_id == store_id, Supplier.store_id.is_(None)))
        if not include_inactive:
            query = query.filter(Supplier.is_active.is_(True))
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Supplier.name.ilike(pattern), Supplier.phone.ilike(pattern), Supplier.email.ilike(pattern), Supplier.gst_number.ilike(pattern)))
        return query.order_by(Supplier.name).offset(skip).limit(limit).all()


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    def get_for_store(self, customer_id: UUID, store_id: UUID) -> Optional[Customer]:
        return self.db.query(Customer).options(selectinload(Customer.payments)).filter(Customer.id == customer_id, Customer.store_id == store_id).first()

    def get_by_phone(self, store_id: UUID, phone: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.store_id == store_id, func.lower(Customer.phone) == phone.strip().lower()).first()

    def list_for_store(self, store_id: UUID, search: Optional[str], include_inactive: bool, skip: int, limit: int) -> list[Customer]:
        query = self.db.query(Customer).filter(Customer.store_id == store_id)
        if not include_inactive:
            query = query.filter(Customer.is_active.is_(True))
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern), Customer.email.ilike(pattern), Customer.gst_number.ilike(pattern)))
        return query.order_by(Customer.name).offset(skip).limit(limit).all()


class ExpenseCategoryRepository(BaseRepository[ExpenseCategory]):
    model = ExpenseCategory

    def get_for_store(self, category_id: UUID, store_id: UUID) -> Optional[ExpenseCategory]:
        return self.db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id, ExpenseCategory.store_id == store_id).first()

    def get_by_name(self, store_id: UUID, name: str) -> Optional[ExpenseCategory]:
        return self.db.query(ExpenseCategory).filter(ExpenseCategory.store_id == store_id, func.lower(ExpenseCategory.name) == name.strip().lower()).first()

    def list_for_store(self, store_id: UUID, include_inactive: bool = False) -> list[ExpenseCategory]:
        query = self.db.query(ExpenseCategory).filter(ExpenseCategory.store_id == store_id)
        if not include_inactive:
            query = query.filter(ExpenseCategory.is_active.is_(True))
        return query.order_by(ExpenseCategory.name).all()

    def expense_count(self, category_id: UUID) -> int:
        return self.db.query(Expense).filter(Expense.category_id == category_id).count()


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense

    def get_for_store(self, expense_id: UUID, store_id: UUID) -> Optional[Expense]:
        return self.db.query(Expense).options(selectinload(Expense.category)).filter(Expense.id == expense_id, Expense.store_id == store_id).first()

    def list_for_store(self, store_id: UUID, start_date: Optional[date], end_date: Optional[date], category_id: Optional[UUID], search: Optional[str], skip: int, limit: int) -> list[Expense]:
        query = self.db.query(Expense).options(selectinload(Expense.category)).filter(Expense.store_id == store_id)
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)
        if category_id:
            query = query.filter(Expense.category_id == category_id)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Expense.title.ilike(pattern), Expense.vendor.ilike(pattern), Expense.reference.ilike(pattern)))
        return query.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).offset(skip).limit(limit).all()
