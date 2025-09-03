from datetime import datetime, date, timedelta
from decimal import Decimal
import sys
import os

# ensure project root is on sys.path for imports when running script directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from config import TestingConfig
from app.models import User, Store, DailySales, ReimbursementRequest
from app.models.enums import (
    RoleType, FinancialCheckStatus, ReimbursementStatus, ReimbursementPrimaryCategory, ReimbursementSecondaryCategory
)

app = create_app(TestingConfig)
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

with app.app_context():
    db.create_all()
    # create stores
    stores = [Store(store_id='S001', store_name='测试门店1'), Store(store_id='S002', store_name='测试门店2'), Store(store_id='S003', store_name='测试门店3')]
    for s in stores:
        db.session.add(s)
    db.session.commit()

    today = date.today()
    last_month = today.replace(day=1) - timedelta(days=1)
    approved_time = datetime.combine(last_month, datetime.min.time())

    # sales
    sales_data = [
        DailySales(store_id='S001', user_id=1, report_date=last_month, actual_sales=50000.0, financial_check_status=FinancialCheckStatus.APPROVED),
        DailySales(store_id='S002', user_id=1, report_date=last_month, actual_sales=30000.0, financial_check_status=FinancialCheckStatus.APPROVED),
        DailySales(store_id='S003', user_id=1, report_date=last_month, actual_sales=20000.0, financial_check_status=FinancialCheckStatus.APPROVED)
    ]
    for s in sales_data:
        db.session.add(s)

    # costs
    cost_data = [
        ReimbursementRequest(submitter_id=1, store_id='S001', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('15000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S001', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.UTILITIES, amount=Decimal('5000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S002', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('12000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S003', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('25000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1)
    ]
    for c in cost_data:
        db.session.add(c)

    db.session.commit()

    # run queries similar to profit_loss_reports_center
    start_date_sel = date(last_month.year, last_month.month, 1)
    end_date_sel = date(last_month.year, last_month.month, last_month.day)

    from sqlalchemy import func
    sales_query = db.session.query(DailySales.store_id, func.sum(DailySales.actual_sales).label('total_revenue')).filter(DailySales.report_date >= start_date_sel, DailySales.report_date <= end_date_sel)
    sales_data_q = sales_query.group_by(DailySales.store_id).all()
    print('sales_data_q:', sales_data_q)

    cost_query = db.session.query(ReimbursementRequest.store_id, func.sum(ReimbursementRequest.amount).label('total_cost')).join(Store, ReimbursementRequest.store_id == Store.store_id).filter(ReimbursementRequest.status == ReimbursementStatus.APPROVED, ReimbursementRequest.check_status == None or ReimbursementRequest.check_status == None, ReimbursementRequest.approved_at != None, ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()), ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time()))
    try:
        cost_data_q = cost_query.group_by(ReimbursementRequest.store_id).all()
    except Exception as e:
        print('cost query error:', e)
        cost_data_q = []
    print('cost_data_q:', cost_data_q)

    # also run simple sum
    total_cost = db.session.query(func.sum(ReimbursementRequest.amount)).filter(ReimbursementRequest.status == ReimbursementStatus.APPROVED).scalar()
    print('total_cost scalar:', total_cost)

    db.drop_all()

print('done')
