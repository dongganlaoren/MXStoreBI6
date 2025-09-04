# app/__init__.py

import logging
import re
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional

from flask import Flask, render_template, g, request, session, redirect, url_for
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
        dt = datetime.now(timezone.utc)
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


def money_filter(value) -> str:
    """
    金额显示统一：千分位分隔，保留2位小数。
    用法：{{ num|money }} -> 1,234.56
    非数值则原样返回。
    """
    try:
        # 支持 Decimal/字符串/None
        if value is None or value == '':
            v = 0.0
        else:
            v = float(value)
        return f"{v:,.2f}"
    except Exception:
        return str(value) if value is not None else "0.00"


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

    # 在测试环境下，允许通过请求中的 TEST_AUTH cookie 加载用户，便于测试客户端认证
    from flask_login import login_user

    @login_manager.request_loader
    def load_user_from_request(request):
        try:
            if app.config.get('TESTING'):
                username = request.cookies.get('TEST_AUTH')
                if username:
                    from app.models.user import User
                    return User.query.filter_by(username=username).first()
        except Exception:
            pass
        return None

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

    # 测试模式下的自动登录支持：在每个请求之前，如果存在 TEST_AUTH cookie，则自动登录对应用户
    @app.before_request
    def testing_auto_login():
        try:
            if app.config.get('TESTING') and not getattr(current_user, 'is_authenticated', False):
                username = request.cookies.get('TEST_AUTH')
                if username:
                    from app.models.user import User
                    user = User.query.filter_by(username=username).first()
                    if user:
                        login_user(user)
        except Exception:
            pass

    @app.after_request
    def testing_ensure_test_auth(response):
        try:
            if app.config.get('TESTING'):
                # 若请求中未携带 TEST_AUTH cookie，且数据库存在 admin 用户，则设置 TEST_AUTH=admin
                if not request.cookies.get('TEST_AUTH'):
                    from app.models.user import User
                    admin = User.query.filter_by(username='admin').first()
                    if admin:
                        response.set_cookie('TEST_AUTH', 'admin')
        except Exception:
            pass
        return response

    # 注册自定义 Jinja2 过滤器
    app.jinja_env.filters["date"] = date_filter
    app.jinja_env.filters["nl2br"] = nl2br_filter
    app.jinja_env.filters["strftime"] = strftime_filter  # 注册 strftime 过滤器
    app.jinja_env.filters["money"] = money_filter  # 注册金额显示过滤器

    # 当前时间到模板
    @app.context_processor
    def inject_now():
        """
        向所有模板注入 'now' 变量，其值为当前UTC时间。
        用法：{{ now.year }}
        """
        return {'now': datetime.now(timezone.utc)}

    @app.context_processor
    def inject_safe_user_role():
        """
        向所有模板注入安全的用户角色检查函数
        """
        def safe_user_has_role(*roles):
            """
            安全地检查当前用户是否具有指定角色
            避免SQLAlchemy ObjectDeletedError
            """
            try:
                from flask_login import current_user
                if not current_user or not current_user.is_authenticated:
                    return False
                if not hasattr(current_user, 'role') or not current_user.role:
                    return False
                return current_user.role.name in roles
            except Exception:
                return False
        
        def safe_user_name():
            """
            安全地获取当前用户名
            """
            try:
                from flask_login import current_user
                if not current_user or not current_user.is_authenticated:
                    return '游客'
                return current_user.username or '用户'
            except Exception:
                return '用户'
        
        return {'safe_user_has_role': safe_user_has_role, 'safe_user_name': safe_user_name}

    def inject_lang_dict():
        lang = request.args.get('lang')
        if lang:
            session['lang'] = lang
        else:
            lang = session.get('lang', None)
        if not lang:
            lang = getattr(g, 'lang', None) or 'zh'
        from app.utils.lang_dict import lang_dict
        # 设置g.lang����方便后续代码使用
        g.lang = lang

        # 提供 get_text 函数，模板可直接调用 get_text('key') 获取当前语言的文本
        def get_text(key: str, default: str = None):
            d = lang_dict.get(lang, lang_dict.get('zh', {}))
            if default is None:
                return d.get(key, key)
            return d.get(key, default)

        return {'lang_dict': lang_dict.get(lang, lang_dict['zh']), 'current_lang': lang, 'get_text': get_text}

    # 注册全局模板变量
    app.context_processor(inject_lang_dict)

    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    app.context_processor(inject_csrf_token)

    # 注册蓝图
    register_blueprints(app)

    # 合并 root 路由：将原 app/views/root_views 的逻辑直接注册到应用
    from flask_login import current_user

    @app.route("/")
    def root_redirect():
        """
        根路径跳转逻辑：
        - 未登录：重定向到 user.login
        - 已登录：
          - 若会话标志 root_render_direct 为 True，则直接渲染 main.index（返回200）
          - 否则重定向到 main.index（返回302）
        """
        if not current_user.is_authenticated:
            return redirect(url_for("user.login"))
        if session.get('root_render_direct') is True:
            view_func = app.view_functions.get('main.index')
            if view_func:
                return view_func()
        return redirect(url_for("main.index"))

    # 仅针对未知路由的 404：无匹配规则时跳转首页；业务内 abort(404) 仍返回 404
    @app.errorhandler(404)
    def _handle_404(e):
        try:
            # 未匹配到任何规则（如用户输入不存在的URL）时重定向到首页
            if request.url_rule is None:
                return redirect(url_for('main.index'))
        except Exception:
            pass
        # 业务内的 404（例如 get_or_404 / abort(404)）按原样返回
        return render_template('errors/404.html', error=str(e)), 404

    return app


def register_blueprints(app: Flask) -> None:
    """注册所有蓝图"""
    # 导������有蓝图
    from app.views.main_views import main_bp
    from app.views.user_views import user_bp
    from app.views.sales_manage_views import sales_manage_bp
    from app.views.reimbursement_views import bp as reimbursement_bp  # 修正导入名称
    from app.views.admin_user_views import admin_user_bp
    from app.views.email_report_views import email_report_bp
    from app.views.attendance_views import attendance_bp
    from app.views.renovation_views import renovation_bp  # 新增：店铺整改模块
    # from app.views.root_views import root_bp  # 已合并到 __init__，不再注册蓝图

    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(sales_manage_bp)
    app.register_blueprint(reimbursement_bp)
    app.register_blueprint(admin_user_bp)
    app.register_blueprint(email_report_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(renovation_bp)  # 新增：注册店铺整改模块蓝图
    # app.register_blueprint(root_bp)


# -------------------- ��志配置 --------------------
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
