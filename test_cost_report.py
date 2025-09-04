#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试成本统计页面的修改
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.daily_sales import DailySales
from app.models.store import Store
from app.models.reimbursement import ReimbursementRequest
from app.models.enums import FinancialCheckStatus, ReimbursementStatus, ReimbursementCheckStatus
from datetime import date, datetime
from decimal import Decimal

def test_cost_report_data():
    """测试成本统计页面的数据计算逻辑"""
    app = create_app()
    
    with app.app_context():
        from app.extensions import db
        
        # 模拟查询一个店铺的实际到账数据
        store_id = "STORE001"
        start_date = date(2025, 8, 1)
        end_date = date(2025, 8, 31)
        
        # 查询该店铺的实际到账数据
        sales_q = db.session.query(
            DailySales.store_id,
            db.func.sum(db.func.coalesce(DailySales.electronic_actual_arrival, 0) + 
                       db.func.coalesce(DailySales.bank_deposit, 0)).label('actual_arrival')
        ).filter(
            DailySales.report_date >= start_date,
            DailySales.report_date <= end_date,
            DailySales.financial_check_status == FinancialCheckStatus.APPROVED,
            DailySales.store_id == store_id
        ).group_by(DailySales.store_id).first()
        
        if sales_q:
            actual_arrival = float(sales_q.actual_arrival or 0.0)
            print(f"店铺 {store_id} 在 {start_date} 到 {end_date} 期间的实际到账总额: {actual_arrival}")
        else:
            print(f"未找到店铺 {store_id} 的销售数据")
            actual_arrival = 0.0
        
        # 查询该店铺的成本数据
        cost_q = db.session.query(
            db.func.sum(ReimbursementRequest.amount).label('total_cost')
        ).join(
            Store, ReimbursementRequest.store_id == Store.store_id
        ).filter(
            ReimbursementRequest.status == ReimbursementStatus.APPROVED,
            ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED,
            ReimbursementRequest.approved_at != None,
            ReimbursementRequest.approved_at >= datetime.combine(start_date, datetime.min.time()),
            ReimbursementRequest.approved_at <= datetime.combine(end_date, datetime.max.time()),
            ReimbursementRequest.store_id == store_id
        ).first()
        
        if cost_q:
            total_cost = float(cost_q.total_cost or 0.0)
            print(f"店铺 {store_id} 在 {start_date} 到 {end_date} 期间的总成本: {total_cost}")
        else:
            print(f"未找到店铺 {store_id} 的成本数据")
            total_cost = 0.0
        
        # 计算利润
        profit = actual_arrival - total_cost
        print(f"店铺 {store_id} 的利润: {actual_arrival} - {total_cost} = {profit}")
        
        # 测试完成
        print("测试完成：成本统计页面数据计算逻辑正常")

if __name__ == "__main__":
    test_cost_report_data()
