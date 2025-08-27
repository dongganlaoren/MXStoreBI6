import io
from datetime import date

from app.extensions import db
from app.models import Store, User, DailySales, DailySalesAttachments
from app.models.enums import RoleType


def test_manage_report_create_saves_attachments(client, db_session):
    # 基础数据和登录
    s = Store(store_id="FX1", store_name="FStore", third_party_platform=True)
    admin = User(username="adfx", role=RoleType.ADMIN, user_status=1)
    admin.set_password("pw")
    db.session.add_all([s, admin])
    db.session.commit()
    client.post("/login", data={"username": "adfx", "password": "pw"}, follow_redirects=True)

    base = {
        "store_id": s.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "1",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
        "takeaway_amount": "8",
    }
    files = {
        "sales_slip_image": (io.BytesIO(b"a"), "a.jpg"),
        "bank_receipt_image": (io.BytesIO(b"b"), "b.jpg"),
        "electronic_actual_arrival_receipt": (io.BytesIO(b"c"), "c.jpg"),
        "takeaway_platform_receipt": (io.BytesIO(b"d"), "d.jpg"),
    }
    data = dict(base)
    data.update(files)

    r = client.post("/manage/report/create", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    # 断言日报与附件保存
    ds = DailySales.query.filter_by(store_id=s.store_id).order_by(DailySales.report_id.desc()).first()
    assert ds is not None
    attachments = DailySalesAttachments.query.filter_by(report_id=ds.report_id).all()
    assert len(attachments) >= 3  # 至少三类必需附件
