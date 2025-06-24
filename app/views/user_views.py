# app/views/user_views.py

from app.extensions import db
from app.forms.staff_forms import StaffForm

# 导入我们最终修复版的表单
from app.forms.user_forms import LoginForm, RegistrationForm

# 从我们统一的 app.models 中导入所有需要的模型和枚举
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


# 【核心新增】: 创建一个全新的视图函数，专门用于处理员工档案的创建和编辑
@user_bp.route('/edit_staff_info', methods=['GET', 'POST'])
@login_required
def edit_staff_info():
    """
    创建或编辑当前登录用户的员工档案。
    """
    # 1. 获取当前用户关联的员工档案，如果不存在，staff_info 将是 None
    staff_info = current_user.staff_info

    # 2. 创建我们刚刚修复的 StaffForm
    # 如果 staff_info 存在，就用它的数据来预填充表单 (obj=staff_info)
    # 这样用户一打开页面，就能看到自己已有的信息
    form = StaffForm(obj=staff_info)

    # 3. 处理表单提交 (POST请求)
    if form.validate_on_submit():
        try:
            # 如果 staff_info 是 None，说明这是在为用户“创建”新的员工档案
            if staff_info is None:
                staff_info = StoreStaff(
                    # 关键一步：将新档案的 user_id 设置为当前登录用户的ID，建立关联
                    user_id=current_user.user_id
                )
                db.session.add(staff_info)
                flash('员工档案创建成功！', 'success')
                current_app.logger.info(f"用户 {current_user.username} 成功创建了自己的员工档案。")
            else:
                flash('员工档案更新成功！', 'success')
                current_app.logger.info(f"用户 {current_user.username} 成功更新了自己的员工档案。")

            # 4. 使用 form.populate_obj() 将表单中的所有数据，一次性地填充到 staff_info 对象上
            # 注意：此方法要求表单字段名和模型字段名一致，我们之前已确保了这一点
            form.populate_obj(staff_info)
            # 提交数据库，将更改保存
            db.session.commit()

            # 操作成功后，重定向回个人资料页面，用户会立刻看到更新后的结果
            return redirect(url_for('user.profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"保存用户 {current_user.username} 的员工档案时发生错误: {e}", exc_info=True)
            flash('保存员工信息时发生未知错误，请联系管理员。', 'danger')

    # 5. 如果是GET请求（用户第一次打开页面），或者表单验证失败，就渲染编辑页面
    # 我们将表单对象 form 传递给模板，以便它能被渲染出来
    return render_template('user/staff_edit.html', form=form)


# --- login, logout, register 等函数保持不变 ---

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    # ... (此函数逻辑保持不变) ...
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('用户名或密码无效。')
    return render_template('user/login.html', form=form)


@user_bp.route('/logout')
@login_required
def logout():
    # ... (此函数逻辑保持不变) ...
    logout_user()
    flash('您已成功登出。')
    return redirect(url_for('main.index'))


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    # ... (此函数逻辑保持不变) ...
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, role=RoleType(form.role.data))
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功！')
        return redirect(url_for('user.login'))
    return render_template('user/register.html', form=form)