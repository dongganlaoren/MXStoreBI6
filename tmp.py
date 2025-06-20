# run.py
# Flask 应用的开发环境启动脚本。

# 导入 os 模块，用于访问环境变量。
import os

# 从 'app' 包 (app/__init__.py) 中导入 create_app 应用工厂函数。
from app import create_app

# 从 config.py 文件导入不同环境的配置类。
from config import (  # 导入 TestingConfig，方便使用
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)

# --- 选择并加载应用配置 ---
# 从环境变量 'FLASK_ENV' 中获取配置名称。
# 如果环境变量未设置，则默认为 'development' (开发环境)。
config_name = os.getenv('FLASK_ENV', 'development').lower()  # 转为小写以统一比较

# 根据配置名称选择相应的配置类来创建 Flask 应用实例。
if config_name == 'production':
    app = create_app(ProductionConfig)  # 使用生产配置
    print("运行模式: 生产环境 (Production)")
elif config_name == 'testing':
    app = create_app(TestingConfig)  # 使用测试配置
    print("运行模式: 测试环境 (Testing)")
elif config_name == 'development':
    app = create_app(DevelopmentConfig)  # 使用开发配置
    print("运行模式: 开发环境 (Development)")
else:  # 默认为开发环境，处理未知的配置名称
    print(f"警告: 未知的 FLASK_ENV: '{config_name}'.  将使用开发环境配置作为默认配置。")
    app = create_app(DevelopmentConfig)  # 使用开发配置
    print(f"运行模式: 开发环境 (Development) - 当前 config_name: '{config_name}'")


# --- 主程序入口 ---
# 仅当直接运行此脚本时 (python run.py) 才执行以下代码。
if __name__ == '__main__':
    # 启动 Flask 内置的开发服务器。
    # host='0.0.0.0' 使服务器在所有网络接口上监听，允许局域网访问，方便局域网调试。
    # port=5000 指定监听端口。
    # debug 模式由加载的配置类中的 DEBUG 属性控制 (例如 DevelopmentConfig.DEBUG = True)。
    # **注意：此开发服务器不应用于生产环境！**
    app.run(host='0.0.0.0', port=5000)
    # 当服务器停止后 (例如按 Ctrl+C)，可以执行一些清理操作 (如果需要)。
    print("Flask 应用已停止运行。")