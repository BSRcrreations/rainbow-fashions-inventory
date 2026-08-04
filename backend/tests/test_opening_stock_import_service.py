from io import BytesIO

from openpyxl import Workbook

from app.core.config import Settings
from app.services.opening_stock_import_service import OpeningStockImportService


def service() -> OpeningStockImportService:
    return OpeningStockImportService(None, Settings(app_env="test", allow_test_opening_stock_import_bypass=True))


def test_parse_and_normalize_20k_rows() -> None:
    headers = "product_name,category,subcategory,brand,sku,barcode,quantity,purchase_cost,selling_price"
    rows = [f"Product {index},Women,Kurtas,Brand,SKU-{index},8900{index:09d},1,10.00,20.00" for index in range(20_000)]
    records, errors = service()._parse("opening-stock.csv", (headers + "\n" + "\n".join(rows)).encode())
    assert errors == []
    assert len(records) == 20_000
    normalized, row_errors = service()._normalize_row(records[-1])
    assert row_errors == []
    assert normalized["quantity"] == "1"


def test_rejects_formula_and_duplicate_headers() -> None:
    records, errors = service()._parse("opening-stock.csv", b"sku,sku\nA,B\n")
    assert records == []
    assert errors[0][0] == "DUPLICATE_HEADER"

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["product_name", "category", "subcategory", "brand", "sku", "barcode", "quantity", "purchase_cost", "selling_price"])
    sheet.append(["Product", "Women", "Kurtas", "Brand", "SKU", "123", "=1+1", "10", "20"])
    content = BytesIO(); workbook.save(content)
    records, errors = service()._parse("opening-stock.xlsx", content.getvalue())
    assert records == []
    assert errors[0][0] == "FORMULA_NOT_ALLOWED"


def test_rejects_invalid_quantity_and_price() -> None:
    row = {"product_name": "Product", "category": "Women", "subcategory": "Kurtas", "brand": "Brand", "sku": "SKU", "barcode": "123", "quantity": "1.5", "purchase_cost": "-1", "selling_price": "200", "mrp": "100"}
    _, errors = service()._normalize_row(row)
    assert {error[1] for error in errors} >= {"INVALID_QUANTITY", "INVALID_MONEY", "SELLING_PRICE_EXCEEDS_MRP"}
