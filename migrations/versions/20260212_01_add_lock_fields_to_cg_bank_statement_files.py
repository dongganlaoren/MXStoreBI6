"""add lock fields to cg_bank_statement_files

Revision ID: 20260212_01
Revises: 20260211_01
Create Date: 2026-02-12

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260212_01'
down_revision = '20260211_01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'cg_bank_statement_files',
        sa.Column(
            'is_locked',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment='保存后只读锁定',
        ),
    )
    op.add_column(
        'cg_bank_statement_files',
        sa.Column('locked_at', sa.DateTime(), nullable=True, comment='锁定时间'),
    )
    op.alter_column('cg_bank_statement_files', 'is_locked', server_default=None)


def downgrade():
    op.drop_column('cg_bank_statement_files', 'locked_at')
    op.drop_column('cg_bank_statement_files', 'is_locked')
