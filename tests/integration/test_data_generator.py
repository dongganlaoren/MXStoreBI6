#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据生成器
用于创建测试环境所需的基础数据
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ['FLASK_ENV'] = 'development'

from app import create_app
from app.extensions import db
from app.models.store import Store
from app.models.user import User
from app.models.daily_sales import DailySales
from app.models.enums import UserRole, FinancialCheckStatus
from werkzeug.security import generate_password_hash
import config

def create_test_data():
    """创建测试数据"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        print("=== 创建测试数据 ===\n")
        
        # 1. 创建测试用户（如果不存在）
        print("1. 创建测试用户")
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('password'),
                role=UserRole.STAFF,
                store_id='190'  # 使用已存在的店铺ID
            )
            db.session.add(test_user)
            print("   ✓ 创建测试用户: testuser")
        else:
            print("   ✓ 测试用户已存在")
        
        # 2. 检查店铺数据
        print("\n2. 检查店铺数据")
        stores = Store.query.all()
        takeaway_count = Store.query.filter_by(third_party_platform=True).count()
        no_takeaway_count = Store.query.filter_by(third_party_platform=False).count()
        
        print(f"   总店铺数: {len(stores)}")
        print(f"   开通外卖平台: {takeaway_count} 家")
        print(f"   未开通外卖平台: {no_takeaway_count} 家")
        
        # 3. 创建测试日报数据
        print("\n3. 创建测试日报数据")
        test_date = date.today()
        
        # 为开通外卖平台的店铺创建测试数据
        takeaway_store = Store.query.filter_by(third_party_platform=True).first()
        if takeaway_store:
            existing = DailySales.query.filter_by(
                store_id=takeaway_store.store_id,
                report_date=test_date
            ).first()
            
            if not existing:
                test_report = DailySales(
                    user_id=test_user.user_id,
                    store_id=takeaway_store.store_id,
                    report_date=test_date,
                    cash_income=1000.00,
                    pos_income=2000.00,
                    pos_info_completed=False,
                    takeaway_info_completed=False,
                    actual_arrival_info_completed=False
                )
                db.session.add(test_report)
                print(f"   ✓ 为开通外卖店铺创建测试日报: {takeaway_store.store_name}")
        
        # 为未开通外卖平台的店铺创建测试数据
        no_takeaway_store = Store.query.filter_by(third_party_platform=False).first()
        if no_takeaway_store:
            existing = DailySales.query.filter_by(
                store_id=no_takeaway_store.store_id,
                report_date=test_date
            ).first()
            
            if not existing:
                test_report = DailySales(
                    user_id=test_user.user_id,
                    store_id=no_takeaway_store.store_id,
                    report_date=test_date,
                    cash_income=800.00,
                    pos_income=1500.00,
                    pos_info_completed=False,
                    takeaway_info_completed=False,  # 将在逻辑中自动设为True
                    actual_arrival_info_completed=False
                )
                db.session.add(test_report)
                print(f"   ✓ 为未开通外卖店铺创建测试日报: {no_takeaway_store.store_name}")
        
        db.session.commit()
        print("\n✓ 测试数据创建完成")
        
        # 4. 数据统计
        print("\n=== 数据统计 ===")
        print(f"用户总数: {User.query.count()}")
        print(f"店铺总数: {Store.query.count()}")
        print(f"今日日报数: {DailySales.query.filter_by(report_date=test_date).count()}")

def clean_test_data():
    """清理测试数据"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        print("=== 清理测试数据 ===\n")
        
        test_date = date.today()
        
        # 删除今天的测试日报
        test_reports = DailySales.query.filter_by(report_date=test_date).all()
        for report in test_reports:
            db.session.delete(report)
        
        # 删除测试用户
        test_user = User.query.filter_by(username='testuser').first()
        if test_user:
            db.session.delete(test_user)
            print("   ✓ 删除测试用户")
        
        db.session.commit()
        print("✓ 测试数据清理完成")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'clean':
        clean_test_data()
    else:
        create_test_data()
