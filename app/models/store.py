# app/models/store.py
from app.extensions import db


class Store(db.Model):
    """店铺信息模型"""
    __tablename__ = "stores"

    store_id = db.Column(db.String(32), primary_key=True, comment="店铺唯一标识符")
    store_name = db.Column(db.String(100), nullable=False, comment="店铺名称")
    store_address = db.Column(db.String(255), comment="店铺地图地址链接")
    third_party_platform = db.Column(db.Boolean, default=False, comment="是否开启第三方外卖平台")

    def __repr__(self):
        return f"<Store {self.store_name}>"

    def to_dict(self):
        return {
            "store_id": self.store_id,
            "store_name": self.store_name,
            "store_address": self.store_address,
            "third_party_platform": self.third_party_platform,
        }
