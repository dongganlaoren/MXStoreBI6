# app/__init__.py
import logging
import re
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import config_by_name
from flask import Flask, render_template
from flask_login import LoginManager
from markupsafe import Markup, escape

from app import commands, utils
from app.extensions import csrf, db, login_manager, migrate  # 导入扩展


def nl2br_filter(value: Optional[str]) -> Markup:
    """将文本中的换行符转换为HTML的<br>标签"""
    if value is None:
        return Markup("")
    escaped = escape(str(value))
    return Markup(re.sub(r"(\r\n|\r|\n)", "<br>\n", escaped))


def handle_app_error(app: Flask, error: Exception, code: int) -> tuple:
    """统一处理应用错误（带日志记录）"""
    app.logger.error(f"错误 {code}: {error}", exc_info=True)
    return render_template(f"errors/{code}.html", error=str(error)), code


def create_app(config: object) -> Flask:
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config)

    # 配置日志
    configure_logging(app)

    # 初始化扩展
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    # 注册初始化插入测试数据的命令
    commands.init_app(app)
    # 配置用户登录
    login_manager.init_app(app)
    login_manager.login_view = "user.login"

    # 注册Jinja2过滤器
    app.jinja_env.filters["nl2br"] = nl2br_filter

    # 路由配置
    app.url_map.strict_slashes = False

    # 生产环境校验
    validate_production_config(app)

    # 在应用上下文中进行数据库操作和蓝图注册
    with app.app_context():
        # utils.fake_data.generate_fake_data() #初始化数据
        register_blueprints(app)
        # initialize_default_user(app)#创建admin

    @login_manager.user_loader
    def load_user(user_id: int) -> Optional["User"]:
        from app.models import User  # 本地导入解决循环引用
        return User.query.get(user_id)

    return app


def configure_logging(app: Flask):
    """配置日志系统"""
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def validate_production_config(app: Flask):
    """验证生产环境配置"""
    REQUIRED_KEYS = ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI"]
    if app.config['ENV'] == "production":
        for key in REQUIRED_KEYS:
            if not app.config.get(key):
                app.logger.error(f"生产环境必须配置 {key}")
                raise ValueError(f"生产环境必须配置 {key}")


def register_blueprints(app: Flask):
    """注册所有蓝图"""
    from app.views.main_views import main_bp
    from app.views.root_views import root_bp

    # from app.views.sales_views import sales_bp
    # from app.views.store_views import store_bp
    from app.views.user_views import user_bp

    # app.register_blueprint(store_bp, url_prefix="/store")
    app.register_blueprint(root_bp)
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(main_bp, url_prefix="/main")
    # app.register_blueprint(sales_bp, url_prefix="/sales")


def initialize_default_user(app: Flask):
    """初始化默认用户"""
    from werkzeug.security import generate_password_hash

    from app.models import User

    default_username = app.config.get("DEFAULT_ADMIN_USERNAME", "admin")
    default_password = app.config.get("DEFAULT_ADMIN_PASSWORD", "admin")

    if not User.query.filter_by(username=default_username).first():
        app.logger.info(f"正在创建默认用户: {default_username}")
        hashed_password = generate_password_hash(default_password)
        admin_user = User(username=default_username, password_hash=hashed_password, user_status=1)
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info(f"创建默认用户成功: {default_username}")