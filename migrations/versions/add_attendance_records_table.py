"""添加 attendance_records 表

Revision ID: add_attendance_records_table
Revises: 946897165bc9
Create Date: 2025-08-30 21:45:00

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_attendance_records_table'
down_revision = '946897165bc9'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 attendance_records 表，添加注释以匹配生产数据库风格
    op.create_table(
        'attendance_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='考勤记录ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('store_id', sa.String(length=32), nullable=True, comment='门店ID'),
        sa.Column('action', sa.Enum('CLOCK_IN', 'CLOCK_OUT', name='attendanceaction'), nullable=False,
                  comment='考勤动作（签到/签退）'),
        sa.Column('source', sa.Enum('WEB', 'LINE', 'API', name='attendancesource'), nullable=False, comment='考勤来源'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, comment='考勤时间'),
        sa.Column('latitude', sa.Float(), nullable=True, comment='纬度'),
        sa.Column('longitude', sa.Float(), nullable=True, comment='经度'),
        sa.Column('location_name', sa.String(length=255), nullable=True, comment='地点名称'),
        sa.Column('photo_path', sa.String(length=255), nullable=True, comment='照片路径'),
        sa.Column('notes', sa.String(length=500), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    # 使用 batch_alter_table 创建索引，保持与本地迁移一致
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_attendance_records_store_id'), ['store_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_attendance_records_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_attendance_records_user_id'), ['user_id'], unique=False)


def downgrade():
    # 按相反顺序删除索引和表
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_attendance_records_user_id'))
        batch_op.drop_index(batch_op.f('ix_attendance_records_timestamp'))
        batch_op.drop_index(batch_op.f('ix_attendance_records_store_id'))
    op.drop_table('attendance_records')
    # 注意：MySQL 在删除最后一个使用 ENUM 的列时会自动删除 ENUM 类型
