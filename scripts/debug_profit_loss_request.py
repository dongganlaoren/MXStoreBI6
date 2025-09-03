import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from config import TestingConfig
from app.models import User, Store, DailySales, ReimbursementRequest
from app.models.enums import (
    RoleType, FinancialCheckStatus, ReimbursementStatus, ReimbursementPrimaryCategory, ReimbursementSecondaryCategory
)
from datetime import date, timedelta, datetime
from decimal import Decimal

app = create_app(TestingConfig)
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

with app.app_context():
    db.create_all()
    admin = User(username='admin', email='admin@test.com', role=RoleType.ADMIN)
    admin.set_password('admin123')
    db.session.add(admin)

    stores = [Store(store_id='S001', store_name='测试门店1'), Store(store_id='S002', store_name='测试门店2'), Store(store_id='S003', store_name='测试门店3')]
    for s in stores:
        db.session.add(s)
    db.session.commit()

    today = date.today()
    last_month = today.replace(day=1) - timedelta(days=1)
    approved_time = datetime.combine(last_month, datetime.min.time())

    sales_data = [
        DailySales(store_id='S001', user_id=1, report_date=last_month, actual_sales=50000.0, financial_check_status=FinancialCheckStatus.APPROVED),
        DailySales(store_id='S002', user_id=1, report_date=last_month, actual_sales=30000.0, financial_check_status=FinancialCheckStatus.APPROVED),
        DailySales(store_id='S003', user_id=1, report_date=last_month, actual_sales=20000.0, financial_check_status=FinancialCheckStatus.APPROVED)
    ]
    for s in sales_data:
        db.session.add(s)

    cost_data = [
        ReimbursementRequest(submitter_id=1, store_id='S001', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('15000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S001', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.UTILITIES, amount=Decimal('5000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S002', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('12000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S003', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('25000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1)
    ]
    for c in cost_data:
        db.session.add(c)

    db.session.commit()

    client = app.test_client()
    # login
    client.post('/login', data={'username':'admin','password':'admin123'})
    r = client.get('/profit_loss_reports')
    print(r.status_code)
    text = r.get_data(as_text=True)
    # print snippet around totals
    idx = text.find('总成本')
    print(text[idx:idx+200])
    # print entire summary block
    start = text.find('<div class="row mb-4">')
    print(text[start:start+800])

    # Also print found numbers
    print('contains 57,000:', '57,000.00' in text)
    print('contains 100,000:', '100,000.00' in text)

    # 打印对应的 cost_query SQL 与结果，复现视图中的查询条件
    from sqlalchemy import func
    cq = db.session.query(ReimbursementRequest.store_id, func.sum(ReimbursementRequest.amount).label('total_cost')).join(Store, ReimbursementRequest.store_id == Store.store_id).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementStatus.CHECKED) if hasattr(ReimbursementRequest, 'check_status') else (ReimbursementRequest.check_status == None),
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(date(last_month.year, last_month.month, 1), datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(date(last_month.year, last_month.month, last_month.day), datetime.max.time())
    )
    try:
        print('cost_query SQL:', cq.statement)
        print('cost_query result:', cq.group_by(ReimbursementRequest.store_id).all())
    except Exception as e:
        print('cost_query error:', e)

    db.drop_all()

print('done')
