"""Add missing foreign keys to renovation tables.

This repository originally introduced the renovation module tables without
referencing base tables (users/stores) to keep the then-incomplete migration
chain runnable.

Now that core business tables exist, we can add the proper FK constraints so
that the database schema matches the SQLAlchemy models.

Production safety notes:
- This migration is written to be "safe to re-run" in the sense that it skips
  creating a FK constraint if it already exists (common when a DB was manually
  patched or migrated via other tooling).
- For MySQL, adding FK constraints can fail if existing data violates the
  constraint; see PRODUCTION_MIGRATION_GUIDE.md for a pre-check SQL.

Revision ID: 8c4a2dd7a1b0
Revises: 6d52051b9c5f
Create Date: 2026-01-30

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8c4a2dd7a1b0"
down_revision = "6d52051b9c5f"
branch_labels = None
depends_on = None


def _fk_exists(table_name: str, fk_name: str) -> bool:
    """Check whether a FK constraint name exists on a given table."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        fks = insp.get_foreign_keys(table_name)
    except Exception:
        # Extremely defensive: if inspection fails for any dialect reason,
        # fall back to attempting to create the FK and let the DB decide.
        return False

    for fk in fks:
        if fk.get("name") == fk_name:
            return True
    return False


def upgrade():
    # Use batch mode for SQLite compatibility (ALTER TABLE limitations).

    # renovation_attachments.uploaded_by -> users.user_id
    fk = "fk_renovation_attachments_uploaded_by_users"
    if not _fk_exists("renovation_attachments", fk):
        with op.batch_alter_table("renovation_attachments") as batch_op:
            batch_op.create_foreign_key(
                fk,
                "users",
                ["uploaded_by"],
                ["user_id"],
            )

    # renovation_records.operator_id -> users.user_id
    fk = "fk_renovation_records_operator_id_users"
    if not _fk_exists("renovation_records", fk):
        with op.batch_alter_table("renovation_records") as batch_op:
            batch_op.create_foreign_key(
                fk,
                "users",
                ["operator_id"],
                ["user_id"],
            )

    # renovation_tasks.* -> users/stores
    fk = "fk_renovation_tasks_store_id_stores"
    if not _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.create_foreign_key(
                fk,
                "stores",
                ["store_id"],
                ["store_id"],
            )

    fk = "fk_renovation_tasks_created_by_users"
    if not _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.create_foreign_key(
                fk,
                "users",
                ["created_by"],
                ["user_id"],
            )

    fk = "fk_renovation_tasks_assigned_to_users"
    if not _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.create_foreign_key(
                fk,
                "users",
                ["assigned_to"],
                ["user_id"],
            )

    fk = "fk_renovation_tasks_verifier_id_users"
    if not _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.create_foreign_key(
                fk,
                "users",
                ["verifier_id"],
                ["user_id"],
            )


def downgrade():
    # Drop constraints only if present.

    fk = "fk_renovation_tasks_verifier_id_users"
    if _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")

    fk = "fk_renovation_tasks_assigned_to_users"
    if _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")

    fk = "fk_renovation_tasks_created_by_users"
    if _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")

    fk = "fk_renovation_tasks_store_id_stores"
    if _fk_exists("renovation_tasks", fk):
        with op.batch_alter_table("renovation_tasks") as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")

    fk = "fk_renovation_records_operator_id_users"
    if _fk_exists("renovation_records", fk):
        with op.batch_alter_table("renovation_records") as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")

    fk = "fk_renovation_attachments_uploaded_by_users"
    if _fk_exists("renovation_attachments", fk):
        with op.batch_alter_table("renovation_attachments") as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")
