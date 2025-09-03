import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from config import TestingConfig
from app.models import Store, ReimbursementRequest
from app.models.enums import ReimbursementPrimaryCategory, ReimbursementSecondaryCategory, ReimbursementStatus, ReimbursementCheckStatus
from datetime import date, timedelta, datetime
from decimal import Decimal

app = create_app(TestingConfig)
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

with app.app_context():
    db.create_all()
    stores = [Store(store_id='S001', store_name='测试门店1'), Store(store_id='S002', store_name='测试门店2'), Store(store_id='S003', store_name='测试门店3')]
    for s in stores:
        db.session.add(s)
    db.session.commit()

    today = date.today()
    last_month = today.replace(day=1) - timedelta(days=1)
    approved_time = datetime.combine(last_month, datetime.min.time())

    cost_data = [
        ReimbursementRequest(submitter_id=1, store_id='S001', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('15000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S001', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.UTILITIES, amount=Decimal('5000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S002', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('12000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1),
        ReimbursementRequest(submitter_id=1, store_id='S003', primary_category=ReimbursementPrimaryCategory.STORE_COST, secondary_category=ReimbursementSecondaryCategory.STORE_RENT, amount=Decimal('25000.00'), status=ReimbursementStatus.APPROVED, approved_at=approved_time, approver_id=1)
    ]
    for c in cost_data:
        db.session.add(c)
    db.session.commit()

    from sqlalchemy import func
    start_date_sel = date(last_month.year, last_month.month, 1)
    end_date_sel = date(last_month.year, last_month.month, last_month.day)

    # Build the same filter as in app.views.profit_loss_reports_center
    cost_query = db.session.query(
        ReimbursementRequest.store_id,
        func.sum(ReimbursementRequest.amount).label('total_cost')
    ).join(
        Store, ReimbursementRequest.store_id == Store.store_id
    ).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )

    print('SQL:', cost_query.statement)
    print('rows:', cost_query.group_by(ReimbursementRequest.store_id).all())

    # show raw reimbursements
    raws = db.session.query(ReimbursementRequest).all()
    print('raw reimbursements:', [(r.request_id, r.store_id, r.amount, r.status, r.check_status, r.approved_at) for r in raws])

    db.drop_all()

print('done')
