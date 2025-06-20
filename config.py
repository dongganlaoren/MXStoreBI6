# config.py
import os
from dotenv import load_dotenv

# 在文件顶部加载 .env，确保环境变量在类定义之前可用
load_dotenv()

class Config:
    """
    基础配置类，包含所有环境通用的配置。
    """
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # +++ 添加 ENV 属性 +++
    ENV = 'default'  # 默认环境

    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV') == 'production':
            raise ValueError("生产环境必须设置 SECRET_KEY 环境变量！")
        else:
            print("警告：SECRET_KEY 未通过环境变量设置，将使用开发默认值。请勿在生产中使用此默认值！")
            SECRET_KEY = 'dev_secret_key_do_not_use_in_prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    RECORDS_PER_PAGE = int(os.environ.get('RECORDS_PER_PAGE', 10))

class DevelopmentConfig(Config):
    """开发环境的特定配置"""
    DEBUG = True
    ENV = 'development'  #  开发环境
    SQLALCHEMY_ECHO = True
    #  开发时需要一个明确的SQLite后备
    if not Config.SQLALCHEMY_DATABASE_URI:
        print("开发环境警告：DATABASE_URL 未设置，将尝试使用默认的开发数据库。")
        SQLALCHEMY_DATABASE_URI =  'sqlite:///./dev_app.db'

class ProductionConfig(Config):
    """生产环境的特定配置"""
    DEBUG = False
    ENV = 'production' # 生产环境
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """测试环境特定配置"""
    TESTING = True
    DEBUG = True
    ENV = 'testing'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = os.environ.get('TEST_SECRET_KEY') or 'test_secret_key'

config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig,
    testing=TestingConfig,
    default=DevelopmentConfig
)