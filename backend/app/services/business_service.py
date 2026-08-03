from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, not_found
from app.models.customer import Customer, CustomerPayment
from app.models.enums import PurchaseStatus, SaleStatus
from app.models.expense import Expense, ExpenseCategory
from app.models.purchase import Purchase
from app.models.sale import Sale
from app.models.supplier import Supplier, SupplierPayment
from app.models.user import User
from app.repositories.business import CustomerRepository, ExpenseCategoryRepository, ExpenseRepository, SupplierRepository
from app.schemas.customer import CustomerCreate, CustomerDetailRead, CustomerLedgerEntry, CustomerPaymentCreate, CustomerRead, CustomerUpdate
from app.schemas.expense import ExpenseCategoryCreate, ExpenseCategoryUpdate, ExpenseCreate, ExpenseUpdate
from app.schemas.supplier import SupplierCreate, SupplierDetailRead, SupplierLedgerEntry, SupplierPaymentCreate, SupplierRead, SupplierUpdate


def _store_id(current_user: User) -> UUID:
    if current_user.store_id is None:
        raise bad_request("Current user is not assigned to a store")
    return current_user.store_id


def _money(value: Optional[Decimal]) -> Decimal:
    return value or Decimal("0")


class SupplierService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SupplierRepository(db)

    def list(self, current_user: User, search: Optional[str] = None, include_inactive: bool = False, skip: int = 0, limit: int = 100) -> list[SupplierRead]:
        store_id = _store_id(current_user)
        return [self._read(supplier, store_id) for supplier in self.repo.list_for_store(store_id, search, include_inactive, skip, limit)]

    def get(self, supplier_id: UUID, current_user: User) -> Supplier:
        supplier = self.repo.get_for_store(supplier_id, _store_id(current_user))
        if not supplier:
            raise not_found("Supplier")
        return supplier

    def detail(self, supplier_id: UUID, current_user: User) -> SupplierDetailRead:
        store_id = _store_id(current_user)
        supplier = self.get(supplier_id, current_user)
        base = self._read(supplier, store_id).model_dump()
        base["payments"] = supplier.payments
        base["ledger"] = self._ledger(supplier, store_id)
        return SupplierDetailRead.model_validate(base)

    def create(self, payload: SupplierCreate, current_user: User) -> SupplierRead:
        store_id = _store_id(current_user)
        if self.repo.get_by_name(store_id, payload.name):
            raise conflict("Supplier already exists")
        supplier = Supplier(store_id=store_id, **payload.model_dump())
        self.repo.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return self._read(supplier, store_id)

    def update(self, supplier_id: UUID, payload: SupplierUpdate, current_user: User) -> SupplierRead:
        store_id = _store_id(current_user)
        supplier = self.get(supplier_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            duplicate = self.repo.get_by_name(store_id, data["name"])
            if duplicate and duplicate.id != supplier.id:
                raise conflict("Supplier already exists")
        if supplier.store_id is None:
            supplier.store_id = store_id
        for key, value in data.items():
            setattr(supplier, key, value)
        self.db.commit()
        self.db.refresh(supplier)
        return self._read(supplier, store_id)

    def delete(self, supplier_id: UUID, current_user: User) -> None:
        store_id = _store_id(current_user)
        supplier = self.get(supplier_id, current_user)
        purchase_count = self.db.query(Purchase).filter(Purchase.store_id == store_id, Purchase.supplier_id == supplier.id).count()
        payment_count = self.db.query(SupplierPayment).filter(SupplierPayment.store_id == store_id, SupplierPayment.supplier_id == supplier.id).count()
        if purchase_count or payment_count:
            supplier.is_active = False
        else:
            self.repo.delete(supplier)
        self.db.commit()

    def add_payment(self, supplier_id: UUID, payload: SupplierPaymentCreate, current_user: User) -> SupplierDetailRead:
        store_id = _store_id(current_user)
        supplier = self.get(supplier_id, current_user)
        payment = SupplierPayment(store_id=store_id, supplier_id=supplier.id, payment_date=payload.payment_date or datetime.now(timezone.utc), amount=payload.amount, payment_mode=payload.payment_mode.upper(), reference=payload.reference, notes=payload.notes, created_by=current_user.id)
        self.db.add(payment)
        self.db.commit()
        return self.detail(supplier.id, current_user)

    def _totals(self, supplier: Supplier, store_id: UUID) -> tuple[Decimal, Decimal, Decimal]:
        purchase_total = _money(
            self.db.query(func.coalesce(func.sum(Purchase.total_amount), 0))
            .filter(Purchase.store_id == store_id, Purchase.supplier_id == supplier.id, Purchase.status.notin_([PurchaseStatus.CANCELLED, PurchaseStatus.VOIDED]))
            .scalar()
        )
        purchase_paid = _money(
            self.db.query(func.coalesce(func.sum(Purchase.amount_paid), 0))
            .filter(Purchase.store_id == store_id, Purchase.supplier_id == supplier.id, Purchase.status.notin_([PurchaseStatus.CANCELLED, PurchaseStatus.VOIDED]))
            .scalar()
        )
        ledger_paid = _money(self.db.query(func.coalesce(func.sum(SupplierPayment.amount), 0)).filter(SupplierPayment.store_id == store_id, SupplierPayment.supplier_id == supplier.id).scalar())
        paid_total = purchase_paid + ledger_paid
        balance = _money(supplier.opening_balance) + purchase_total - paid_total
        return purchase_total, paid_total, balance

    def _read(self, supplier: Supplier, store_id: UUID) -> SupplierRead:
        purchase_total, paid_total, balance = self._totals(supplier, store_id)
        data = SupplierRead.model_validate(supplier).model_dump()
        data.update(purchase_total=purchase_total, paid_total=paid_total, balance_due=balance)
        return SupplierRead.model_validate(data)

    def _ledger(self, supplier: Supplier, store_id: UUID) -> list[SupplierLedgerEntry]:
        entries: list[SupplierLedgerEntry] = []
        balance = _money(supplier.opening_balance)
        if balance:
            entries.append(SupplierLedgerEntry(id=supplier.id, entry_type="OPENING", entry_date=supplier.created_at, reference=None, description="Opening balance", debit=balance, credit=Decimal("0"), balance=balance))
        purchases = (
            self.db.query(Purchase)
            .filter(Purchase.store_id == store_id, Purchase.supplier_id == supplier.id, Purchase.status.notin_([PurchaseStatus.CANCELLED, PurchaseStatus.VOIDED]))
            .order_by(Purchase.purchase_date, Purchase.created_at)
            .all()
        )
        events = []
        for purchase in purchases:
            event_date = datetime.combine(purchase.purchase_date, time.min, tzinfo=timezone.utc)
            events.append((event_date, "PURCHASE", purchase.id, purchase.invoice_number, purchase.supplier_name or supplier.name, purchase.total_amount, Decimal("0")))
            if purchase.amount_paid:
                events.append((event_date, "PAYMENT", purchase.id, purchase.invoice_number, "Paid on invoice", Decimal("0"), purchase.amount_paid))
        for payment in supplier.payments:
            events.append((payment.payment_date, "PAYMENT", payment.id, payment.reference, payment.notes or payment.payment_mode, Decimal("0"), payment.amount))
        for event_date, entry_type, entry_id, reference, description, debit, credit in sorted(events, key=lambda event: event[0]):
            balance += debit - credit
            entries.append(SupplierLedgerEntry(id=entry_id, entry_type=entry_type, entry_date=event_date, reference=reference, description=description, debit=debit, credit=credit, balance=balance))
        return entries


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CustomerRepository(db)

    def list(self, current_user: User, search: Optional[str] = None, include_inactive: bool = False, skip: int = 0, limit: int = 100) -> list[CustomerRead]:
        store_id = _store_id(current_user)
        return [self._read(customer, store_id) for customer in self.repo.list_for_store(store_id, search, include_inactive, skip, limit)]

    def get(self, customer_id: UUID, current_user: User) -> Customer:
        customer = self.repo.get_for_store(customer_id, _store_id(current_user))
        if not customer:
            raise not_found("Customer")
        return customer

    def detail(self, customer_id: UUID, current_user: User) -> CustomerDetailRead:
        store_id = _store_id(current_user)
        customer = self.get(customer_id, current_user)
        base = self._read(customer, store_id).model_dump()
        base["payments"] = customer.payments
        base["ledger"] = self._ledger(customer, store_id)
        return CustomerDetailRead.model_validate(base)

    def create(self, payload: CustomerCreate, current_user: User) -> CustomerRead:
        store_id = _store_id(current_user)
        if payload.phone and self.repo.get_by_phone(store_id, payload.phone):
            raise conflict("Customer phone number already exists")
        customer = Customer(store_id=store_id, **payload.model_dump())
        self.repo.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return self._read(customer, store_id)

    def update(self, customer_id: UUID, payload: CustomerUpdate, current_user: User) -> CustomerRead:
        store_id = _store_id(current_user)
        customer = self.get(customer_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "phone" in data and data["phone"]:
            duplicate = self.repo.get_by_phone(store_id, data["phone"])
            if duplicate and duplicate.id != customer.id:
                raise conflict("Customer phone number already exists")
        for key, value in data.items():
            setattr(customer, key, value)
        self.db.commit()
        self.db.refresh(customer)
        return self._read(customer, store_id)

    def delete(self, customer_id: UUID, current_user: User) -> None:
        store_id = _store_id(current_user)
        customer = self.get(customer_id, current_user)
        sale_count = self.db.query(Sale).filter(Sale.store_id == store_id, Sale.customer_id == customer.id).count()
        payment_count = self.db.query(CustomerPayment).filter(CustomerPayment.store_id == store_id, CustomerPayment.customer_id == customer.id).count()
        if sale_count or payment_count:
            customer.is_active = False
        else:
            self.repo.delete(customer)
        self.db.commit()

    def add_payment(self, customer_id: UUID, payload: CustomerPaymentCreate, current_user: User) -> CustomerDetailRead:
        store_id = _store_id(current_user)
        customer = self.get(customer_id, current_user)
        payment = CustomerPayment(store_id=store_id, customer_id=customer.id, payment_date=payload.payment_date or datetime.now(timezone.utc), amount=payload.amount, payment_mode=payload.payment_mode.upper(), reference=payload.reference, notes=payload.notes, created_by=current_user.id)
        self.db.add(payment)
        self.db.commit()
        return self.detail(customer.id, current_user)

    def _totals(self, customer: Customer, store_id: UUID) -> tuple[Decimal, Decimal, Decimal]:
        credit_sales = _money(
            self.db.query(func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(Sale.store_id == store_id, Sale.customer_id == customer.id, Sale.payment_mode == "CREDIT", Sale.status.notin_([SaleStatus.CANCELLED, SaleStatus.VOIDED]))
            .scalar()
        )
        paid_total = _money(self.db.query(func.coalesce(func.sum(CustomerPayment.amount), 0)).filter(CustomerPayment.store_id == store_id, CustomerPayment.customer_id == customer.id).scalar())
        balance = _money(customer.opening_credit) + credit_sales - paid_total
        return credit_sales, paid_total, balance

    def _read(self, customer: Customer, store_id: UUID) -> CustomerRead:
        credit_sales, paid_total, balance = self._totals(customer, store_id)
        data = CustomerRead.model_validate(customer).model_dump()
        data.update(credit_sales_total=credit_sales, paid_total=paid_total, balance_due=balance)
        return CustomerRead.model_validate(data)

    def _ledger(self, customer: Customer, store_id: UUID) -> list[CustomerLedgerEntry]:
        entries: list[CustomerLedgerEntry] = []
        balance = _money(customer.opening_credit)
        if balance:
            entries.append(CustomerLedgerEntry(id=customer.id, entry_type="OPENING", entry_date=customer.created_at, reference=None, description="Opening credit", debit=balance, credit=Decimal("0"), balance=balance))
        events = []
        sales = (
            self.db.query(Sale)
            .filter(Sale.store_id == store_id, Sale.customer_id == customer.id, Sale.payment_mode == "CREDIT", Sale.status.notin_([SaleStatus.CANCELLED, SaleStatus.VOIDED]))
            .order_by(Sale.sale_date)
            .all()
        )
        for sale in sales:
            events.append((sale.sale_date, "CREDIT_SALE", sale.id, sale.invoice_number, "Credit sale", sale.total_amount, Decimal("0")))
        for payment in customer.payments:
            events.append((payment.payment_date, "PAYMENT", payment.id, payment.reference, payment.notes or payment.payment_mode, Decimal("0"), payment.amount))
        for event_date, entry_type, entry_id, reference, description, debit, credit in sorted(events, key=lambda event: event[0]):
            balance += debit - credit
            entries.append(CustomerLedgerEntry(id=entry_id, entry_type=entry_type, entry_date=event_date, reference=reference, description=description, debit=debit, credit=credit, balance=balance))
        return entries


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.category_repo = ExpenseCategoryRepository(db)
        self.expense_repo = ExpenseRepository(db)

    def list_categories(self, current_user: User, include_inactive: bool = False) -> list[ExpenseCategory]:
        return self.category_repo.list_for_store(_store_id(current_user), include_inactive)

    def create_category(self, payload: ExpenseCategoryCreate, current_user: User) -> ExpenseCategory:
        store_id = _store_id(current_user)
        if self.category_repo.get_by_name(store_id, payload.name):
            raise conflict("Expense category already exists")
        category = ExpenseCategory(store_id=store_id, **payload.model_dump())
        self.category_repo.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update_category(self, category_id: UUID, payload: ExpenseCategoryUpdate, current_user: User) -> ExpenseCategory:
        store_id = _store_id(current_user)
        category = self.category_repo.get_for_store(category_id, store_id)
        if not category:
            raise not_found("Expense category")
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            duplicate = self.category_repo.get_by_name(store_id, data["name"])
            if duplicate and duplicate.id != category.id:
                raise conflict("Expense category already exists")
        for key, value in data.items():
            setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, category_id: UUID, current_user: User) -> None:
        store_id = _store_id(current_user)
        category = self.category_repo.get_for_store(category_id, store_id)
        if not category:
            raise not_found("Expense category")
        if self.category_repo.expense_count(category.id):
            category.is_active = False
        else:
            self.category_repo.delete(category)
        self.db.commit()

    def list_expenses(self, current_user: User, start_date=None, end_date=None, category_id: Optional[UUID] = None, search: Optional[str] = None, skip: int = 0, limit: int = 100) -> list[Expense]:
        return self.expense_repo.list_for_store(_store_id(current_user), start_date, end_date, category_id, search, skip, limit)

    def get_expense(self, expense_id: UUID, current_user: User) -> Expense:
        expense = self.expense_repo.get_for_store(expense_id, _store_id(current_user))
        if not expense:
            raise not_found("Expense")
        return expense

    def create_expense(self, payload: ExpenseCreate, current_user: User) -> Expense:
        store_id = _store_id(current_user)
        category = self.category_repo.get_for_store(payload.category_id, store_id)
        if not category or not category.is_active:
            raise bad_request("Select an active expense category")
        expense = Expense(store_id=store_id, created_by=current_user.id, **payload.model_dump())
        self.expense_repo.add(expense)
        self.db.commit()
        return self.get_expense(expense.id, current_user)

    def update_expense(self, expense_id: UUID, payload: ExpenseUpdate, current_user: User) -> Expense:
        store_id = _store_id(current_user)
        expense = self.get_expense(expense_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "category_id" in data:
            category = self.category_repo.get_for_store(data["category_id"], store_id)
            if not category or not category.is_active:
                raise bad_request("Select an active expense category")
        for key, value in data.items():
            setattr(expense, key, value)
        self.db.commit()
        return self.get_expense(expense.id, current_user)

    def delete_expense(self, expense_id: UUID, current_user: User) -> None:
        expense = self.get_expense(expense_id, current_user)
        self.expense_repo.delete(expense)
        self.db.commit()
