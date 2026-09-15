"""Store-scoped operational cards using aggregated account entries."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import func
from app.models import Product, ProductVariant, Sale, SaleReturn, Purchase
from app.models.customer import Customer, CustomerPayment
from app.models.supplier import Supplier, SupplierPayment
from app.models.purchase_return import PurchaseReturn
from app.models.enums import SaleStatus, PurchaseStatus
from app.models.sale import SaleItem
from app.services.report_service import ReportService


def shop_summary(db, user):
    store = user.store_id
    today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    def grouped(model, identity, value, *filters):
        return dict(db.query(identity, func.coalesce(func.sum(value), 0)).filter(model.store_id == store, *filters).group_by(identity).all())
    supplier_purchases = grouped(Purchase, Purchase.supplier_id, Purchase.total_amount - Purchase.amount_paid, Purchase.status == PurchaseStatus.CONFIRMED)
    supplier_payments = grouped(SupplierPayment, SupplierPayment.supplier_id, SupplierPayment.amount)
    credits = grouped(PurchaseReturn, PurchaseReturn.supplier_id, PurchaseReturn.credit_amount)
    payable = sum((max(Decimal('0'), row.opening_balance + supplier_purchases.get(row.id, 0) - supplier_payments.get(row.id, 0) - credits.get(row.id, 0)) for row in db.query(Supplier).filter_by(store_id=store)), Decimal('0'))
    valid = Sale.status.notin_([SaleStatus.VOIDED, SaleStatus.CANCELLED, SaleStatus.DRAFT])
    customer_sales = grouped(Sale, Sale.customer_id, Sale.total_amount, Sale.payment_mode == 'CREDIT', valid)
    customer_payments = grouped(CustomerPayment, CustomerPayment.customer_id, CustomerPayment.amount)
    refunds = dict(db.query(Sale.customer_id, func.sum(SaleReturn.refund_amount)).join(SaleReturn, SaleReturn.sale_id == Sale.id).filter(Sale.store_id == store, SaleReturn.store_id == store, Sale.payment_mode == 'CREDIT', valid).group_by(Sale.customer_id).all())
    receivable = sum((max(Decimal('0'), row.opening_credit + customer_sales.get(row.id, 0) - customer_payments.get(row.id, 0) - refunds.get(row.id, 0)) for row in db.query(Customer).filter_by(store_id=store)), Decimal('0'))
    variants = db.query(ProductVariant).join(Product).filter(ProductVariant.store_id == store, Product.store_id == store, ProductVariant.is_active.is_(True), Product.is_active.is_(True))
    minimum = func.coalesce(ProductVariant.minimum_stock, Product.minimum_stock)
    retail = variants.with_entities(func.coalesce(func.sum(ProductVariant.current_stock * ProductVariant.selling_price), 0)).scalar()
    units = db.query(func.coalesce(func.sum(SaleItem.quantity), 0)).join(Sale, SaleItem.sale_id == Sale.id).filter(Sale.store_id == store, valid, func.date(func.timezone('Asia/Kolkata', Sale.sale_date)) == today).scalar()
    return {'supplier_payable': payable, 'customer_receivable': receivable, 'inventory_retail_value': retail,
            'today_expenses': ReportService(db)._expense_total(store,today,today), 'today_units_sold': units,
            'low_stock_count': variants.filter(ProductVariant.current_stock > 0, ProductVariant.current_stock <= minimum).count(),
            'out_of_stock_count': variants.filter(ProductVariant.current_stock == 0).count()}
