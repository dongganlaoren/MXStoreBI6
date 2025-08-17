# app/__init__.py

import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

from flask import Flask, render_template, g, request, session
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup, escape

from app import commands
from app.extensions import csrf, db, login_manager, migrate, mail
from app.views.email_report_views import register_email_report_tasks


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
    mail.init_app(app)  # 初始化邮件扩展
    login_manager.login_view = "user.login"
    app.url_map.strict_slashes = False
    validate_production_config(app)

    # 配置Flask-Login用户加载器
    @login_manager.user_loader
    def load_user(user_id):
        """加载用户的回调函数"""
        from app.models.user import User
        return User.query.filter_by(user_id=int(user_id)).first()

    # 注册自定义 Jinja2 过滤器
    app.jinja_env.filters["date"] = date_filter
    app.jinja_env.filters["nl2br"] = nl2br_filter
    app.jinja_env.filters["strftime"] = strftime_filter  # 注册 strftime 过滤器

    # ��当前时间到模板
    @app.context_processor
    def inject_now():
        """
        向所有模板注入 'now' 变量，其值为当前UTC时间。
        用法：{{ now.year }}
        """
        return {'now': datetime.utcnow()}

    def inject_lang_dict():
        lang = request.args.get('lang')
        if lang:
            session['lang'] = lang
        else:
            lang = session.get('lang', None)
        if not lang:
            lang = getattr(g, 'lang', None) or 'zh'
        from app.utils.lang_dict import lang_dict
        # 设置g.lang，方便后续代码使用
        g.lang = lang
        return {'lang_dict': lang_dict.get(lang, lang_dict['zh']), 'current_lang': lang}

    # 注册全局模板变量
    app.context_processor(inject_lang_dict)

    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    app.context_processor(inject_csrf_token)

    # 注册蓝图
    register_blueprints(app)

    # 初始化监控系统
    init_monitoring(app)

    # 注册邮件报告任务 - 注释掉直到我们有调度器实例
    # with app.app_context():
    #     register_email_report_tasks()

    return app


def register_blueprints(app: Flask) -> None:
    """注册所有蓝图"""
    # 导入所有蓝图
    from app.views.main_views import main_bp
    from app.views.user_views import user_bp
    from app.views.sales_manage_views import sales_manage_bp
    from app.views.reimbursement_views import bp as reimbursement_bp  # 修正导入名称
    from app.views.admin_user_views import admin_user_bp
    from app.views.email_report_views import email_report_bp
    from app.views.root_views import root_bp
    from app.views.monitor_views import monitor_bp

    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(sales_manage_bp)
    app.register_blueprint(reimbursement_bp)
    app.register_blueprint(admin_user_bp)
    app.register_blueprint(email_report_bp)
    app.register_blueprint(root_bp)
    app.register_blueprint(monitor_bp)  # 注册监控蓝图


def init_monitoring(app: Flask) -> None:
    """初始化监控系统"""
    # 设置数据库日志处理器
    if app.config.get('ENV') == 'production':
        from app.utils.monitor import DatabaseLogHandler, setup_request_logging

        # 添加数据库日志处理器
        db_handler = DatabaseLogHandler()
        db_handler.setLevel(logging.WARNING)  # 只记录WARNING及以上级别的日志到数据库
        app.logger.addHandler(db_handler)

        # 设置请求日志记录
        setup_request_logging(app)

        # 启动监控定时任务 - 仅生产环境启动
        try:
            from app.utils.scheduler import start_monitoring_tasks
            start_monitoring_tasks(app)
            app.logger.info("监控定时任务已启动（仅生产环境）")
        except Exception as e:
            app.logger.error(f"启动监控任务失败: {e}")
    else:
        app.logger.info("开发/测试环境不启动监控定时任务。如需关闭生产环境监控，请在 .env 设置 MONITORING_ENABLED=False")


# -------------------- 日�����配置 --------------------
def configure_logging(app: Flask):
    """配置日志文件滚动"""
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3, encoding='utf-8')
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


# -------------------- 错误处理 --------------------
def handle_app_error(app: Flask, error: Exception, code: int) -> tuple:
    """统一错误处理"""
    app.logger.error(f"错误 {code}: {error}", exc_info=True)
    return render_template(f"errors/{code}.html", error=str(error)), code
