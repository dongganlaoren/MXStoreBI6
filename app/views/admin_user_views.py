import os
import uuid
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms.user_forms import EditProfileForm, RegistrationForm
from app.models import User, RoleType

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
    return render_template('user/user_list.html', users=users, q=q)


@admin_user_bp.route('/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user/user_detail.html', user=user)


@admin_user_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = EditProfileForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        # 修正：防止 employee_number 为空字符串写入数据库
        if hasattr(user, 'employee_number'):
            if user.employee_number == '' or user.employee_number is None:
                user.employee_number = None
            else:
                try:
                    user.employee_number = int(user.employee_number)
                except Exception:
                    user.employee_number = None
        # 强制 role 字段为大写枚举，防止小写写入
        if hasattr(form, 'role') and form.role.data:
            user.role = RoleType(form.role.data.upper())
        # 处理身份证复印件上传
        file = form.id_card_copy.data
        if file:
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'secure')
            os.makedirs(upload_dir, exist_ok=True)
            ext = os.path.splitext(secure_filename(file.filename))[1]
            filename = f"idcard_{user.user_id}_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            # 只存相对路径
            user.id_card_copy = f"uploads/secure/{filename}"
        db.session.commit()
        flash('用户资料已更新', 'success')
        return redirect(url_for('admin_user.user_detail', user_id=user.user_id))
    return render_template('user/user_edit.html', form=form, user=user)


@admin_user_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def user_create():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            role=RoleType(form.role.data.upper()),
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
    return render_template('user/user_create.html', form=form)


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


@admin_user_bp.route('/<int:user_id>/download_id_card_copy')
@login_required
@admin_required
def download_id_card_copy(user_id):
    user = User.query.get_or_404(user_id)
    if not user.id_card_copy:
        abort(404)
    file_path = user.id_card_copy  # 形如 uploads/secure/xxx.jpg
    abs_dir = os.path.join(current_app.root_path, 'static', os.path.dirname(file_path))
    filename = os.path.basename(file_path)
    # 只允许在线预览，不允许下载
    return send_from_directory(abs_dir, filename, as_attachment=False)
