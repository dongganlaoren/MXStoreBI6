"""store-scoped inventory-stocktake drafts (one per store)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-06

This migration changes draft uniqueness from (store_id, check_date, material_code)
into (store_id, material_code), so each store has at most one effective draft
set (independent of date). Existing rows are preserved.

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    # Drop old unique constraint
    with op.batch_alter_table("mx_inventory_draft") as batch:
        batch.drop_constraint("uq_draft_store_date_material", type_="unique")
        batch.create_unique_constraint("uq_draft_store_material", ["store_id", "material_code"])

    # Helpful index for store-scoped reads
    op.create_index(
        "ix_mx_draft_store",
        "mx_inventory_draft",
        ["store_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_mx_draft_store", table_name="mx_inventory_draft")

    with op.batch_alter_table("mx_inventory_draft") as batch:
        batch.drop_constraint("uq_draft_store_material", type_="unique")
        batch.create_unique_constraint("uq_draft_store_date_material", ["store_id", "check_date", "material_code"])
