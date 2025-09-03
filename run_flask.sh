#!/bin/bash

# 自动激活虚拟环境并运行 Flask 应用
# 使用方法: ./run_flask.sh

PROJECT_DIR="/Users/renweimin/PycharmProjects/FlaskProject/Git/vscodeSpace/0902/MXStoreBI6"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_EXEC="$VENV_DIR/bin/python"
FLASK_APP="$PROJECT_DIR/run.py"

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "错误: 虚拟环境不存在: $VENV_DIR"
    echo "请先创建虚拟环境: python -m venv venv"
    exit 1
fi

# 检查 Python 可执行文件是否存在
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "错误: Python 可执行文件不存在: $PYTHON_EXEC"
    exit 1
fi

# 检查 Flask 应用文件是否存在
if [ ! -f "$FLASK_APP" ]; then
    echo "错误: Flask 应用文件不存在: $FLASK_APP"
    exit 1
fi

# 检查当前是否已经在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "虚拟环境未激活，正在激活..."
    source "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        echo "错误: 无法激活虚拟环境"
        exit 1
    fi
    echo "虚拟环境已激活: $VIRTUAL_ENV"
else
    echo "虚拟环境已激活: $VIRTUAL_ENV"
fi

# 切换到项目目录
cd "$PROJECT_DIR" || {
    echo "错误: 无法切换到项目目录: $PROJECT_DIR"
    exit 1
}

# 设置 Flask 环境变量
export FLASK_APP="$FLASK_APP"
export FLASK_ENV="development"
export FLASK_DEBUG="1"
export FLASK_RUN_PORT="5001"

echo "正在启动 Flask 应用..."
echo "项目目录: $PROJECT_DIR"
echo "Python 版本: $($PYTHON_EXEC --version)"
echo "Flask 应用: $FLASK_APP"
echo ""
echo "按 Ctrl+C 停止应用"
echo "========================================"

# 运行 Flask 应用
$PYTHON_EXEC run.py
