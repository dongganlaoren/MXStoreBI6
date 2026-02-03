"""inventory-stocktake tables

Revision ID: 9a1b2c3d4e5f
Revises: 8c4a2dd7a1b0
Create Date: 2026-02-03

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9a1b2c3d4e5f"
down_revision = "8c4a2dd7a1b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mx_material_info",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_code", sa.String(length=64), nullable=False),
        sa.Column("cn_name", sa.String(length=255), nullable=False),
        sa.Column("th_name", sa.String(length=255), nullable=True),
        sa.Column("spec_model", sa.String(length=255), nullable=False),
        sa.Column("per_group_qty", sa.Integer(), nullable=False),
        sa.Column("price_per_case", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_per_group", sa.Numeric(12, 2), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("safety_stock", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="启用"),
        sa.Column("product_image", sa.String(length=255), nullable=True),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("material_code", name="uq_mx_material_code"),
    )
    op.create_index("ix_mx_material_category", "mx_material_info", ["category"], unique=False)
    op.create_index("ix_mx_material_code", "mx_material_info", ["material_code"], unique=False)

    op.create_table(
        "mx_inventory_check",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.String(length=32), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("material_code", sa.String(length=64), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("spec_model", sa.String(length=255), nullable=True),
        sa.Column("remaining_case_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_group_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("operator", sa.String(length=64), nullable=True),
        sa.Column("operated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("store_id", "check_date", "material_code", name="uq_check_store_date_material"),
    )
    op.create_index("ix_mx_inv_store_date", "mx_inventory_check", ["store_id", "check_date"], unique=False)
    op.create_index("ix_mx_inv_material_code", "mx_inventory_check", ["material_code"], unique=False)
    op.create_index("ix_mx_inv_valid_until", "mx_inventory_check", ["valid_until"], unique=False)


def downgrade():
    op.drop_index("ix_mx_inv_valid_until", table_name="mx_inventory_check")
    op.drop_index("ix_mx_inv_material_code", table_name="mx_inventory_check")
    op.drop_index("ix_mx_inv_store_date", table_name="mx_inventory_check")
    op.drop_table("mx_inventory_check")

    op.drop_index("ix_mx_material_code", table_name="mx_material_info")
    op.drop_index("ix_mx_material_category", table_name="mx_material_info")
    op.drop_table("mx_material_info")
