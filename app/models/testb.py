# app/models/testb.py

from datetime import datetime

from app.extensions import db


class TestB(db.Model):
    """新的测试表：testb

    包含 id, name, value, created_at, updated_in
    """
    __tablename__ = "testb"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")
    name = db.Column(db.String(100), nullable=False, comment="名称")
    value = db.Column(db.Float, nullable=True, comment="数值，可选")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_in = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<TestB id={self.id} name={self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_in": self.updated_in.isoformat() if self.updated_in else None,
        }
