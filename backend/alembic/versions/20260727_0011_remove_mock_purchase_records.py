"""remove historical mock OCR purchase records

Revision ID: 20260727_0011
Revises: 20260727_0010
Create Date: 2026-07-27
"""

from alembic import op


revision = "20260727_0011"
down_revision = "20260727_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The old mock OCR provider fabricated this exact supplier and invoice. Reverse
    # only its confirmed purchase movements before deleting the placeholder records.
    op.execute(
        """
        WITH mock_moves AS (
            SELECT stock_history.product_id, SUM(stock_history.qty) AS qty
            FROM stock_history
            JOIN purchases ON purchases.id = stock_history.purchase_id
            WHERE purchases.supplier_name = 'ARK Distributors'
              AND purchases.invoice_number = 'ARK-INV-1001'
              AND stock_history.movement_type = 'PURCHASE'
            GROUP BY stock_history.product_id
        )
        UPDATE products
        SET current_stock = GREATEST(0, products.current_stock - mock_moves.qty)
        FROM mock_moves
        WHERE products.id = mock_moves.product_id
        """
    )
    op.execute(
        """
        WITH mock_moves AS (
            SELECT stock_history.product_id, stock_history.store_id, SUM(stock_history.qty) AS qty
            FROM stock_history
            JOIN purchases ON purchases.id = stock_history.purchase_id
            WHERE purchases.supplier_name = 'ARK Distributors'
              AND purchases.invoice_number = 'ARK-INV-1001'
              AND stock_history.movement_type = 'PURCHASE'
            GROUP BY stock_history.product_id, stock_history.store_id
        )
        UPDATE product_inventory
        SET current_stock = GREATEST(0, product_inventory.current_stock - mock_moves.qty)
        FROM mock_moves
        WHERE product_inventory.product_id = mock_moves.product_id
          AND product_inventory.store_id = mock_moves.store_id
        """
    )
    op.execute(
        """
        DELETE FROM stock_history
        USING purchases
        WHERE purchases.id = stock_history.purchase_id
          AND purchases.supplier_name = 'ARK Distributors'
          AND purchases.invoice_number = 'ARK-INV-1001'
        """
    )
    op.execute("DELETE FROM purchases WHERE supplier_name = 'ARK Distributors' AND invoice_number = 'ARK-INV-1001'")
    op.execute("DELETE FROM suppliers WHERE name = 'ARK Distributors' AND NOT EXISTS (SELECT 1 FROM purchases WHERE purchases.supplier_id = suppliers.id)")


def downgrade() -> None:
    # Removed mock data is intentionally not recreated.
    pass
