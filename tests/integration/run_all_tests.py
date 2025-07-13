#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的测试套件运行器
按顺序执行所有测试，提供完整的测试报告
"""
import os
import sys
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_test_suite():
    """运行完整的测试套件"""
    print("=" * 60)
    print("🧪 第三方外卖平台功能 - 完整测试套件")
    print("=" * 60)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    
    # 测试1: 基础功能测试
    print("🔍 测试1: 基础功能测试")
    print("-" * 30)
    try:
        from .test_takeaway_platform import test_third_party_platform_logic
        test_third_party_platform_logic()
        test_results.append(("基础功能测试", "✅ 通过"))
        print("✅ 基础功能测试通过\n")
    except Exception as e:
        test_results.append(("基础功能测试", f"❌ 失败: {str(e)}"))
        print(f"❌ 基础功能测试失败: {e}\n")
    
    # 测试2: 业务流程测试
    print("🔄 测试2: 业务流程测试")
    print("-" * 30)
    try:
        from .test_business_flow import test_takeaway_logic_complete
        test_takeaway_logic_complete()
        test_results.append(("业务流程测试", "✅ 通过"))
        print("✅ 业务流程测试通过\n")
    except Exception as e:
        test_results.append(("业务流程测试", f"❌ 失败: {str(e)}"))
        print(f"❌ 业务流程测试失败: {e}\n")
    
    # 测试3: Web界面测试
    print("🌐 测试3: Web界面测试")
    print("-" * 30)
    try:
        from .test_web_interface import test_web_interface
        test_web_interface()
        test_results.append(("Web界面测试", "✅ 通过"))
        print("✅ Web界面测试通过\n")
    except Exception as e:
        test_results.append(("Web界面测试", f"❌ 失败: {str(e)}"))
        print(f"❌ Web界面测试失败: {e}\n")
    
    # 测试4: 店铺平台配置测试
    print("🏪 测试4: 店铺平台配置测试")
    print("-" * 30)
    try:
        from .test_store_platform import test_store_third_party_platform
        test_store_third_party_platform()
        test_results.append(("店铺配置测试", "✅ 通过"))
        print("✅ 店铺配置测试通过\n")
    except Exception as e:
        test_results.append(("店铺配置测试", f"❌ 失败: {str(e)}"))
        print(f"❌ 店铺配置测试失败: {e}\n")
    
    # 生成测试报告
    print("=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        print(f"{test_name:<20} {result}")
        if "✅ 通过" in result:
            passed_tests += 1
    
    print("-" * 60)
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
    
    print(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！系统准备就绪！")
        return True
    else:
        print(f"\n⚠️  有 {total_tests - passed_tests} 个测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)
