from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, RoleType, Store
from app.forms.user_forms import EditProfileForm, RegistrationForm
from app.extensions import db
from functools import wraps

admin_user_bp = Blueprint('admin_user', __name__, url_prefix='/admin/users')

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role not in [RoleType.ADMIN, RoleType.HEAD_MANAGER, RoleType.FINANCE]:
            flash('无权限访问', 'danger')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    return wrapper

@admin_user_bp.route('/')
@login_required
@admin_required
def user_list():
    q = request.args.get('q', '')
    users = User.query
    if q:
        users = users.filter(User.username.contains(q))
    users = users.order_by(User.user_id.desc()).all()
    return render_template('admin/user_list.html', users=users, q=q)

@admin_user_bp.route('/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)

@admin_user_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = EditProfileForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()
        flash('用户资料已更新', 'success')
        return redirect(url_for('admin_user.user_detail', user_id=user.user_id))
    return render_template('admin/user_edit.html', form=form, user=user)

@admin_user_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def user_create():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            role=RoleType(form.role.data),
            store_id=form.store_id.data or None,
            real_name=form.real_name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('新用户已创建', 'success')
        return redirect(url_for('admin_user.user_list'))
    return render_template('admin/user_create.html', form=form)

@admin_user_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('用户已删除', 'success')
    return redirect(url_for('admin_user.user_list'))

@admin_user_bp.route('/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def user_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = '123456'
    user.set_password(new_password)
    db.session.commit()
    flash(f'密码已重置为：{new_password}', 'info')
    return redirect(url_for('admin_user.user_detail', user_id=user.user_id))
