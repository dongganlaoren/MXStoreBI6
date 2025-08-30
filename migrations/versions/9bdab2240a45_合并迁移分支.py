"""合并迁移分支

Revision ID: 9bdab2240a45
Revises: add_attendance_records_table, e5d89116a8fc
Create Date: 2025-08-30 21:44:47.618231

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9bdab2240a45'
down_revision = ('add_attendance_records_table', 'e5d89116a8fc')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
