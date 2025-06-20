# app/views/user_views.py

from app.extensions import db
from app.forms.user_forms import LoginForm, RegistrationForm
from app.models.user import RoleType, User
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

user_bp = Blueprint("user", __name__, url_prefix="/user")

@user_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("用户名已存在", "error")
            return render_template("user/register.html", form=form)

        user = User(
            username=form.username.data,
            role=RoleType(form.role.data)
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("注册成功，请登录", "success")
        return redirect(url_for("user.login"))

    return render_template("user/register.html", form=form)

@user_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))

        flash("用户名或密码错误", "error")

    return render_template("user/login.html", form=form)

@user_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已注销", "success")
    return redirect(url_for("user.login"))

@user_bp.route("/profile")
@login_required
def profile():
    return render_template("user/profile.html", user=current_user)
