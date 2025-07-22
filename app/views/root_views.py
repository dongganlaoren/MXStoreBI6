# app/views/root_views.py

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user

root_bp = Blueprint("root", __name__)


@root_bp.route("/")
def root_redirect():
    """
    根路径跳转逻辑：
    - 若已登录，跳转到 main.index
    - 否则，跳转到 user.login
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    else:
        return redirect(url_for("user.login"))


@root_bp.route("/error")
def error():
    """错误页面"""
    error_code = request.args.get("code", "404")
    error_message = request.args.get("message", "页面未找到")
    return render_template(
        f"errors/{error_code}.html", error_message=error_message
    ), int(error_code)
