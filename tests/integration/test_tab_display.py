#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板渲染测试：验证第三方外卖平台Tab显示问题
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
import config

def test_template_tab_display():
    """测试模板中Tab显示逻辑"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        print("=== 第三方外卖平台Tab显示测试 ===\n")
        
        # 获取开通外卖平台的店铺
        takeaway_store = Store.query.filter_by(third_party_platform=True).first()
        if not takeaway_store:
            print("❌ 找不到开通外卖平台的店铺")
            return
        
        print(f"测试店铺: {takeaway_store.store_name}")
        print(f"店铺ID: {takeaway_store.store_id}")
        print(f"第三方外卖平台: {takeaway_store.third_party_platform}")
        
        # 检查是否有今天的日报
        today = date.today()
        daily_sales = DailySales.query.filter_by(
            store_id=takeaway_store.store_id,
            report_date=today
        ).first()
        
        if daily_sales:
            print(f"\n找到日报记录 (ID: {daily_sales.report_id})")
            print(f"POS信息完成: {daily_sales.pos_info_completed}")
            print(f"外卖信息完成: {daily_sales.takeaway_info_completed}")
            print(f"入账信息完成: {daily_sales.actual_arrival_info_completed}")
            print(f"已提交: {daily_sales.is_submitted}")
            
            # 模拟模板逻辑
            print(f"\n=== 模拟模板逻辑 ===")
            current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
            print(f"current_store: {current_store.store_name if current_store else 'None'}")
            print(f"current_store.third_party_platform: {current_store.third_party_platform if current_store else 'N/A'}")
            
            # 模拟模板中的条件判断
            show_takeaway = False
            if current_store and current_store.third_party_platform:
                show_takeaway = True
            
            print(f"show_takeaway = current_store and current_store.third_party_platform = {show_takeaway}")
            
            # 判断外卖Tab是否应该显示
            if show_takeaway:
                print("✅ 外卖Tab应该显示")
                
                # 检查Tab是否应该启用
                tab_enabled = daily_sales.pos_info_completed
                print(f"外卖Tab启用状态: {tab_enabled} (依赖于POS信息完成)")
                
                # 检查最终提交条件
                need_takeaway = current_store and current_store.third_party_platform
                can_final_submit = (
                    daily_sales.pos_info_completed and 
                    daily_sales.actual_arrival_info_completed and 
                    not daily_sales.is_submitted and
                    (not need_takeaway or daily_sales.takeaway_info_completed)
                )
                print(f"可以最终提交: {can_final_submit}")
                print(f"  - POS完成: {daily_sales.pos_info_completed}")
                print(f"  - 入账完成: {daily_sales.actual_arrival_info_completed}")
                print(f"  - 未提交: {not daily_sales.is_submitted}")
                print(f"  - 外卖条件: {not need_takeaway or daily_sales.takeaway_info_completed}")
            else:
                print("❌ 外卖Tab不应该显示")
        else:
            print("\n未找到今天的日报记录")
            
            # 创建一个测试日报来模拟场景
            print("创建测试日报...")
            daily_sales = DailySales(
                user_id=1,
                store_id=takeaway_store.store_id,
                report_date=today,
                pos_info_completed=True,
                takeaway_info_completed=True,
                actual_arrival_info_completed=True
            )
            db.session.add(daily_sales)
            db.session.commit()
            
            print(f"测试日报创建成功 (ID: {daily_sales.report_id})")
            
            # 重新测试模板逻辑
            current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
            show_takeaway = current_store and current_store.third_party_platform
            print(f"show_takeaway = {show_takeaway}")
            
            if show_takeaway:
                print("✅ 测试日报：外卖Tab应该显示")
            else:
                print("❌ 测试日报：外卖Tab不应该显示")

if __name__ == "__main__":
    test_template_tab_display()
