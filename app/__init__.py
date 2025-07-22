# app/__init__.py

import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

from flask import Flask, g, render_template, request
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


def strftime_filter(value, format="%Y-%m-%d %H:%M:%S"):
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
    app.jinja_env.filters["strftime"] = strftime_filter

    # 注入当前时间到模板
    @app.context_processor
    def inject_now():
        """
        向所有模板注入 'now' 变量，其值为当前UTC时间。
        用法：{{ now.year }}
        """
        return {"now": datetime.utcnow()}

    @app.context_processor
    def inject_lang_dict():
        from app.utils.lang_dict import get_lang_dict

        lang = request.args.get("lang")
        g.lang_dict = get_lang_dict(lang)
        return {"lang_dict": g.lang_dict}

    # 配置用户加载函数
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        return User.query.get(int(user_id))

    # 注册蓝图
    from app.views.admin_user_views import admin_user_bp
    from app.views.main_views import main_bp
    from app.views.reimbursement_views import reimbursement_bp
    from app.views.root_views import root_bp
    from app.views.sales_manage_views import sales_manage_bp
    from app.views.user_views import user_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(admin_user_bp, url_prefix="/admin")
    app.register_blueprint(main_bp, url_prefix="/main")
    app.register_blueprint(sales_manage_bp, url_prefix="/sales")
    app.register_blueprint(reimbursement_bp, url_prefix="/reimbursement")

    # 错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # 全局请求处理器
    @app.before_request
    def before_request():
        g.request_start_time = datetime.utcnow()

    return app


def configure_logging(app):
    """配置日志"""
    if not app.debug and not app.testing:
        if app.config["LOG_TO_STDOUT"]:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists("logs"):
                os.mkdir("logs")
            file_handler = RotatingFileHandler(
                "logs/mixue_bi.log", maxBytes=10240, backupCount=10
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s "
                    "[in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("MixueBI startup")


def validate_production_config(app):
    """验证生产环境配置"""
    if app.config.get("ENV") == "production":
        required_configs = ["SECRET_KEY", "DATABASE_URL"]
        missing_configs = [
            config for config in required_configs if not app.config.get(config)
        ]
        if missing_configs:
            raise RuntimeError(
                f"生产环境缺少必要配置: {', '.join(missing_configs)}"
            )
