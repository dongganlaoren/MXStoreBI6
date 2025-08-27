from app.extensions import db
from app.models import Store, User
from app.models.enums import RoleType


def test_store_crud(db_session):
    s = Store(store_id="91001", store_name="测试店铺")
    db.session.add(s)
    db.session.commit()

    got = Store.query.get("91001")
    assert got is not None
    assert got.store_name == "测试店铺"

    got.store_name = "测试店铺-更新"
    db.session.commit()

    got2 = Store.query.get("91001")
    assert got2.store_name == "测试店铺-更新"

    db.session.delete(got2)
    db.session.commit()

    assert Store.query.get("91001") is None


def test_user_with_optional_store(db_session):
    # 管理组用户无需店铺
    admin = User(username="root", role=RoleType.ADMIN)
    admin.set_password("x")
    db.session.add(admin)
    db.session.commit()

    loaded = User.query.filter_by(username="root").first()
    assert loaded is not None
    assert loaded.store_id is None

    # 门店组用户关联店铺
    s = Store(store_id="92001", store_name="分店A")
    db.session.add(s)
    emp = User(username="emp1", role=RoleType.EMPLOYEE, store_id="92001")
    emp.set_password("y")
    db.session.add(emp)
    db.session.commit()

    emp_loaded = User.query.filter_by(username="emp1").first()
    assert emp_loaded is not None
    assert emp_loaded.store_id == "92001"
