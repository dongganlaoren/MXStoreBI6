"""inventory-stocktake draft table

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-02-06

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mx_inventory_draft",
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
        sa.Column("header_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("store_id", "check_date", "material_code", name="uq_draft_store_date_material"),
    )

    op.create_index("ix_mx_draft_store_date", "mx_inventory_draft", ["store_id", "check_date"], unique=False)
    op.create_index("ix_mx_draft_material_code", "mx_inventory_draft", ["material_code"], unique=False)
    op.create_index("ix_mx_draft_valid_until", "mx_inventory_draft", ["valid_until"], unique=False)
    op.create_index("ix_mx_draft_header_id", "mx_inventory_draft", ["header_id"], unique=False)

    op.create_foreign_key(
        "fk_mx_draft_header",
        "mx_inventory_draft",
        "mx_stocktake_header",
        ["header_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_mx_draft_header", "mx_inventory_draft", type_="foreignkey")
    op.drop_index("ix_mx_draft_header_id", table_name="mx_inventory_draft")
    op.drop_index("ix_mx_draft_valid_until", table_name="mx_inventory_draft")
    op.drop_index("ix_mx_draft_material_code", table_name="mx_inventory_draft")
    op.drop_index("ix_mx_draft_store_date", table_name="mx_inventory_draft")
    op.drop_table("mx_inventory_draft")
