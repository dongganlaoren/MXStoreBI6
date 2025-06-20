# app/models/user.py
import enum
from datetime import datetime

from app.extensions import db  # 导入数据库实例
from flask_login import UserMixin  # 导入 Flask-Login 的 UserMixin
from werkzeug.security import check_password_hash, generate_password_hash  # 导入密码哈希函数


class RoleType(enum.Enum):
    """
    用户角色枚举
    """
    ADMIN = "admin"  # 管理员
    HEAD_MANAGER = "head_manager"  # 总店长
    FINANCE = "finance"  # 财务
    BRANCH_MANAGER = "branch_manager"  # 分店长
    EMPLOYEE = "employee"  # 店员


class User(UserMixin, db.Model):
    """
    系统用户模型
    """

    __tablename__ = "users"  # 表名

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="用户主键，自增 ID")
    username = db.Column(db.String(64), unique=True, nullable=False, comment="登录用户名")
    password_hash = db.Column(db.String(255), nullable=False, comment="登录密码哈希")
    user_status = db.Column(db.Integer, nullable=False, default=1, comment="用户状态（1=活跃，0=禁用）")
    last_login_time = db.Column(db.DateTime, default=datetime.now, comment="最近一次登录时间")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    role = db.Column(db.Enum(RoleType), default=RoleType.EMPLOYEE, comment="用户角色 (admin, head_manager, finance, branch_manager, employee)")
    # 使用枚举类型

    def __repr__(self):
        return f"<User {self.username}>"  # 返回对象的字符串表示形式

    def to_dict(self):
        """
        将对象转换为字典
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_status": self.user_status,
            "last_login_time": self.last_login_time,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "role": self.role.value,  # 返回枚举的值
        }

    def set_password(self, password):
        """
        设置密码，对密码进行哈希处理
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        检查密码是否正确
        """
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """
        Flask-Login 需要的 get_id 方法
        """
        return str(self.user_id)