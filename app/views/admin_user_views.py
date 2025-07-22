from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import RoleType, User

admin_user_bp = Blueprint("admin_user", __name__)


@admin_user_bp.route("/admin")
@login_required
def admin_panel():
    """管理员面板"""
    if current_user.role not in [
        RoleType.ADMIN,
        RoleType.HEAD_MANAGER,
        RoleType.FINANCE,
    ]:
        flash("您没有权限访问管理员面板", "danger")
        return redirect(url_for("main.index"))
    return render_template("admin/panel.html")


@admin_user_bp.route("/admin/users")
@login_required
def list_users():
    """用户列表"""
    if current_user.role != RoleType.ADMIN:
        flash("只有系统管理员可以查看用户列表", "danger")
        return redirect(url_for("main.index"))

    users = User.query.all()
    return render_template("admin/users.html", users=users)


@admin_user_bp.route("/admin/users/<int:user_id>/toggle")
@login_required
def toggle_user_status(user_id):
    """切换用户状态（启用/禁用）"""
    if current_user.role != RoleType.ADMIN:
        flash("只有系统管理员可以管理用户状态", "danger")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    user.user_status = 1 - user.user_status  # 切换状态
    db.session.commit()

    status_text = "启用" if user.user_status == 1 else "禁用"
    flash(f"用户 {user.username} 已{status_text}", "success")
    return redirect(url_for("admin_user.list_users"))


@admin_user_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    """删除用户"""
    if current_user.role != RoleType.ADMIN:
        flash("只有系统管理员可以删除用户", "danger")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    if user.user_id == current_user.user_id:
        flash("不能删除自己的账户", "warning")
        return redirect(url_for("admin_user.list_users"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"用户 {username} 已删除", "success")
    return redirect(url_for("admin_user.list_users"))
