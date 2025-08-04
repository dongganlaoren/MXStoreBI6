"""Merge multiple heads

Revision ID: b7a4466cf027
Revises: 9f673d59a005, af29a7d9db10
Create Date: 2025-08-04 21:33:09.115246

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7a4466cf027'
down_revision = ('9f673d59a005', 'af29a7d9db10')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
