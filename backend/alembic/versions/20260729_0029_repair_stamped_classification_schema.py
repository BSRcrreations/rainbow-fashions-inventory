"""repair stamped classification and purchase discount schema

Revision ID: 20260729_0029
Revises: 20260729_0028
Create Date: 2026-07-29
"""

from alembic import op


revision = "20260729_0029"
down_revision = "20260729_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS description TEXT,
            ADD COLUMN IF NOT EXISTS hsn_sac VARCHAR(40),
            ADD COLUMN IF NOT EXISTS unit VARCHAR(40) NOT NULL DEFAULT 'Each',
            ADD COLUMN IF NOT EXISTS warehouse VARCHAR(120);
        """
    )
    op.execute("UPDATE products SET unit = 'Each' WHERE unit IS NULL OR btrim(unit) = ''")

    op.execute(
        """
        ALTER TABLE purchases
            ADD COLUMN IF NOT EXISTS invoice_discount_type VARCHAR(40) NOT NULL DEFAULT 'NONE',
            ADD COLUMN IF NOT EXISTS invoice_discount_percentage NUMERIC(7, 4) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS invoice_discount_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS invoice_discount_reason VARCHAR(500),
            ADD COLUMN IF NOT EXISTS invoice_discount_allocation_method VARCHAR(40) NOT NULL DEFAULT 'BY_ITEM_VALUE',
            ADD COLUMN IF NOT EXISTS invoice_tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0;
        """
    )

    op.execute(
        """
        ALTER TABLE purchase_items
            ADD COLUMN IF NOT EXISTS proposed_product_name VARCHAR(180),
            ADD COLUMN IF NOT EXISTS selling_price NUMERIC(12, 2),
            ADD COLUMN IF NOT EXISTS manufacturing_date DATE,
            ADD COLUMN IF NOT EXISTS create_new_product BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS variant_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS classification_verified BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS classification_verified_by UUID,
            ADD COLUMN IF NOT EXISTS classification_verified_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS list_unit_price NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS invoiced_unit_price NUMERIC(18, 2),
            ADD COLUMN IF NOT EXISTS discount_type VARCHAR(40) NOT NULL DEFAULT 'NONE',
            ADD COLUMN IF NOT EXISTS discount_percentage NUMERIC(7, 4) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS discount_per_unit NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS discount_reason VARCHAR(500),
            ADD COLUMN IF NOT EXISTS discount_source VARCHAR(40) NOT NULL DEFAULT 'INVOICE_EXTRACTED',
            ADD COLUMN IF NOT EXISTS free_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS chargeable_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS accepted_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS gross_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS taxable_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS net_line_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS effective_unit_cost NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS landed_unit_cost NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS allocated_invoice_discount NUMERIC(18, 2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS promotion_id UUID,
            ADD COLUMN IF NOT EXISTS discount_rule_id UUID,
            ADD COLUMN IF NOT EXISTS discount_verified BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS discount_verified_by UUID,
            ADD COLUMN IF NOT EXISTS discount_verified_at TIMESTAMP WITH TIME ZONE;
        """
    )
    op.execute(
        """
        UPDATE purchase_items
        SET proposed_product_name = COALESCE(proposed_product_name, product_name),
            list_unit_price = CASE WHEN list_unit_price = 0 THEN purchase_price ELSE list_unit_price END,
            invoiced_unit_price = COALESCE(invoiced_unit_price, purchase_price),
            chargeable_quantity = CASE WHEN chargeable_quantity = 0 THEN quantity ELSE chargeable_quantity END,
            accepted_quantity = CASE WHEN accepted_quantity = 0 THEN quantity ELSE accepted_quantity END,
            gross_amount = CASE WHEN gross_amount = 0 THEN quantity * purchase_price ELSE gross_amount END,
            discount_amount = CASE WHEN discount_amount = 0 THEN discount ELSE discount_amount END,
            taxable_amount = CASE WHEN taxable_amount = 0 THEN GREATEST((quantity * purchase_price) - discount, 0) ELSE taxable_amount END,
            net_line_amount = CASE WHEN net_line_amount = 0 THEN line_total ELSE net_line_amount END,
            effective_unit_cost = CASE
                WHEN effective_unit_cost = 0 AND quantity > 0 THEN GREATEST((quantity * purchase_price) - discount, 0) / quantity
                ELSE effective_unit_cost
            END,
            landed_unit_cost = CASE
                WHEN landed_unit_cost = 0 AND quantity > 0 THEN GREATEST((quantity * purchase_price) - discount, 0) / quantity
                ELSE landed_unit_cost
            END,
            discount_type = CASE WHEN discount_type = 'NONE' AND discount > 0 THEN 'FIXED_PER_LINE' ELSE discount_type END;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_purchase_items_classification_verified_by') THEN
                ALTER TABLE purchase_items ADD CONSTRAINT fk_purchase_items_classification_verified_by
                FOREIGN KEY (classification_verified_by) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_purchase_items_discount_verified_by') THEN
                ALTER TABLE purchase_items ADD CONSTRAINT fk_purchase_items_discount_verified_by
                FOREIGN KEY (discount_verified_by) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Forward-only repair for stamped databases. Dropping columns here could
    # remove valid data on correctly migrated environments.
    pass
