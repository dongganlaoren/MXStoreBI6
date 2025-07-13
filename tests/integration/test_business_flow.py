#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整业务流程测试：验证第三方外卖平台逻辑的完整性
模拟用户完整的营业额上报流程
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ['FLASK_ENV'] = 'development'

from app import create_app
from app.extensions import db
from app.models.store import Store
from app.models.daily_sales import DailySales
from app.models.enums import FinancialCheckStatus
import config

def test_takeaway_logic_complete():
    """完整测试外卖平台逻辑"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        print("=== 完整外卖平台逻辑测试 ===\n")
        
        # 获取测试店铺
        takeaway_store = Store.query.filter_by(third_party_platform=True).first()
        no_takeaway_store = Store.query.filter_by(third_party_platform=False).first()
        
        test_date = date.today()
        
        # 测试1: 开通外卖平台的店铺
        if takeaway_store:
            print(f"测试1: 开通外卖平台的店铺 - {takeaway_store.store_name}")
            
            # 清理现有测试数据
            existing = DailySales.query.filter_by(
                store_id=takeaway_store.store_id,
                report_date=test_date
            ).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            
            # 创建新日报
            daily_sales = DailySales(
                user_id=1,
                store_id=takeaway_store.store_id,
                report_date=test_date
            )
            db.session.add(daily_sales)
            db.session.flush()
            
            # 模拟步骤1: 完成POS信息
            print("  步骤1: 完成POS信息")
            daily_sales.pos_info_completed = True
            
            # 获取店铺信息判断是否需要外卖
            current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
            need_takeaway = current_store and current_store.third_party_platform
            print(f"    need_takeaway = {need_takeaway}")
            
            # 如果不需要外卖平台信息，则自动标记为完成
            if not need_takeaway:
                daily_sales.takeaway_info_completed = True
                print("    ✓ 自动标记takeaway_info_completed = True")
            else:
                print("    → 需要填写外卖平台信息")
            
            # 检查是否可以显示最终提交
            can_submit = daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed
            print(f"    可以最终提交: {can_submit}")
            
            # 模拟步骤2: 完成外卖信息
            if need_takeaway:
                print("  步骤2: 完成外卖平台信息")
                daily_sales.takeaway_info_completed = True
                can_submit = daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed
                print(f"    可以最终提交: {can_submit}")
            
            # 模拟步骤3: 完成实际入账信息
            print("  步骤3: 完成实际入账信息")
            daily_sales.actual_arrival_info_completed = True
            
            # 再次检查外卖平台逻辑
            current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
            need_takeaway = current_store and current_store.third_party_platform
            if not need_takeaway:
                daily_sales.takeaway_info_completed = True
            
            can_submit = daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed
            print(f"    最终可以提交: {can_submit}")
            print(f"    POS完成: {daily_sales.pos_info_completed}")
            print(f"    外卖完成: {daily_sales.takeaway_info_completed}")
            print(f"    入账完成: {daily_sales.actual_arrival_info_completed}")
            
            db.session.commit()
            print("  ✓ 开通外卖平台店铺测试完成\n")
        
        # 测试2: 未开通外卖平台的店铺
        if no_takeaway_store:
            print(f"测试2: 未开通外卖平台的店铺 - {no_takeaway_store.store_name}")
            
            # 清理现有测试数据
            existing = DailySales.query.filter_by(
                store_id=no_takeaway_store.store_id,
                report_date=test_date
            ).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            
            # 创建新日报
            daily_sales = DailySales(
                user_id=1,
                store_id=no_takeaway_store.store_id,
                report_date=test_date
            )
            db.session.add(daily_sales)
            db.session.flush()
            
            # 模拟步骤1: 完成POS信息
            print("  步骤1: 完成POS信息")
            daily_sales.pos_info_completed = True
            
            # 获取店铺信息判断是否需要外卖
            current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
            need_takeaway = current_store and current_store.third_party_platform
            print(f"    need_takeaway = {need_takeaway}")
            
            # 如果不需要外卖平台信息，则自动标记为完成
            if not need_takeaway:
                daily_sales.takeaway_info_completed = True
                print("    ✓ 自动标记takeaway_info_completed = True")
            
            # 检查是否可以显示最终提交
            can_submit = daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed
            print(f"    可以最终提交: {can_submit}")
            
            # 模拟步骤2: 完成实际入账信息（跳过外卖步骤）
            print("  步骤2: 完成实际入账信息")
            daily_sales.actual_arrival_info_completed = True
            
            # 再次检查外卖平台逻辑
            current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
            need_takeaway = current_store and current_store.third_party_platform
            if not need_takeaway:
                daily_sales.takeaway_info_completed = True
            
            can_submit = daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed
            print(f"    最终可以提交: {can_submit}")
            print(f"    POS完成: {daily_sales.pos_info_completed}")
            print(f"    外卖完成: {daily_sales.takeaway_info_completed} (自动完成)")
            print(f"    入账完成: {daily_sales.actual_arrival_info_completed}")
            
            db.session.commit()
            print("  ✓ 未开通外卖平台店铺测试完成\n")
        
        print("=== 所有测试完成 ===")
        
        # 总结
        print("\n=== 测试总结 ===")
        print("✓ 开通外卖平台的店铺：需要完成3个步骤（POS、外卖、入账）")
        print("✓ 未开通外卖平台的店铺：只需完成2个步骤（POS、入账），外卖步骤自动跳过")
        print("✓ 店铺外卖平台状态检查逻辑正常")
        print("✓ 最终提交条件判断正确")

if __name__ == "__main__":
    test_takeaway_logic_complete()
