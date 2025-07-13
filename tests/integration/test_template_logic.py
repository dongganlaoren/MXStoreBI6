#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接模拟模板渲染逻辑，验证外卖Tab显示问题
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

def simulate_template_logic():
    """模拟模板渲染逻辑"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        print("=== 直接模拟模板渲染逻辑 ===\n")
        
        # 获取开通外卖平台的店铺
        takeaway_store = Store.query.filter_by(third_party_platform=True).first()
        print(f"测试店铺: {takeaway_store.store_name}")
        print(f"店铺ID: {takeaway_store.store_id}")
        print(f"third_party_platform: {takeaway_store.third_party_platform}")
        
        # 获取或创建日报
        today = date.today()
        daily_sales = DailySales.query.filter_by(
            store_id=takeaway_store.store_id,
            report_date=today
        ).first()
        
        if daily_sales:
            print(f"\n日报信息:")
            print(f"  report_id: {daily_sales.report_id}")
            print(f"  pos_info_completed: {daily_sales.pos_info_completed}")
            print(f"  takeaway_info_completed: {daily_sales.takeaway_info_completed}")
            print(f"  actual_arrival_info_completed: {daily_sales.actual_arrival_info_completed}")
            print(f"  is_submitted: {daily_sales.is_submitted}")
        
        # 模拟视图逻辑
        print(f"\n=== 模拟视图逻辑 ===")
        current_store = Store.query.filter_by(store_id=takeaway_store.store_id).first()
        print(f"current_store 查询结果: {current_store.store_name if current_store else 'None'}")
        print(f"current_store.third_party_platform: {current_store.third_party_platform if current_store else 'N/A'}")
        
        # 模拟模板条件判断
        print(f"\n=== 模拟模板条件判断 ===")
        
        # 情况1: 已有数据的情况 (主要问题场景)
        print("1. 已有数据的情况:")
        if daily_sales:  # 相当于模板中的 {% else %} 分支
            print("   进入 '已有日报数据的情况' 分支")
            
            # 模拟修复后的模板逻辑
            show_takeaway = current_store and current_store.third_party_platform
            print(f"   show_takeaway = current_store and current_store.third_party_platform")
            print(f"   show_takeaway = {show_takeaway}")
            
            if show_takeaway:
                print("   ✅ 外卖平台Tab应该显示")
                
                # 检查Tab是否应该启用
                tab_enabled = daily_sales.pos_info_completed
                print(f"   外卖Tab启用状态: {tab_enabled}")
                
                # 检查最终提交条件
                need_takeaway = current_store and current_store.third_party_platform
                can_final_submit = (
                    daily_sales.pos_info_completed and 
                    daily_sales.actual_arrival_info_completed and 
                    not daily_sales.is_submitted and
                    (not need_takeaway or daily_sales.takeaway_info_completed)
                )
                print(f"   最终提交条件检查:")
                print(f"     - POS完成: {daily_sales.pos_info_completed}")
                print(f"     - 入账完成: {daily_sales.actual_arrival_info_completed}")
                print(f"     - 未提交: {not daily_sales.is_submitted}")
                print(f"     - 外卖条件满足: {not need_takeaway or daily_sales.takeaway_info_completed}")
                print(f"     → 可以最终提交: {can_final_submit}")
            else:
                print("   ❌ 外卖平台Tab不应该显示")
        
        # 情况2: 新建数据的情况
        print("\n2. 新建数据的情况:")
        print("   进入 '新建数据' 分支")
        show_takeaway_new = current_store and current_store.third_party_platform
        print(f"   show_takeaway = {show_takeaway_new}")
        
        if show_takeaway_new:
            print("   ✅ 外卖平台Tab应该显示")
        else:
            print("   ❌ 外卖平台Tab不应该显示")
        
        # 检查Jinja2模板语法
        print(f"\n=== Jinja2语法验证 ===")
        print("检查模板中的条件语句:")
        print("  {% set show_takeaway = current_store and current_store.third_party_platform %}")
        print("  {% if show_takeaway %}")
        print("模拟结果:")
        print(f"  current_store = {current_store is not None}")
        print(f"  current_store.third_party_platform = {current_store.third_party_platform if current_store else 'N/A'}")
        print(f"  结果 = {bool(current_store and current_store.third_party_platform)}")

if __name__ == "__main__":
    simulate_template_logic()
