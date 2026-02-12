"""add parser cache fields to cg_bank_statement_files

Revision ID: 20260211_01
Revises:
Create Date: 2026-02-11

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260211_01'
down_revision = 'f66b1182829d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cg_bank_statement_files', sa.Column('parser_version', sa.String(length=32), nullable=True))
    op.add_column('cg_bank_statement_files', sa.Column('parsed_summary_json', sa.JSON(), nullable=True))
    op.add_column('cg_bank_statement_files', sa.Column('parsed_txns_json', sa.JSON(), nullable=True))
    op.add_column('cg_bank_statement_files', sa.Column('parsed_errors_json', sa.JSON(), nullable=True))
    op.add_column('cg_bank_statement_files', sa.Column('parsed_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('cg_bank_statement_files', 'parsed_at')
    op.drop_column('cg_bank_statement_files', 'parsed_errors_json')
    op.drop_column('cg_bank_statement_files', 'parsed_txns_json')
    op.drop_column('cg_bank_statement_files', 'parsed_summary_json')
    op.drop_column('cg_bank_statement_files', 'parser_version')
