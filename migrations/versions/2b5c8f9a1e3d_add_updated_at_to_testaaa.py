"""add updated_at to testaaa

Revision ID: 2b5c8f9a1e3d
Revises: 1b4aa505d0ce
Create Date: 2025-08-31 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '2b5c8f9a1e3d'
down_revision = '1b4aa505d0ce'
branch_labels = None
depends_on = None


def upgrade():
    # check if column exists first to avoid duplicate column error
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = [c['name'] for c in inspector.get_columns('testaaa')]
    if 'updated_at' not in existing_cols:
        # add updated_at column (nullable) with comment
        op.add_column('testaaa', sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'))


def downgrade():
    # remove updated_at column
    op.drop_column('testaaa', 'updated_at')
