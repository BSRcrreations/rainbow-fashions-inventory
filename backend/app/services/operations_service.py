from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, forbidden, not_found
from app.core.security import hash_password
from app.models.destructive_action import DestructiveActionAudit
from app.models.enums import SaleStatus, UserRole
from app.models.customer import CustomerPayment
from app.models.expense import Expense
from app.models.inventory_reconciliation import InventoryReconciliationAudit
from app.models.opening_stock_import import OpeningStockImport, OpeningStockImportAudit
from app.models.operations import DayClosing, OperationsAudit, StorePreference
from app.models.product_barcode import ProductBarcodeAudit
from app.models.product_deletion_audit import ProductDeletionAudit
from app.models.product_update_audit import ProductUpdateAudit
from app.models.purchase import Purchase
from app.models.purchase_audit import PurchaseAudit
from app.models.sale import Sale, SaleAudit, SaleReturn
from app.models.stock_audit_event import StockAuditEvent
from app.models.store import Store
from app.models.user import User
from app.schemas.operations import AuditPage, AuditRead, DayClosingCreate, DayClosingSummary, PrinterSettings, StoreSettings, UserCreate, UserUpdate


def store_id_for(user: User) -> UUID:
    if not user.store_id:
        raise forbidden("Your account is not assigned to a shop. Ask the owner for help.")
    return user.store_id


def get_store_settings(db: Session, store_id: UUID) -> StoreSettings:
    preference = db.get(StorePreference, store_id)
    if preference:
        return StoreSettings.model_validate(preference.settings_json)
    store = db.get(Store, store_id)
    if not store:
        raise not_found("Store")
    return StoreSettings(name=store.name, address=store.address or "", phone=store.phone or "")


def business_day_bounds(day: date, zone: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(zone)
    return (datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc),
            datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc))


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def audit(db: Session, user: User, action: str, request_id: str, *, reference=None, reason=None, before=None, after=None) -> None:
    # Call within the operation's transaction; never commit an audit separately.
    db.add(OperationsAudit(store_id=store_id_for(user), user_id=user.id, action=action,
                           request_id=request_id[:120], reference=reference, reason=reason,
                           before_data=before, after_data=after))


