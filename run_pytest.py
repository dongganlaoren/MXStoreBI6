#!/usr/bin/env python
"""
执行 Flask 项目的 pytest 测试并生成详细报告
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 设置项目目录
PROJECT_DIR = "/Users/renweimin/PycharmProjects/FlaskProject/Git/0723007"
os.chdir(PROJECT_DIR)

# 确保项目目录在 sys.path 中
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

print("=" * 60)
print("MXStoreBI Flask 项目 - Pytest 测试执行报告")
print("=" * 60)
print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"项目目录: {PROJECT_DIR}")
print(f"Python 版本: {sys.version}")
print("=" * 60)
print()

# 验证虚拟环境
print("✓ 虚拟环境检查")
venv_path = Path(PROJECT_DIR) / ".venv"
if venv_path.exists():
    print(f"  虚拟环境路径: {venv_path}")
    print(f"  虚拟环境激活状态: {sys.prefix}")
else:
    print("  ⚠ 虚拟环境未找到，使用系统 Python")

print()

# 检查依赖
print("✓ 依赖检查")
try:
    import pytest
    print(f"  pytest 版本: {pytest.__version__}")
except ImportError:
    print("  ⚠ pytest 未安装")
    sys.exit(1)

try:
    import pytest_cov
    print(f"  pytest-cov: 已安装")
except ImportError:
    print("  ⚠ pytest-cov 未安装")

try:
    import flask
    print(f"  Flask 版本: {flask.__version__}")
except ImportError:
    print("  ⚠ Flask 未安装")

print()

# 检查 .env 文件
print("✓ 环境配置检查")
env_file = Path(PROJECT_DIR) / ".env"
if env_file.exists():
    print(f"  .env 文件: 存在")
    with open(env_file) as f:
        for line in f:
            if "FLASK_ENV=" in line:
                print(f"  FLASK_ENV: {line.strip()}")
            elif "DATABASE_URL=" in line:
                print(f"  DATABASE_URL: 已配置")
else:
    print("  ⚠ .env 文件未找到")

print()
print("=" * 60)
print("执行 Pytest 测试")
print("=" * 60)
print()

# 构建 pytest 命令
pytest_cmd = [
    sys.executable, "-m", "pytest",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--tb=short",
    "-v",
    "tests/"
]

print(f"执行命令: {' '.join(pytest_cmd)}")
print()

# 执行测试
result = subprocess.run(pytest_cmd, capture_output=False, text=True)

print()
print("=" * 60)
print("测试执行完成")
print("=" * 60)
print()

if result.returncode == 0:
    print("✓ 所有测试已通过")
else:
    print(f"✗ 部分测试失败 (退出码: {result.returncode})")

print()
print("生成的报告:")
print("  - HTML 覆盖率报告: htmlcov/index.html")
print("  - 覆盖率数据文件: .coverage")
print()

sys.exit(result.returncode)
