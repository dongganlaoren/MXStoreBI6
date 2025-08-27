#!/bin/bash
# MXStoreBI6 快速回滚脚本
# 功能：恢复到最近一次部署前的数据库和代码备份
# 使用：sudo bash rollback_MXStoreBI6.sh

set -euo pipefail

PROJECT_NAME="MXStoreBI6"
DEPLOY_PATH="/var/www/$PROJECT_NAME"

DB_BACKUP_DIR="/var/backups/db/$PROJECT_NAME"
CODE_BACKUP_DIR="/var/backups/$PROJECT_NAME"

DB_USER="${DB_USER:-${DB_USER_FALLBACK:-root}}"   # 可从环境变量注入
DB_PASSWORD="${DB_PASSWORD:-${DB_PASSWORD_FALLBACK:-password}}"
DB_NAME="${DB_NAME:-${DB_NAME_FALLBACK:-mxstorebi6}}"

echo "🚨 [警告] 即将回滚 MXStoreBI6，操作会覆盖当前代码和数据库"
read -p "是否继续？(yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ 操作已取消"
    exit 1
fi

echo "🔎 [步骤1] 查找最新的数据库备份"
LATEST_DB_BACKUP=$(ls -1t "$DB_BACKUP_DIR"/backup_*.sql | head -n 1)
if [ -z "$LATEST_DB_BACKUP" ]; then
    echo "❌ 未找到数据库备份文件"
    exit 1
fi
echo "✅ 选中数据库备份: $LATEST_DB_BACKUP"

echo "🗑️ [步骤2] 清空数据库 $DB_NAME"
mysql -u"$DB_USER" -p"$DB_PASSWORD" -e "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "📥 [步骤3] 恢复数据库数据"
mysql -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$LATEST_DB_BACKUP"
echo "✅ 数据库已恢复"

echo "🔎 [步骤4] 查找最新的代码备份"
LATEST_CODE_BACKUP=$(ls -1t "$CODE_BACKUP_DIR"/backup_*.tar.gz | head -n 1)
if [ -z "$LATEST_CODE_BACKUP" ]; then
    echo "❌ 未找到代码备份文件"
    exit 1
fi
echo "✅ 选中代码备份: $LATEST_CODE_BACKUP"

echo "📂 [步骤5] 还原代码目录: $DEPLOY_PATH"
cd "$DEPLOY_PATH"
sudo tar xzf "$LATEST_CODE_BACKUP" -C "$DEPLOY_PATH" --strip-components=0
echo "✅ 代码已恢复"

echo "🌀 [步骤6] 重启 Supervisor 项目"
sudo supervisorctl restart "${PROJECT_NAME}"
sudo supervisorctl restart "${PROJECT_NAME}_celery"
echo "✅ 服务已重启"

echo "🎉 [完成] 回滚操作成功"
