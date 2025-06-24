# app/views/user_views.py
from app.extensions import db
from app.forms.staff_forms import StaffForm
from app.forms.user_forms import LoginForm, RegistrationForm
from app.models import RoleType, StoreStaff, User
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

user_bp = Blueprint('user', __name__)


@user_bp.route('/profile')
@login_required
def profile():
    """
    统一的个人资料页面视图。
    它会同时展示用户的账户信息和关联的员工档案信息。
    """
    try:
        # staff_info 是我们之前在 User 模型中定义的“一对一”关系
        staff_info = current_user.staff_info

        current_app.logger.info(f"用户 {current_user.username} 正在查看个人资料页面。")

        # 将当前用户对象(user)和可能存在的员工档案对象(staff_info)一并传给模板
        return render_template('user/profile.html', user=current_user, staff_info=staff_info)

    except Exception as e:
        current_app.logger.error(f"加载用户 {current_user.username} 的个人资料时发生错误: {e}", exc_info=True)
        flash("加载个人资料时发生未知错误，请联系管理员。", "danger")
        return redirect(url_for('main.index'))


# 【核心修正】: 创建一个全新的视图函数，专门用于处理员工档案的创建和编辑
@user_bp.route('/edit_staff_info', methods=['GET', 'POST'])
@login_required
def edit_staff_info():
    """
    创建或编辑当前登录用户的员工档案。
    修改：用户只能一次性完善档案，完成后不能再次编辑。
    """
    # 1. 获取当前用户关联的员工档案
    staff_info = current_user.staff_info

    # 【核心修改】：如果用户已经有员工档案，则不允许再次编辑
    if staff_info:
        flash('您已完善员工档案，无法再次编辑。', 'info')
        current_app.logger.info(f"用户 {current_user.username} 已有员工档案，禁止再次编辑。")
        return redirect(url_for('user.profile'))

    # 2. 创建 StaffForm
    form = StaffForm()

    # 3. 处理表单提交 (POST请求)
    if form.validate_on_submit():
        try:
            # 创建新的员工档案
            staff_info = StoreStaff(
                user_id=current_user.user_id
            )
            form.populate_obj(staff_info)  # 填充表单数据
            db.session.add(staff_info)
            db.session.commit()

            flash('员工档案创建成功！', 'success')
            current_app.logger.info(f"用户 {current_user.username} 成功创建了自己的员工档案。")

            return redirect(url_for('user.profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"保存用户 {current_user.username} 的员工档案时发生错误: {e}", exc_info=True)
            flash('保存员工信息时发生未知错误，请联系管理员。', 'danger')

    # 4. 如果是GET请求（用户第一次打开页面），或者表单验证失败，就渲染编辑页面
    return render_template('user/staff_edit.html', form=form)