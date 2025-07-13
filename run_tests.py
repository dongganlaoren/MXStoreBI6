#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三方外卖平台功能测试套件主入口
提供便捷的测试执行和管理功能
"""
import os
import sys
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='第三方外卖平台功能测试套件')
    parser.add_argument('action', choices=['all', 'basic', 'flow', 'web', 'store', 'unit', 'data-create', 'data-clean'], 
                       help='要执行的测试动作')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    print("=" * 60)
    print("🧪 蜜雪BI第三方外卖平台功能测试套件")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"执行动作: {args.action}")
    print()
    
    try:
        if args.action == 'all':
            print("🚀 执行完整测试套件...")
            from tests.integration.run_all_tests import run_test_suite
            success = run_test_suite()
            return 0 if success else 1
            
        elif args.action == 'basic':
            print("🔍 执行基础功能测试...")
            from tests.integration.test_takeaway_platform import test_third_party_platform_logic, test_web_interface
            test_third_party_platform_logic()
            test_web_interface()
            print("✅ 基础功能测试完成")
            
        elif args.action == 'flow':
            print("🔄 执行业务流程测试...")
            from tests.integration.test_business_flow import test_takeaway_logic_complete
            test_takeaway_logic_complete()
            print("✅ 业务流程测试完成")
            
        elif args.action == 'web':
            print("🌐 执行Web界面测试...")
            from tests.integration.test_web_interface import test_web_interface
            test_web_interface()
            print("✅ Web界面测试完成")
            
        elif args.action == 'store':
            print("🏪 执行店铺配置测试...")
            from tests.integration.test_store_platform import test_store_third_party_platform
            test_store_third_party_platform()
            print("✅ 店铺配置测试完成")
            
        elif args.action == 'unit':
            print("🧪 执行单元测试...")
            import subprocess
            result = subprocess.run(['python', '-m', 'pytest', 'tests/test_user_admin.py', '-v'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("错误信息:", result.stderr)
            return result.returncode
            
        elif args.action == 'data-create':
            print("📝 创建测试数据...")
            from tests.integration.test_data_generator import create_test_data
            create_test_data()
            
        elif args.action == 'data-clean':
            print("🧹 清理测试数据...")
            from tests.integration.test_data_generator import clean_test_data
            clean_test_data()
            
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
