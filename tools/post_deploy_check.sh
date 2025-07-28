#!/bin/bash
set -euo pipefail

# 统一部署后探测脚本

echo "🔎 [探测] 开始服务状态和关键端口检测..."

# 检查 Supervisor 进程是否运行
if pgrep -f "supervisord" >/dev/null; then
  echo "✅ Supervisor 进程正常"
else
  echo "❌ Supervisor 进程未运行"
  exit 1
fi

# 检查 gunicorn 是否监听本地8001端口
if ss -tulnp | grep -q '127.0.0.1:8001'; then
  echo "✅ Gunicorn 正常监听127.0.0.1:8001"
else
  echo "❌ Gunicorn 未监听127.0.0.1:8001"
  exit 1
fi

# 检查 Supervisor 管理的项目是否 RUNNING
SUPERVISOR_STATUS=$(sudo -n /usr/bin/supervisorctl status MXStoreBI6 | grep RUNNING || true)
if [[ -n "$SUPERVISOR_STATUS" ]]; then
  echo "✅ Supervisor 管理的项目 MXStoreBI6 运行中"
else
  echo "❌ Supervisor 项目 MXStoreBI6 未运行"
  exit 1
fi

# 可扩展：应用健康接口探测（示例）
# 例如使用 curl 请求应用本地健康接口，确认返回状态码200
if command -v curl >/dev/null 2>&1; then
  HEALTH_URL="http://127.0.0.1:8001/health"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 应用健康接口检测通过 ($HEALTH_URL)"
  else
    echo "❌ 应用健康接口检测失败，HTTP状态码: $HTTP_CODE"
    exit 1
  fi
else
  echo "⚠️ curl 命令不可用，跳过应用健康接口检测"
fi

echo "🎉 [探测] 全部检查通过，服务运行正常"
exit 0
