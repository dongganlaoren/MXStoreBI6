#!/bin/bash
set -euo pipefail

echo "[检测] 检查 Gunicorn 是否监听端口 8001..."
ss -tulnp | grep -q ':8001' && echo "✅ Gunicorn 正在监听 8001" || {
  echo "❌ Gunicorn 未监听 8001"; exit 1;
}

echo "[检测] 检查本地接口是否正常响应..."
curl -sSf http://127.0.0.1:8001/ > /dev/null && echo "✅ 本地接口访问正常" || {
  echo "❌ 本地接口访问失败"; exit 1;
}

echo "[检测] 检查公网访问 https://www.gothaieasy.fun/"
curl -sSf https://www.gothaieasy.fun/ > /dev/null && echo "✅ 公网访问正常" || {
  echo "❌ 公网访问失败"; exit 1;
}
