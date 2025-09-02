#!/usr/bin/env python3
"""
项目测试验证脚本
用于验证损益报表功能和整体项目状态
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_basic_imports():
    """测试基本导入功能"""
    try:
        from app import create_app, db
        from app.models import User, Store, DailySales, ReimbursementRequest
        from app.models.enums import RoleType, FinancialCheckStatus, ReimbursementStatus
        print("✅ 基本导入测试通过")
        return True
    except Exception as e:
        print(f"❌ 基本导入测试失败: {e}")
        return False


def test_app_creation():
    """测试应用创建"""
    try:
        from app import create_app
        app = create_app()
        print("✅ 应用创建测试通过")
        return True
    except Exception as e:
        print(f"❌ 应用创建测试失败: {e}")
        return False


def test_profit_loss_route():
    """测试损益报表路由"""
    try:
        from app import create_app
        app = create_app()

        with app.app_context():
            # 检查路由是否注册
            routes = [str(rule) for rule in app.url_map.iter_rules()]
            profit_loss_routes = [r for r in routes if 'profit_loss' in r]

            if profit_loss_routes:
                print(f"✅ 损益报表路由已注册: {profit_loss_routes}")
                return True
            else:
                print("❌ 损益报表路由未找到")
                return False
    except Exception as e:
        print(f"❌ 损益报表路由测试失败: {e}")
        return False


def test_template_exists():
    """测试模板文件是否存在"""
    template_path = "app/templates/email_report/profit_loss_report.html"
    if os.path.exists(template_path):
        print("✅ 损益报表模板文件存在")
        return True
    else:
        print("❌ 损益报表模板文件不存在")
        return False


def main():
    """主测试函数"""
    print("=" * 50)
    print("🔍 开始项目状态验证")
    print("=" * 50)

    tests = [
        test_basic_imports,
        test_app_creation,
        test_profit_loss_route,
        test_template_exists
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有验证测试通过！项目状态良好！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
