from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ReportMetric(BaseModel):
    label: str
    value: Decimal


class ProfitAndLossReport(BaseModel):
    start_date: date
    end_date: date
    sales_total: Decimal
    purchase_total: Decimal
    expense_total: Decimal
    gross_profit: Decimal
    net_profit: Decimal


class CashFlowReport(BaseModel):
    start_date: date
    end_date: date
    cash_sales: Decimal
    supplier_payments: Decimal
    customer_payments: Decimal
    expenses: Decimal
    net_cash_flow: Decimal


class InventoryValuationReport(BaseModel):
    total_stock: int
    purchase_value: Decimal
    selling_value: Decimal
    potential_margin: Decimal


class BusinessReportsSummary(BaseModel):
    # A zero-valued report is different from a report that has no transactions
    # in the selected period.  The client uses this to render a useful empty
    # state instead of presenting an apparently broken all-zero dashboard.
    has_report_data: bool
    profit_and_loss: ProfitAndLossReport
    cash_flow: CashFlowReport
    inventory_valuation: InventoryValuationReport
