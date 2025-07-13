#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证外卖平台Tab显示修复
"""
import os
import sys
import requests
import time
import threading
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ['FLASK_ENV'] = 'development'

from app import create_app
from app.extensions import db
from app.models.store import Store
from app.models.daily_sales import DailySales
import config

def run_test_server():
    """运行测试服务器"""
    app = create_app(config.DevelopmentConfig)
    app.run(debug=False, use_reloader=False, port=5001, host='127.0.0.1')

def test_takeaway_tab_display():
    """测试外卖平台Tab显示"""
    print("=== 验证外卖平台Tab显示修复 ===\n")
    
    # 启动测试服务器
    server_thread = threading.Thread(target=run_test_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(3)
    
    app = create_app(config.DevelopmentConfig)
    with app.app_context():
        # 获取开通外卖平台的店铺
        takeaway_store = Store.query.filter_by(third_party_platform=True).first()
        if not takeaway_store:
            print("❌ 找不到开通外卖平台的店铺")
            return
        
        print(f"测试店铺: {takeaway_store.store_name} (ID: {takeaway_store.store_id})")
        print(f"外卖平台状态: {takeaway_store.third_party_platform}")
        
        # 检查/创建测试日报
        today = date.today()
        daily_sales = DailySales.query.filter_by(
            store_id=takeaway_store.store_id,
            report_date=today
        ).first()
        
        if not daily_sales:
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
            print(f"创建测试日报 (ID: {daily_sales.report_id})")
        else:
            print(f"使用现有日报 (ID: {daily_sales.report_id})")
        
        print(f"POS完成: {daily_sales.pos_info_completed}")
        print(f"外卖完成: {daily_sales.takeaway_info_completed}")
        print(f"入账完成: {daily_sales.actual_arrival_info_completed}")
    
    # 测试Web界面
    try:
        # 构造查询URL
        url = f"http://127.0.0.1:5001/sales/report?store_id={takeaway_store.store_id}&report_date={today.strftime('%Y-%m-%d')}&initial_load=true"
        print(f"\n测试URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            
            # 检查关键元素是否存在
            checks = [
                ("店内营业信息Tab", "店内营业信息" in html_content),
                ("外卖平台Tab导航", 'id="takeaway-tab"' in html_content),
                ("外卖平台Tab内容", 'id="takeaway-content"' in html_content),
                ("实际入账Tab", "实际入账" in html_content),
                ("最终提交按钮", "最终提交所有信息" in html_content),
                ("外卖平台销售额字段", "takeaway_platform_sales" in html_content),
                ("外卖平台回执字段", "takeaway_platform_receipt" in html_content)
            ]
            
            print("\n=== HTML内容检查 ===")
            all_passed = True
            for check_name, result in checks:
                status = "✅ 存在" if result else "❌ 缺失"
                print(f"{check_name}: {status}")
                if not result:
                    all_passed = False
            
            if all_passed:
                print("\n🎉 所有检查通过！外卖平台Tab显示正常")
            else:
                print("\n⚠️  部分检查失败，可能仍有问题")
                
                # 输出部分HTML内容用于调试
                print("\n=== 部分HTML内容（用于调试）===")
                lines = html_content.split('\n')
                for i, line in enumerate(lines):
                    if 'takeaway' in line.lower() or 'tab' in line.lower():
                        print(f"第{i+1}行: {line.strip()}")
                        
        else:
            print(f"❌ 页面访问失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_takeaway_tab_display()
