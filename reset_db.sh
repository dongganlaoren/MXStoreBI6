#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # 无色

step() {
    echo -e "${YELLOW}==== $1 ====${NC}"
}
success() {
    echo -e "${GREEN}$1${NC}"
}
fail() {
    echo -e "${RED}$1${NC}"
    exit 1
}

step "删除目录 migrations"
if [ -d migrations ]; then
    rm -rf migrations && success "已删除 migrations 目录。" || fail "删除 migrations 目录失败！"
else
    echo -e "${YELLOW}migrations 目录不存在，跳过。${NC}"
fi

step "删除目录 instance"
if [ -d instance ]; then
    rm -rf instance && success "已删除 instance 目录。" || fail "删除 instance 目录失败！"
else
    echo -e "${YELLOW}instance 目录不存在，跳过。${NC}"
fi

step "删除目录 app/static/uploads"
if [ -d app/static/uploads ]; then
    rm -rf app/static/uploads && success "已删除 app/static/uploads 目录。" || fail "删除 app/static/uploads 目录失败！"
else
    echo -e "${YELLOW}app/static/uploads 目录不存在，跳过。${NC}"
fi

step "初始化数据库迁移环境 (flask db init)"
flask db init && success "flask db init 成功。" || fail "flask db init 失败！"

step "生成迁移脚本 (flask db migrate)"
flask db migrate -m "init" && success "flask db migrate 成功。" || fail "flask db migrate 失败！"

step "应用迁移 (flask db upgrade)"
flask db upgrade && success "flask db upgrade 成功。" || fail "flask db upgrade 失败！"

success "全部操作完成！"
