# app/__init__.py

import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

from flask import Flask, render_template
from markupsafe import Markup, escape

from app import commands
from app.extensions import csrf, db, login_manager, migrate

# -------------------- Jinja2 过滤器 --------------------
def nl2br_filter(value: Optional[str]) -> Markup:
    """将换行符转换为 <br>，用于模板安全换行显示"""
    if value is None:
        return Markup("")
    escaped = escape(str(value))
    return Markup(re.sub(r"(\r\n|\r|\n)", "<br>\n", escaped))

def date_filter(value, fmt="%Y"):
    """自定义Jinja2日期格式化过滤器，支持 'now' 字符串、datetime对象、ISO日期字符串"""
    if value == "now":
        dt = datetime.utcnow()
    elif hasattr(value, "strftime"):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value))
        except Exception:
            return value
    return dt.strftime(fmt)

def strftime_filter(value, format='%Y-%m-%d %H:%M:%S'):
    """Jinja2 filter to format datetime objects using strftime."""
    if isinstance(value, datetime):
        return value.strftime(format)
    return value  # 如果不是 datetime 对象，则原样返回

# -------------------- Flask 应用工厂 --------------------
def create_app(config: object) -> Flask:
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config)

    # 初始化扩展
    configure_logging(app)
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    commands.init_app(app)
    login_manager.login_view = "user.login"
    app.url_map.strict_slashes = False
    validate_production_config(app)

    # 注册自定义 Jinja2 过滤器
    app.jinja_env.filters["date"] = date_filter
    app.jinja_env.filters["nl2br"] = nl2br_filter
    app.jinja_env.filters["strftime"] = strftime_filter # 注册 strftime 过滤器

    # 注入当前时间到模板
    @app.context_processor
    def inject_now():
        """
        向所有模板注入 'now' 变量，其值为当前UTC时间。
        用法：{{ now.year }}
        """
        return {'now': datetime.utcnow()}

    # 注册蓝图
    with app.app_context():
        register_blueprints(app)

    # 用户加载回调
    @login_manager.user_loader
    def load_user(user_id: int) -> Optional["User"]:
        from app.models import User  # 本地导入解决循环引用
        return User.query.get(user_id)

    return app

# -------------------- 日志配置 --------------------
def configure_logging(app: Flask):
    """配置日志文件滚动"""
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

# -------------------- 生产环境配置校验 --------------------
def validate_production_config(app: Flask):
    """生产环境下必须配置的关键参数校验"""
    REQUIRED_KEYS = ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI"]
    if app.config.get('ENV') == "production":
        for key in REQUIRED_KEYS:
            if not app.config.get(key):
                app.logger.error(f"生产环境必须配置 {key}")
                raise ValueError(f"生产环境必须配置 {key}")

# -------------------- 蓝图注册 --------------------
def register_blueprints(app: Flask):
    """注册所有蓝图"""
    from app.views.main_views import main_bp
    from app.views.root_views import root_bp
    from app.views.sales_views import sales_bp
    from app.views.user_views import user_bp
    from app.views.admin_user_views import admin_user_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(main_bp, url_prefix="/main")
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.register_blueprint(admin_user_bp)

# -------------------- 错误处理 --------------------
def handle_app_error(app: Flask, error: Exception, code: int) -> tuple:
    """统一错误处理"""
    app.logger.error(f"错误 {code}: {error}", exc_info=True)
    return render_template(f"errors/{code}.html", error=str(error)), code