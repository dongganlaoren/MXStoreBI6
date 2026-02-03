#!/bin/zsh

# 项目根目录
PROJECT_DIR="/Users/renweimin/PycharmProjects/FlaskProject/Git/0723007"
cd "$PROJECT_DIR"

echo "=========================================="
echo "MXStoreBI Flask 项目 Pytest 测试执行"
echo "=========================================="
echo ""
echo "执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "项目目录: $PROJECT_DIR"
echo ""

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "✓ 虚拟环境已检测到"
    source .venv/bin/activate
    echo "✓ 虚拟环境已激活"
else
    echo "⚠ 虚拟环境未找到，尝试使用全局 Python"
fi

echo ""
echo "=========================================="
echo "依赖检查"
echo "=========================================="

# 检查关键依赖
echo "检查 pytest..."
python -c "import pytest; print(f'✓ pytest 版本: {pytest.__version__}')" 2>/dev/null || echo "⚠ pytest 未安装"

echo "检查 pytest-cov..."
python -c "import pytest_cov; print('✓ pytest-cov 已安装')" 2>/dev/null || echo "⚠ pytest-cov 未安装"

echo "检查 Flask..."
python -c "import flask; print(f'✓ Flask 版本: {flask.__version__}')" 2>/dev/null || echo "⚠ Flask 未安装"

echo ""
echo "=========================================="
echo "环境配置检查"
echo "=========================================="

if [ -f ".env" ]; then
    echo "✓ .env 文件已存在"
    echo "  - FLASK_ENV: $(grep FLASK_ENV .env | cut -d'=' -f2)"
    echo "  - DATABASE_URL 已配置: $(grep -q 'DATABASE_URL=' .env && echo '是' || echo '否')"
    echo "  - SECRET_KEY 已配置: $(grep -q 'SECRET_KEY=' .env && echo '是' || echo '否')"
else
    echo "⚠ .env 文件未找到"
fi

echo ""
echo "=========================================="
echo "运行 Pytest 测试（含覆盖率报告）"
echo "=========================================="
echo ""

# 运行 pytest，生成多种格式的报告
python -m pytest \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=json \
    --tb=short \
    -v \
    tests/ \
    2>&1 | tee test_execution.log

TEST_RESULT=$?

echo ""
echo "=========================================="
echo "测试执行完成"
echo "=========================================="
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ 所有测试已通过"
else
    echo "✗ 部分测试失败，退出码: $TEST_RESULT"
fi

echo ""
echo "生成的报告:"
echo "  - 终端输出: 详见上方"
echo "  - HTML 覆盖率报告: htmlcov/index.html"
echo "  - JSON 覆盖率报告: .coverage.json"
echo "  - 执行日志: test_execution.log"
echo ""

exit $TEST_RESULT
