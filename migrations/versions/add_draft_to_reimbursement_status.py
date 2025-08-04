"""add DRAFT to reimbursement status enum

Revision ID: add_draft_to_reimbursement_status
Revises: b7a4466cf027
Create Date: 2025-08-04 14:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_draft_to_reimbursement_status'
down_revision = 'b7a4466cf027'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE reimbursement_requests MODIFY COLUMN status ENUM('PENDING','APPROVED','REJECTED','DRAFT') NOT NULL COMMENT '审批状态';"
    )


def downgrade():
    op.execute(
        "ALTER TABLE reimbursement_requests MODIFY COLUMN status ENUM('PENDING','APPROVED','REJECTED') NOT NULL COMMENT '审批状态';"
    )
