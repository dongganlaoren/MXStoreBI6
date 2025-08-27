from datetime import date
from io import BytesIO

from app.extensions import db
from app.models import User, Store, DailySales
from app.models.enums import RoleType, FinancialCheckStatus


def _ensure_store_with_sales(store_id: str, user_id: int):
    s = Store(store_id=store_id, store_name=f"Store {store_id}")
    db.session.add(s)
    # 插入一条本月已审核的日报数据（含外卖金额），满足统计逻辑
    db.session.add(DailySales(
        store_id=store_id,
        user_id=user_id,
        report_date=date.today(),
        pos_total=100.0,
        takeaway_amount=20.0,
        actual_sales=95.0,
        total_error=5.0,
        financial_check_status=FinancialCheckStatus.APPROVED,
    ))
    db.session.commit()
    return s


def test_main_index_with_admin_via_client(app, db_session, admin_user, client, login):
    # 准备门店与数据
    _ensure_store_with_sales('S001', admin_user.user_id)
    _ensure_store_with_sales('S002', admin_user.user_id)

    # 登录并访问根路径，跟随跳转进入 main.index
    login('admin', 'secret123')
    r = client.get('/', follow_redirects=True)
    assert r.status_code == 200


def test_admin_user_download_id_card_copy(client, db_session, admin_user, login):
    # 先创建一个员工用户
    u = User(username='u_file', role=RoleType.EMPLOYEE, user_status=1)
    u.set_password('pw')
    db.session.add(u)
    db.session.commit()

    # 登录管理员
    login('admin', 'secret123')

    # 未上传时下载应404
    r0 = client.get(f"/admin/users/{u.user_id}/download_id_card_copy")
    assert r0.status_code == 404

    # 提交带文件的编辑表单，触发保存身份证复印件
    data = {
        'real_name': 'RN',
        'employee_number': '',
        'role': RoleType.EMPLOYEE.value,
        'store_id': '',
        'id_card_copy': (BytesIO(b'fake image data'), 'id.jpg'),
    }
    r1 = client.post(
        f"/admin/users/{u.user_id}/edit",
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert r1.status_code == 200

    # 现在下载应成功（在线预览）
    r2 = client.get(f"/admin/users/{u.user_id}/download_id_card_copy")
    assert r2.status_code == 200
    # 不作为附件下载
    cd = r2.headers.get('Content-Disposition', '')
    assert 'attachment' not in cd.lower()
