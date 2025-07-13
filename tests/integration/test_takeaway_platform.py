#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三方外卖平台功能综合测试
包含数据库逻辑、店铺配置、Web界面等全方位测试
"""
import os
import sys
import requests
from datetime import date

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['FLASK_ENV'] = 'development'

from app import create_app
from app.extensions import db
from app.models.store import Store
from app.models.user import User
from app.models.daily_sales import DailySales
import config

def test_third_party_platform_logic():
    """测试第三方外卖平台逻辑"""
    try:
        app = create_app(config.DevelopmentConfig)
        
        with app.app_context():
            print("=== 第三方外卖平台功能测试 ===")
            
            # 1. 检查店铺配置
            stores = Store.query.all()
            print(f"\n1. 店铺配置检查:")
            for store in stores:
                print(f"   - {store.store_name} (ID: {store.store_id})")
                print(f"     第三方外卖平台: {'✓ 已开通' if store.third_party_platform else '✗ 未开通'}")
            
            # 2. 测试店铺查询逻辑
            print(f"\n2. 店铺查询逻辑测试:")
            
            # 找一个开通外卖平台的店铺
            takeaway_store = Store.query.filter_by(third_party_platform=True).first()
            if takeaway_store:
                print(f"   开通外卖平台的店铺: {takeaway_store.store_name}")
                print(f"   store.third_party_platform = {takeaway_store.third_party_platform}")
            
            # 找一个未开通外卖平台的店铺
            no_takeaway_store = Store.query.filter_by(third_party_platform=False).first()
            if no_takeaway_store:
                print(f"   未开通外卖平台的店铺: {no_takeaway_store.store_name}")
                print(f"   store.third_party_platform = {no_takeaway_store.third_party_platform}")
            
            # 3. 测试日报创建逻辑
            print(f"\n3. 日报创建逻辑测试:")
            
            # 创建测试日报（如果不存在）
            test_date = date.today()
            
            if takeaway_store:
                existing_report = DailySales.query.filter_by(
                    store_id=takeaway_store.store_id,
                    report_date=test_date
                ).first()
                
                if not existing_report:
                    print(f"   为开通外卖的店铺创建测试日报...")
                    test_report = DailySales(
                        user_id=1,  # 假设有用户ID为1的用户
                        store_id=takeaway_store.store_id,
                        report_date=test_date,
                        pos_info_completed=True,
                        takeaway_info_completed=False,  # 模拟需要填写外卖信息
                        actual_arrival_info_completed=False
                    )
                    db.session.add(test_report)
                    db.session.commit()
                    print(f"   ✓ 测试日报创建成功 (report_id: {test_report.report_id})")
                else:
                    print(f"   已存在测试日报 (report_id: {existing_report.report_id})")
            
            # 4. 验证店铺对象查询
            print(f"\n4. 店铺对象查询验证:")
            test_store_id = takeaway_store.store_id if takeaway_store else stores[0].store_id
            
            # 模拟视图中的查询逻辑
            current_store = Store.query.filter_by(store_id=test_store_id).first()
            if current_store:
                print(f"   查询店铺: {current_store.store_name}")
                print(f"   third_party_platform: {current_store.third_party_platform}")
                print(f"   need_takeaway = current_store and current_store.third_party_platform")
                need_takeaway = current_store and current_store.third_party_platform
                print(f"   need_takeaway = {need_takeaway}")
            
            print(f"\n=== 测试完成 ===")
            
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

def test_web_interface():
    """测试Web界面"""
    print(f"\n=== Web界面测试 ===")
    
    try:
        # 测试首页是否可访问
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"首页访问: {'✓ 成功' if response.status_code in [200, 302] else '✗ 失败'} (状态码: {response.status_code})")
        
        # 测试营业额上报页面
        response = requests.get('http://127.0.0.1:5000/sales/report?initial_load=true', timeout=5)
        print(f"营业额上报页面: {'✓ 可访问' if response.status_code in [200, 302] else '✗ 无法访问'} (状态码: {response.status_code})")
        
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到Flask应用，请确保应用正在运行")
    except Exception as e:
        print(f"Web界面测试出错: {e}")

if __name__ == "__main__":
    test_third_party_platform_logic()
    test_web_interface()
