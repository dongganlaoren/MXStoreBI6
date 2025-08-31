"""rename updated_at to updated_in on testaaa

Revision ID: 3c7d9e4b5f6a
Revises: 2b5c8f9a1e3d
Create Date: 2025-08-31 12:10:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '3c7d9e4b5f6a'
down_revision = '2b5c8f9a1e3d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = [c['name'] for c in inspector.get_columns('testaaa')]

    # drop updated_at if exists
    if 'updated_at' in existing_cols:
        op.drop_column('testaaa', 'updated_at')

    # add updated_in if not exists
    if 'updated_in' not in existing_cols:
        op.add_column('testaaa', sa.Column('updated_in', sa.DateTime(), nullable=True, comment='更新时间'))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = [c['name'] for c in inspector.get_columns('testaaa')]

    # drop updated_in if exists
    if 'updated_in' in existing_cols:
        op.drop_column('testaaa', 'updated_in')

    # add updated_at if not exists
    if 'updated_at' not in existing_cols:
        op.add_column('testaaa', sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'))
