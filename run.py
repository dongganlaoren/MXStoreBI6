# MXStoreBI/run.py

# Flask 应用的开发环境启动脚本。
import os

from app import create_app
from config import (
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)

# --- 选择并加载应用配置 ---
config_name = os.getenv('FLASK_ENV', 'development').lower()

if config_name == 'production':
    app = create_app(ProductionConfig)
    print("运行模式: 生产环境 (Production)")
elif config_name == 'testing':
    app = create_app(TestingConfig)
    print("运行模式: 测试环境 (Testing)")
elif config_name == 'development':
    app = create_app(DevelopmentConfig)
    print("运行模式: 开发环境 (Development)")
else:
    print(f"警告: 未知的 FLASK_ENV: '{config_name}'.  将使用开发环境配置作为默认配置。")
    app = create_app(DevelopmentConfig)
    print(f"运行模式: 开发环境 (Development) - 当前 config_name: '{config_name}'")


# --- 主程序入口 ---
if __name__ == '__main__':
    # 推荐：开发环境用127.0.0.1，局域网调试用0.0.0.0，避免Can't assign requested address
    app.run(host='127.0.0.1', port=5000, debug=True)
    print("Flask 应用已停止运行。")