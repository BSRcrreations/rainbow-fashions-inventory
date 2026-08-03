from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models.customer import CustomerPayment
from app.models.enums import PurchaseStatus, SaleStatus
from app.models.expense import Expense
from app.models.product_variant import ProductVariant
from app.models.purchase import Purchase
from app.models.sale import Sale
from app.models.supplier import SupplierPayment
from app.models.user import User
from app.schemas.report import BusinessReportsSummary, CashFlowReport, InventoryValuationReport, ProfitAndLossReport


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, current_user: User, start_date: Optional[date] = None, end_date: Optional[date] = None) -> BusinessReportsSummary:
        store_id = current_user.store_id
        if store_id is None:
            raise bad_request("Current user is not assigned to a store")
        end_date = end_date or date.today()
        start_date = start_date or end_date - timedelta(days=30)
        if start_date > end_date:
            raise bad_request("Start date cannot be after end date")

        sales_total = self._sales_total(store_id, start_date, end_date)
        cost_total = self._sales_cost(store_id, start_date, end_date)
        purchase_total = self._purchase_total(store_id, start_date, end_date)
        expense_total = self._expense_total(store_id, start_date, end_date)
        gross_profit = sales_total - cost_total
        net_profit = gross_profit - expense_total
        customer_payments = self._customer_payment_total(store_id, start_date, end_date)
        supplier_payments = self._supplier_payment_total(store_id, start_date, end_date)
        cash_sales = self._cash_sales_total(store_id, start_date, end_date)

        return BusinessReportsSummary(
            profit_and_loss=ProfitAndLossReport(start_date=start_date, end_date=end_date, sales_total=sales_total, purchase_total=purchase_total, expense_total=expense_total, gross_profit=gross_profit, net_profit=net_profit),
            cash_flow=CashFlowReport(start_date=start_date, end_date=end_date, cash_sales=cash_sales, supplier_payments=supplier_payments, customer_payments=customer_payments, expenses=expense_total, net_cash_flow=cash_sales + customer_payments - supplier_payments - expense_total),
            inventory_valuation=self.inventory_valuation(current_user),
        )

    def inventory_valuation(self, current_user: User) -> InventoryValuationReport:
        store_id = current_user.store_id
        if store_id is None:
            raise bad_request("Current user is not assigned to a store")
        rows = (
            self.db.query(
                func.coalesce(func.sum(ProductVariant.current_stock), 0),
                func.coalesce(func.sum(ProductVariant.current_stock * ProductVariant.average_cost), 0),
                func.coalesce(func.sum(ProductVariant.current_stock * ProductVariant.selling_price), 0),
            )
            .filter(ProductVariant.store_id == store_id, ProductVariant.is_active.is_(True))
            .one()
        )
        total_stock = int(rows[0] or 0)
        purchase_value = Decimal(rows[1] or 0)
        selling_value = Decimal(rows[2] or 0)
        return InventoryValuationReport(total_stock=total_stock, purchase_value=purchase_value, selling_value=selling_value, potential_margin=selling_value - purchase_value)

    def _sales_total(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(Sale.store_id == store_id, func.date(Sale.sale_date) >= start_date, func.date(Sale.sale_date) <= end_date, Sale.status.notin_([SaleStatus.CANCELLED, SaleStatus.VOIDED])).scalar() or 0)

    def _sales_cost(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(Sale.cost_amount), 0)).filter(Sale.store_id == store_id, func.date(Sale.sale_date) >= start_date, func.date(Sale.sale_date) <= end_date, Sale.status.notin_([SaleStatus.CANCELLED, SaleStatus.VOIDED])).scalar() or 0)

    def _cash_sales_total(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(Sale.store_id == store_id, func.date(Sale.sale_date) >= start_date, func.date(Sale.sale_date) <= end_date, Sale.payment_mode != "CREDIT", Sale.status.notin_([SaleStatus.CANCELLED, SaleStatus.VOIDED])).scalar() or 0)

    def _purchase_total(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(Purchase.total_amount), 0)).filter(Purchase.store_id == store_id, Purchase.purchase_date >= start_date, Purchase.purchase_date <= end_date, Purchase.status.notin_([PurchaseStatus.CANCELLED, PurchaseStatus.VOIDED])).scalar() or 0)

    def _expense_total(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.store_id == store_id, Expense.expense_date >= start_date, Expense.expense_date <= end_date).scalar() or 0)

    def _customer_payment_total(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(CustomerPayment.amount), 0)).filter(CustomerPayment.store_id == store_id, func.date(CustomerPayment.payment_date) >= start_date, func.date(CustomerPayment.payment_date) <= end_date).scalar() or 0)

    def _supplier_payment_total(self, store_id, start_date: date, end_date: date) -> Decimal:
        return Decimal(self.db.query(func.coalesce(func.sum(SupplierPayment.amount), 0)).filter(SupplierPayment.store_id == store_id, func.date(SupplierPayment.payment_date) >= start_date, func.date(SupplierPayment.payment_date) <= end_date).scalar() or 0)
