# app/views/root_views.py

from flask import Blueprint, redirect, url_for
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
