#!/bin/bash
# 一键清理、重建数据库并初始化迁移脚本
# 使用前请确保已激活虚拟环境，并有MySQL root权限

set -e

echo "==============================="
echo "MXStoreBI6 数据库重建与迁移初始化脚本"
echo "本操作将删除所��历史数据并重建表结构，请谨慎操作！"
echo "==============================="
read -p "按回车键继续，或 Ctrl+C 取消..."

# 1. 清空并重建数据库（危险操作，确保无重要数据！）
echo "\n[1/5] 正在重建数据库 MXStoreBI_Production..."
sudo mysql -u root -p <<EOF
DROP DATABASE IF EXISTS MXStoreBI_Production;
CREATE DATABASE MXStoreBI_Production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON MXStoreBI_Production.* TO 'mixuebi_user'@'localhost';
FLUSH PRIVILEGES;
EOF
echo "数据库 MXStoreBI_Production 已重建。"

# 2. 删除旧迁移文件夹
if [ -d "migrations" ]; then
    echo "[2/5] 删除旧的 migrations 文件夹..."
    rm -rf migrations
    echo "migrations 文件夹已删除。"
else
    echo "[2/5] 未检测到 migrations 文件夹，无需删除。"
fi

# 3. 清理 pycache、日志、README.MD 和 docs

# 删除 __pycache__ 目录
find . -type d -name "__pycache__" -exec rm -rf {} +
# 删除日志文件
rm -f app.log app.log.1 app.log.2 app.log.3
# 删除 README.MD
rm -f README.MD
# 删除 docs 文件夹
rm -rf docs

echo "[3/5] 缓存、日志、README.MD 和 docs 已清理。"

# 4. 重新初始化迁移环境
echo "[4/5] 初始化 Flask-Migrate..."
source venv/bin/activate
flask db init || true
flask db migrate -m "init"
flask db upgrade
echo "数据库迁移已完成。"

echo "==============================="
echo "所有操作已完成！请检查输出确认无异常。"
echo "==============================="
