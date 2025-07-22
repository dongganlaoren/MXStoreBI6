#!/bin/bash
# 一键清理、重建数据库并初始化迁移脚本
# 使用前请确保已激活虚拟环境，并有MySQL权限

set -e

# 1. 用 Python 脚本重建数据库（自动读取 .env 并连接 MySQL）
echo "==============================="
echo "[1/5] 正在重建数据库（自动读取 .env 配置）..."
python reset_db.py
if [ $? -ne 0 ]; then
    echo "数据库重建失败，请检查 .env 配置和 reset_db.py 脚本。"
    exit 1
fi
echo "数据库已重建。"

# 2. 删除旧迁移文件夹
if [ -d "migrations" ]; then
    echo "[2/5] 删除旧的 migrations 文件夹..."
    rm -rf migrations
    echo "migrations 文件夹已删除。"
else
    echo "[2/5] 未检测到 migrations 文件夹，无需删除。"
fi

# 3. 清理 pycache、日志
# 删除 __pycache__ 目录
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
# 删除日志文件
rm -f app.log app.log.1 app.log.2 app.log.3

echo "[3/5] 缓存和日志已清理。"

# 4. 重新初始化迁移环境
echo "[4/5] 初始化 Flask-Migrate..."
# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "警告: 未检测到虚拟环境，请手动激活虚拟环境后再运行此脚本"
        exit 1
    fi
fi

flask db init || true
flask db migrate -m "init"
flask db upgrade
echo "数据库迁移已完成。"

# 5. 自动生成基础数据（门店、用户等）
echo "[5/5] 生成基础测试数据..."
python -c "from app import create_app; from config import DevelopmentConfig; app = create_app(DevelopmentConfig); from app.utils.fake_data import generate_fake_data; ctx = app.app_context(); ctx.push(); generate_fake_data(); ctx.pop()" || echo "基础数据生成失败，可能需要手动创建"
echo "基础数据已生成。"

echo "==============================="
echo "所有操作已完成！请检查输出确认无异常。"
echo "==============================="
