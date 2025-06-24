# app/models/user.py

from datetime import datetime

from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

# 从我们统一的 enums.py 文件中导入 RoleType
from .enums import RoleType


class User(UserMixin, db.Model):
    """
    系统用户模型
    """
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="用户主键，自增 ID")
    username = db.Column(db.String(64), unique=True, nullable=False, comment="登录用户名")
    password_hash = db.Column(db.String(255), nullable=False, comment="登录密码哈希")
    user_status = db.Column(db.Integer, nullable=False, default=1, comment="用户状态（1=活跃，0=禁用）")
    last_login_time = db.Column(db.DateTime, default=datetime.now, comment="最近一次登录时间")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    role = db.Column(db.Enum(RoleType), default=RoleType.EMPLOYEE, comment="用户角色")

    # 【核心修正】：在这里建立从 User 到 StoreStaff 的“一对一”关系
    # uselist=False 告诉 SQLAlchemy，一个 User 最多只会对应一个 StoreStaff 记录
    # cascade="all, delete-orphan" 确保了当我们删除一个用户时，他关联的员工档案也会被自动删除
    # backref="user" 会在 StoreStaff 对象上创建一个 .user 属性，方便反向查询
    staff_info = db.relationship("StoreStaff", uselist=False, backref="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        # 我们在 to_dict 中也加入了 staff_info，方便未来API的使用
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_status": self.user_status,
            "role": self.role.value,
            "staff_info": self.staff_info.to_dict() if self.staff_info else None
        }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_id)