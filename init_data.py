#!/usr/bin/env python3
# init_data.py - 初始化测试数据

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import DevelopmentConfig
from app.utils.fake_data import generate_fake_data

if __name__ == '__main__':
    app = create_app(DevelopmentConfig)
    with app.app_context():
        print("开始生成测试数据...")
        generate_fake_data()
        print("测试数据生成完毕！")