class OperationsService:
    def __init__(self, db: Session):
        self.db = db

    def settings(self, user: User) -> StoreSettings:
        return get_store_settings(self.db, store_id_for(user))

    def save_settings(self, payload: StoreSettings | PrinterSettings, user: User, request_id: str) -> StoreSettings:
        if isinstance(payload, StoreSettings) and user.role != UserRole.OWNER:
            raise forbidden("Only the owner can change shop settings.")
        if user.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise forbidden("Ask a manager to change printer settings.")
        store_id = store_id_for(user)
        store = self.db.query(Store).filter(Store.id == store_id).with_for_update().one()
        before = self.settings(user).model_dump(mode="json")
        data = {**before, **payload.model_dump(mode="json")}
        preference = self.db.get(StorePreference, store_id)
        if not preference:
            preference = StorePreference(store_id=store_id)
            self.db.add(preference)
        preference.settings_json = data
        preference.updated_by = user.id
        if isinstance(payload, StoreSettings):
            store.name, store.address, store.phone = payload.name, payload.address, payload.phone
        audit(self.db, user, "PRINTER_SETTINGS_UPDATED" if isinstance(payload, PrinterSettings) else "STORE_SETTINGS_UPDATED", request_id, before=before, after=data)
        self.db.commit()
        return StoreSettings.model_validate(data)

    def users(self, user: User, skip: int = 0, limit: int = 100):
        self._owner(user)
        return self.db.query(User).filter(User.store_id == store_id_for(user)).order_by(User.full_name, User.id).offset(skip).limit(limit).all()

    @staticmethod
    def _owner(user: User):
        if user.role != UserRole.OWNER:
            raise forbidden("Only the owner can manage users.")

    def create_user(self, payload: UserCreate, user: User, request_id: str) -> User:
        self._owner(user)
        store_id = store_id_for(user)
        self.db.query(Store).filter(Store.id == store_id).with_for_update().one()
        email = str(payload.email).strip().lower()
        if self.db.query(User.id).filter(func.lower(User.email) == email).first():
            raise conflict("This email is already in use. Choose a different email.")
        created = User(store_id=store_id, email=email, full_name=payload.full_name.strip(), role=payload.role,
                       password_hash=hash_password(payload.password), is_active=True)
        self.db.add(created)
        self.db.flush()
        audit(self.db, user, "USER_CREATED", request_id, reference=created.full_name,
              after={"full_name": created.full_name, "email": created.email, "role": created.role.value, "is_active": True})
        self.db.commit()
        return created

    def update_user(self, user_id: UUID, payload: UserUpdate, user: User, request_id: str) -> User:
        self._owner(user)
        store_id = store_id_for(user)
        # Serializing on the store protects the last-owner rule from concurrent edits.
        self.db.query(Store).filter(Store.id == store_id).with_for_update().one()
        target = self.db.query(User).filter(User.id == user_id, User.store_id == store_id).with_for_update().first()
        if not target:
            raise not_found("User")
        if target.id == user.id and (not payload.is_active or payload.role != UserRole.OWNER):
            raise bad_request("Ask another owner to change your role or disable your account.")
        if target.role == UserRole.OWNER and target.is_active and (payload.role != UserRole.OWNER or not payload.is_active):
            owners = self.db.query(User.id).filter(User.store_id == store_id, User.role == UserRole.OWNER, User.is_active.is_(True)).count()
            if owners <= 1:
                raise bad_request("Keep at least one active owner for this shop.")
        before = {"full_name": target.full_name, "role": target.role.value, "is_active": target.is_active}
        target.full_name, target.role, target.is_active = payload.full_name.strip(), payload.role, payload.is_active
        audit(self.db, user, "USER_UPDATED", request_id, reference=target.full_name, reason=payload.reason,
              before=before, after={"full_name": target.full_name, "role": target.role.value, "is_active": target.is_active})
        self.db.commit()
        return target

    def closing_preview(self, user: User, day: date, opening_cash: Decimal) -> DayClosingSummary:
        store_id = store_id_for(user)
        zone = self.settings(user).timezone
        if day > datetime.now(ZoneInfo(zone)).date():
            raise bad_request("Choose today or an earlier date for day closing.")
        start, end = business_day_bounds(day, zone)
        sales = self.db.query(Sale.payment_mode, func.sum(Sale.total_amount), func.count(Sale.id)).filter(
            Sale.store_id == store_id, Sale.sale_date >= start, Sale.sale_date < end,
            Sale.status.in_([SaleStatus.COMPLETED, SaleStatus.EDITED, SaleStatus.PARTIALLY_RETURNED, SaleStatus.RETURNED]),
        ).group_by(Sale.payment_mode).all()
        modes = {mode: Decimal("0.00") for mode in ("CASH", "UPI", "CARD", "BANK", "CREDIT", "OTHER")}
        for mode, amount, _ in sales:
            key = mode.upper() if mode.upper() in modes else "OTHER"
            modes[key] += money(amount)
        refunds = self.db.query(func.sum(SaleReturn.refund_amount)).filter(
            SaleReturn.store_id == store_id, SaleReturn.created_at >= start, SaleReturn.created_at < end,
            func.upper(SaleReturn.refund_method) == "CASH").scalar()
        expenses = self.db.query(func.sum(Expense.amount)).filter(
            Expense.store_id == store_id, Expense.expense_date == day, func.upper(Expense.payment_mode) == "CASH").scalar()
        payments = self.db.query(func.sum(CustomerPayment.amount)).filter(
            CustomerPayment.store_id == store_id, CustomerPayment.payment_date >= start, CustomerPayment.payment_date < end,
            func.upper(CustomerPayment.payment_mode) == "CASH").scalar()
        from app.models.supplier import SupplierPayment
        from app.models.purchase import Purchase
        from app.models.enums import PurchaseStatus
        supplier_cash = money(self.db.query(func.sum(SupplierPayment.amount)).filter(SupplierPayment.store_id == store_id, SupplierPayment.payment_date >= start, SupplierPayment.payment_date < end, func.upper(SupplierPayment.payment_mode) == "CASH").scalar())
        supplier_cash += money(self.db.query(func.sum(Purchase.amount_paid)).filter(Purchase.store_id == store_id, Purchase.purchase_date == day, Purchase.status == PurchaseStatus.CONFIRMED, func.upper(Purchase.payment_mode) == "CASH").scalar())
        expected = money(opening_cash) + modes["CASH"] - money(refunds) - money(expenses) + money(payments) - supplier_cash
        return DayClosingSummary(business_date=day, timezone=zone, opening_cash=money(opening_cash), cash_sales=modes["CASH"],
                                 cash_refunds=money(refunds), cash_expenses=money(expenses), customer_cash_payments=money(payments),
                                 supplier_cash_payments=supplier_cash, expected_cash=expected, payment_totals=modes, bills=sum(count for _, _, count in sales))

    def submit_closing(self, payload: DayClosingCreate, user: User, request_id: str) -> DayClosing:
        if user.role not in (UserRole.OWNER, UserRole.MANAGER, UserRole.CASHIER, UserRole.STAFF):
            raise forbidden("Only billing staff can submit day closing.")
        store_id = store_id_for(user)
        self.db.query(Store).filter(Store.id == store_id).with_for_update().one()
        existing = self.db.query(DayClosing).filter(DayClosing.store_id == store_id, DayClosing.business_date == payload.business_date).first()
        summary = self.closing_preview(user, payload.business_date, payload.opening_cash)
        snapshot = summary.model_dump(mode="json")
        if existing:
            if existing.opening_cash == payload.opening_cash and existing.actual_cash == payload.actual_cash and existing.notes == payload.notes and existing.summary_json == snapshot:
                return existing
            if existing.status == "APPROVED":
                raise conflict("This day has already been approved. Its original closing is kept in history.")
            before = {"opening_cash": str(existing.opening_cash), "actual_cash": str(existing.actual_cash), "summary": existing.summary_json}
            closing = existing
        else:
            before = None
            closing = DayClosing(store_id=store_id, business_date=payload.business_date, created_by=user.id, status="SUBMITTED")
            self.db.add(closing)
        closing.opening_cash, closing.actual_cash = payload.opening_cash, payload.actual_cash
        closing.expected_cash, closing.difference = summary.expected_cash, money(payload.actual_cash - summary.expected_cash)
        closing.summary_json, closing.notes = snapshot, payload.notes
        self.db.flush()
        audit(self.db, user, "DAY_CLOSING_SUBMITTED", request_id, reference=str(payload.business_date), reason=payload.notes,
              before=before, after={"actual_cash": str(payload.actual_cash), "difference": str(closing.difference), "summary": snapshot})
        self.db.commit()
        return closing

    def approve_closing(self, closing_id: UUID, user: User, request_id: str) -> DayClosing:
        if user.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise forbidden("Ask the manager or owner to approve day closing.")
        store_id = store_id_for(user)
        self.db.query(Store).filter(Store.id == store_id).with_for_update().one()
        closing = self.db.query(DayClosing).filter(DayClosing.id == closing_id, DayClosing.store_id == store_id).with_for_update().first()
        if not closing:
            raise not_found("Day closing")
        if closing.status == "APPROVED":
            return closing
        fresh = self.closing_preview(user, closing.business_date, closing.opening_cash).model_dump(mode="json")
        if fresh != closing.summary_json:
            raise conflict("Shop transactions have changed. Check the cash again and save day closing before approving.")
        closing.status, closing.approved_by, closing.approved_at = "APPROVED", user.id, datetime.now(timezone.utc)
        audit(self.db, user, "DAY_CLOSING_APPROVED", request_id, reference=str(closing.business_date),
              before={"status": "SUBMITTED"}, after={"status": "APPROVED", "difference": str(closing.difference)})
        self.db.commit()
        return closing

    def closings(self, user: User, skip: int = 0, limit: int = 30, start_date: date | None = None, end_date: date | None = None):
        query = self.db.query(DayClosing).filter(DayClosing.store_id == store_id_for(user))
        if start_date:
            query = query.filter(DayClosing.business_date >= start_date)
        if end_date:
            query = query.filter(DayClosing.business_date <= end_date)
        return query.order_by(DayClosing.business_date.desc()).offset(skip).limit(limit).all()

    def audit_log(self, user: User, skip=0, limit=50, search: str | None = None, start_date: date | None = None, end_date: date | None = None) -> AuditPage:
        if user.role not in (UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT):
            raise forbidden("Ask a manager to view the audit log.")
        store_id = store_id_for(user)
        no_json, no_text = cast(literal(None), JSONB), cast(literal(None), String)

        def entry(model, source, when, action, actor, scope, reference=no_text, reason=no_text, before=no_json, after=no_json, request=no_text):
            return select((literal(source + ":") + cast(model.id, String)).label("id"), when.label("created_at"),
                          action.label("action"), actor.label("user_id"), cast(reference, String).label("reference"),
                          reason.label("reason"), before.label("before_data"), after.label("after_data"), request.label("request_id")).where(scope)

        statements = [
            entry(OperationsAudit, "shop", OperationsAudit.created_at, OperationsAudit.action, OperationsAudit.user_id, OperationsAudit.store_id == store_id, OperationsAudit.reference, OperationsAudit.reason, OperationsAudit.before_data, OperationsAudit.after_data, OperationsAudit.request_id),
            entry(StockAuditEvent, "stock", StockAuditEvent.created_at, StockAuditEvent.event_type, StockAuditEvent.user_id, StockAuditEvent.store_id == store_id, StockAuditEvent.product_id, after=StockAuditEvent.metadata_json, request=StockAuditEvent.request_id),
            entry(ProductUpdateAudit, "product", ProductUpdateAudit.created_at, literal("PRODUCT_UPDATED"), ProductUpdateAudit.changed_by, ProductUpdateAudit.store_id == store_id, ProductUpdateAudit.product_id, before=ProductUpdateAudit.before_values, after=ProductUpdateAudit.after_values, request=ProductUpdateAudit.request_id),
            entry(ProductBarcodeAudit, "barcode", ProductBarcodeAudit.changed_at, ProductBarcodeAudit.action, ProductBarcodeAudit.changed_by, ProductBarcodeAudit.store_id == store_id, ProductBarcodeAudit.barcode, ProductBarcodeAudit.reason, after=ProductBarcodeAudit.metadata_json, request=ProductBarcodeAudit.request_id),
            entry(ProductDeletionAudit, "deletion", ProductDeletionAudit.created_at, ProductDeletionAudit.event_type, ProductDeletionAudit.performed_by, ProductDeletionAudit.store_id == store_id, ProductDeletionAudit.product_id, ProductDeletionAudit.reason, ProductDeletionAudit.product_snapshot, ProductDeletionAudit.deleted_record_counts, ProductDeletionAudit.request_id),
            entry(DestructiveActionAudit, "security", DestructiveActionAudit.created_at, DestructiveActionAudit.event_type, DestructiveActionAudit.user_id, DestructiveActionAudit.store_id == store_id, DestructiveActionAudit.reference, after=DestructiveActionAudit.record_counts, request=DestructiveActionAudit.request_id),
            entry(InventoryReconciliationAudit, "reconciliation", InventoryReconciliationAudit.created_at, InventoryReconciliationAudit.action, InventoryReconciliationAudit.performed_by, InventoryReconciliationAudit.store_id == store_id, InventoryReconciliationAudit.product_id, before=InventoryReconciliationAudit.before_values, after=InventoryReconciliationAudit.after_values, request=InventoryReconciliationAudit.request_id),
            entry(SaleAudit, "sale", SaleAudit.created_at, SaleAudit.action, SaleAudit.performed_by, Sale.store_id == store_id, Sale.invoice_number, SaleAudit.reason, SaleAudit.before_data, SaleAudit.after_data).join(Sale, Sale.id == SaleAudit.sale_id),
            entry(PurchaseAudit, "purchase", PurchaseAudit.created_at, PurchaseAudit.action, PurchaseAudit.performed_by, Purchase.store_id == store_id, Purchase.invoice_number, PurchaseAudit.reason, PurchaseAudit.before_data, PurchaseAudit.after_data).join(Purchase, Purchase.id == PurchaseAudit.purchase_id),
            entry(OpeningStockImportAudit, "opening", OpeningStockImportAudit.created_at, OpeningStockImportAudit.action, OpeningStockImportAudit.performed_by, OpeningStockImport.store_id == store_id, OpeningStockImport.original_filename, after=OpeningStockImportAudit.metadata_json, request=OpeningStockImportAudit.request_id).join(OpeningStockImport, OpeningStockImport.id == OpeningStockImportAudit.opening_stock_import_id),
        ]
        combined = union_all(*statements).subquery()
        query = select(combined, func.coalesce(User.full_name, "System").label("actor")).outerjoin(User, User.id == combined.c.user_id)
        zone = self.settings(user).timezone
        if start_date:
            query = query.where(combined.c.created_at >= business_day_bounds(start_date, zone)[0])
        if end_date:
            query = query.where(combined.c.created_at < business_day_bounds(end_date, zone)[1])
        if search:
            query = query.where((combined.c.action + literal(" ") + func.coalesce(combined.c.reference, "") + literal(" ") + func.coalesce(User.full_name, "")).ilike("%" + search.strip() + "%"))
        rows = self.db.execute(query.order_by(combined.c.created_at.desc(), combined.c.id.desc()).offset(skip).limit(limit + 1)).mappings().all()
        return AuditPage(items=[AuditRead.model_validate({**row, "before_data": redact(row["before_data"]), "after_data": redact(row["after_data"])}) for row in rows[:limit]], has_more=len(rows) > limit)


def redact(value):
    """Historical snapshots must never reveal credentials through the audit UI."""
    if isinstance(value, dict):
        return {key: ("[hidden]" if any(part in key.lower() for part in ("password", "credential", "secret", "token")) else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
