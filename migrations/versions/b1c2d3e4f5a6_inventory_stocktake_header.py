"""inventory-stocktake header table

Revision ID: b1c2d3e4f5a6
Revises: 9a1b2c3d4e5f
Create Date: 2026-02-04

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "9a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mx_stocktake_header",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.String(length=32), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("committed_by", sa.String(length=64), nullable=True),
        sa.Column("committed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("store_id", "check_date", name="uq_stocktake_header_store_date"),
    )

    op.create_index("ix_mx_stocktake_store_date", "mx_stocktake_header", ["store_id", "check_date"], unique=False)

    with op.batch_alter_table("mx_inventory_check") as batch_op:
        batch_op.add_column(sa.Column("header_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_mx_inv_header_id", ["header_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_mx_inv_header",
            "mx_stocktake_header",
            ["header_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("mx_inventory_check") as batch_op:
        batch_op.drop_constraint("fk_mx_inv_header", type_="foreignkey")
        batch_op.drop_index("ix_mx_inv_header_id")
        batch_op.drop_column("header_id")

    op.drop_index("ix_mx_stocktake_store_date", table_name="mx_stocktake_header")
    op.drop_table("mx_stocktake_header")
