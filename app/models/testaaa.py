# app/models/testaaa.py

from datetime import datetime

from app.extensions import db


class TestAaa(db.Model):
    """测试用表：testaaa

    简单示例模型，包含基本字段与 to_dict 方法，便于后续迁移与使用。
    """
    __tablename__ = "testaaa"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")
    name = db.Column(db.String(100), nullable=False, comment="名称")
    value = db.Column(db.Float, nullable=True, comment="数值，可选")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<TestAaa id={self.id} name={self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
