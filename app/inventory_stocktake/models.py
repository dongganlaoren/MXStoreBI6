"""Models for inventory-stocktake.

注意：需求文档中提到的表名（mx_material_info / mx_inventory_check）在当前仓库中并不存在，
这里按需求新增对应表的 SQLAlchemy 模型，避免侵入其他模块。

如果生产库已有同名表/不同字段，请在落库前对齐并调整迁移。
"""

from __future__ import annotations

from datetime import datetime, date

from app.extensions import db


class MXMaterialInfo(db.Model):
    """物料信息表：用于盘点时校验物料编码、货值计算取单价。"""

    __tablename__ = "mx_material_info"

    id = db.Column(db.Integer, primary_key=True)

    material_code = db.Column(db.String(64), unique=True, nullable=False, index=True, comment="物料编码")
    cn_name = db.Column(db.String(255), nullable=False, comment="中文名称")
    th_name = db.Column(db.String(255), nullable=True, comment="泰文名称")
    spec_model = db.Column(db.String(255), nullable=False, comment="规格型号")

    per_group_qty = db.Column(db.Integer, nullable=False, comment="每组数量")
    price_per_case = db.Column(db.Numeric(12, 2), nullable=True, comment="每件单价（泰铢）")
    price_per_group = db.Column(db.Numeric(12, 2), nullable=True, comment="每组单价（泰铢）")

    category = db.Column(db.String(128), nullable=False, index=True, comment="物料类别")
    safety_stock = db.Column(db.Integer, nullable=True, comment="安全库存")

    status = db.Column(db.String(16), nullable=False, default="启用", comment="状态：启用/禁用")

    product_image = db.Column(db.String(255), nullable=True, comment="预留产品图片字段（文本路径/标识）")
    remark = db.Column(db.String(255), nullable=True, comment="备注")

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class MXInventoryCheck(db.Model):
    """盘点明细：按“店铺 + 日期 + 物料编码”保存一行库存。"""

    __tablename__ = "mx_inventory_check"

    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.String(32), nullable=False, index=True, comment="店铺ID（对齐 stores.store_id）")
    check_date = db.Column(db.Date, nullable=False, index=True, default=date.today, comment="盘点日期")

    material_code = db.Column(db.String(64), nullable=False, index=True, comment="物料编码")
    material_name = db.Column(db.String(255), nullable=False, comment="物料名称（冗余，便于展示）")
    spec_model = db.Column(db.String(255), nullable=True, comment="规格（冗余，便于展示）")

    remaining_case_qty = db.Column(db.Integer, nullable=False, default=0, comment="剩余整件数")
    remaining_group_qty = db.Column(db.Integer, nullable=False, default=0, comment="剩余散件数")

    valid_until = db.Column(db.Date, nullable=True, index=True, comment="有效期至（用于到期前提醒）")

    operator = db.Column(db.String(64), nullable=True, comment="操作员（username）")
    operated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment="操作时间")

    __table_args__ = (
        db.UniqueConstraint("store_id", "check_date", "material_code", name="uq_check_store_date_material"),
    )
