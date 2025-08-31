"""drop testaaa and create testb (idempotent)

Revision ID: 4d5e6f7a8b9c
Revises: 3c7d9e4b5f6a
Create Date: 2025-08-31 12:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '4d5e6f7a8b9c'
down_revision = '3c7d9e4b5f6a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # drop testaaa if exists (safe in production)
    if 'testaaa' in existing_tables:
        op.drop_table('testaaa')

    # create testb if not exists
    if 'testb' not in existing_tables:
        op.create_table(
            'testb',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='主键 ID'),
            sa.Column('name', sa.String(length=100), nullable=False, comment='名称'),
            sa.Column('value', sa.Float(), nullable=True, comment='数值，可选'),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'),
                      comment='创建时间'),
            sa.Column('updated_in', sa.DateTime(), nullable=True, comment='更新时间'),
            mysql_engine='InnoDB',
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # drop testb if exists
    if 'testb' in existing_tables:
        op.drop_table('testb')

    # recreate testaaa if not exists
    if 'testaaa' not in existing_tables:
        op.create_table(
            'testaaa',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='主键 ID'),
            sa.Column('name', sa.String(length=100), nullable=False, comment='名称'),
            sa.Column('value', sa.Float(), nullable=True, comment='数值，可选'),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'),
                      comment='创建时间'),
            sa.Column('updated_in', sa.DateTime(), nullable=True, comment='更新时间'),
            mysql_engine='InnoDB',
        )
