#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
店铺第三方外卖平台配置测试
验证店铺模型中的third_party_platform字段功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.extensions import db
from app.models.store import Store
import config

def test_store_third_party_platform():
    """测试店铺第三方外卖平台设置"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        print("=== 店铺第三方外卖平台配置测试 ===\n")
        
        # 查询现有店铺
        stores = Store.query.all()
        print("1. 当前店铺信息检查")
        print("-" * 40)
        
        if not stores:
            print("❌ 没有找到任何店铺数据")
            return
        
        # 统计店铺配置
        total_stores = len(stores)
        takeaway_enabled = Store.query.filter_by(third_party_platform=True).count()
        takeaway_disabled = Store.query.filter_by(third_party_platform=False).count()
        
        print(f"总店铺数: {total_stores}")
        print(f"开通外卖平台: {takeaway_enabled} 家")
        print(f"未开通外卖平台: {takeaway_disabled} 家")
        print()
        
        # 显示详细店铺信息
        print("2. 详细店铺配置")
        print("-" * 40)
        for store in stores:
            platform_status = "✅ 已开通" if store.third_party_platform else "❌ 未开通"
            print(f"• {store.store_name} (ID: {store.store_id})")
            print(f"  地址: {store.store_address}")
            print(f"  第三方外卖平台: {platform_status}")
            print()
        
        # 验证查询功能
        print("3. 查询功能验证")
        print("-" * 40)
        
        # 测试筛选开通外卖平台的店铺
        takeaway_stores = Store.query.filter_by(third_party_platform=True).all()
        print(f"通过查询获取开通外卖平台的店铺: {len(takeaway_stores)} 家")
        for store in takeaway_stores:
            print(f"  - {store.store_name}")
        
        # 测试筛选未开通外卖平台的店铺
        no_takeaway_stores = Store.query.filter_by(third_party_platform=False).all()
        print(f"\n通过查询获取未开通外卖平台的店铺: {len(no_takeaway_stores)} 家")
        for store in no_takeaway_stores:
            print(f"  - {store.store_name}")
        
        # 验证模型属性
        print("\n4. 模型属性验证")
        print("-" * 40)
        test_store = stores[0]
        print(f"测试店铺: {test_store.store_name}")
        print(f"third_party_platform 类型: {type(test_store.third_party_platform)}")
        print(f"third_party_platform 值: {test_store.third_party_platform}")
        print(f"布尔判断结果: {bool(test_store.third_party_platform)}")
        
        # 测试条件判断逻辑
        print("\n5. 条件判断逻辑测试")
        print("-" * 40)
        for store in stores[:2]:  # 只测试前两个店铺
            need_takeaway = store and store.third_party_platform
            print(f"店铺: {store.store_name}")
            print(f"  store.third_party_platform = {store.third_party_platform}")
            print(f"  need_takeaway = store and store.third_party_platform = {need_takeaway}")
            print(f"  应该显示外卖Tab: {'是' if need_takeaway else '否'}")
            print()
        
        print("✅ 店铺第三方外卖平台配置测试完成")

def create_test_stores_if_needed():
    """如果没有店铺数据，创建测试店铺"""
    app = create_app(config.DevelopmentConfig)
    
    with app.app_context():
        stores = Store.query.all()
        
        if not stores:
            print("=== 创建测试店铺数据 ===")
            
            # 创建测试店铺
            test_stores = [
                Store(
                    store_id="TEST001",
                    store_name="测试店铺(有外卖)",
                    store_address="测试地址1",
                    third_party_platform=True
                ),
                Store(
                    store_id="TEST002", 
                    store_name="测试店铺(无外卖)",
                    store_address="测试地址2",
                    third_party_platform=False
                ),
                Store(
                    store_id="TEST003",
                    store_name="测试店铺2(有外卖)",
                    store_address="测试地址3",
                    third_party_platform=True
                )
            ]
            
            for store in test_stores:
                db.session.add(store)
            
            db.session.commit()
            print("✅ 测试店铺创建成功！")
            
            # 显示创建的店铺
            for store in test_stores:
                platform_status = "开通" if store.third_party_platform else "未开通"
                print(f"• {store.store_name} - {platform_status}外卖平台")

if __name__ == "__main__":
    # 先检查是否需要创建测试数据
    create_test_stores_if_needed()
    
    # 运行测试
    test_store_third_party_platform()
