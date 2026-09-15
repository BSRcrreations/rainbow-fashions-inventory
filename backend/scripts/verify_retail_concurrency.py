"""Verify concurrent retail writes in a new disposable local database.
Run from backend with RAINBOW_TEST_DATABASE_URL pointing at a local *_test DB.
The randomly named sibling database is created and removed by this script.
"""
import importlib.util
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text, make_url
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import User, ProductVariant, StockHistory
from app.schemas.sale import SaleCreate
from app.schemas.stock_scan import StockScanSessionCreate, QuickStockItemSet, StockScanConfirmRequest
from app.services.sale_service import SaleService
from app.services.stock_scan_service import StockScanService
from app.services.inventory_reconciliation_service import InventoryReconciliationService


def main():
    url = make_url(os.environ["RAINBOW_TEST_DATABASE_URL"])
    if url.host not in {"127.0.0.1", "localhost", "postgres"} or not url.database.endswith("_test"):
        raise RuntimeError("Only an explicitly disposable local *_test database is allowed")
    database = "rainbow_race_" + uuid4().hex[:12] + "_test"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = None
    with admin.connect() as connection: connection.execute(text(f'CREATE DATABASE "{database}"'))
    try:
        race_url = url.set(database=database)
        environment = {**os.environ, "APP_ENV": "testing", "DATABASE_URL": race_url.render_as_string(hide_password=False)}
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=environment, check=True, capture_output=True)
        engine = create_engine(race_url)
        spec = importlib.util.spec_from_file_location("retail_fixtures", "tests/test_master_retail_workflows.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with Session(engine, expire_on_commit=False) as db:
            shop = module.shop.__wrapped__(db); module.stock(shop, 1)
            owner_id = shop[1].id; variant_id = shop[3][0].id; product_id = shop[2].id
        barrier = Barrier(2)
        def checkout(key):
            with Session(engine) as db:
                owner = db.get(User, owner_id); barrier.wait()
                try:
                    bill = SaleService(db).create(SaleCreate(payment_mode="CASH", items=[{"product_variant_id": variant_id, "quantity": 1}]), owner, idempotency_key=key)
                    return {"status": 201, "id": str(bill.id)}
                except HTTPException as error: return {"status": error.status_code}
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(checkout, [str(uuid4()), str(uuid4())]))
        assert sum(result["status"] == 201 for result in results) == 1, results
        with Session(engine, expire_on_commit=False) as db:
            owner = db.get(User, owner_id); stock = StockScanService(db)
            draft = stock.create_session(StockScanSessionCreate(session_id=uuid4(), mode="DAILY_STOCK"), owner)
            stock.set_quick_item(draft.id, QuickStockItemSet(product_variant_id=variant_id, quantity=2, unit_cost=10), owner)
            draft_id = draft.id
        barrier = Barrier(2)
        def confirm(_):
            with Session(engine) as db:
                owner = db.get(User, owner_id); barrier.wait()
                return str(StockScanService(db).confirm(draft_id, StockScanConfirmRequest(), owner).id)
        with ThreadPoolExecutor(max_workers=2) as pool: ids = list(pool.map(confirm, range(2)))
        assert ids == [str(draft_id)] * 2
        barrier = Barrier(2); same_key = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool: repeated = list(pool.map(checkout, [same_key, same_key]))
        assert repeated[0] == repeated[1] and repeated[0]["status"] == 201, repeated
        with Session(engine) as db:
            assert db.get(ProductVariant, variant_id).current_stock == 1
            findings = InventoryReconciliationService(db).report(db.get(User, owner_id))
            assert all(row.category == "HEALTHY" for row in findings), findings
            movements = db.query(StockHistory).filter_by(product_id=product_id).count()
        print(json.dumps({"last_piece_race": results, "same_draft_confirmation": "one stock effect", "same_sale_key": "one invoice", "integrity": "HEALTHY", "movement_count": movements, "database": "new disposable database removed after check"}, indent=2))
    finally:
        if engine: engine.dispose()
        with admin.connect() as connection: connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()


if __name__ == "__main__": main()
