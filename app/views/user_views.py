# app/views/user_views.py

from app.extensions import db

# 导入我们更新后的表单
from app.forms.user_forms import EditProfileForm, LoginForm, RegistrationForm

# 导入我们需要的模型和枚举
from app.models import RoleType, User
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
    现在它只传递当前用户对象，因为所有信息都在 User 模型里。
    """
    current_app.logger.info(f"用户 {current_user.username} 正在查看个人资料页面。")
    # 传递 staff_info=current_user，模板可直接用 staff_info.xxx
    return render_template('user/profile.html', user=current_user, staff_info=current_user, title="我的资料")


@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    【全新逻辑】创建或编辑当前登录用户的个人资料。
    门店组用户只能一次性完善，完善后不可再编辑。
    """
    # 仅门店组用户受限
    if current_user.role in [RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER] and current_user.profile_completed:
        flash('您的员工档案已完善，无法再次修改。', 'warning')
        return redirect(url_for('user.profile'))

    # 1. 使用我们全新的 EditProfileForm
    #    用 obj=current_user 来自动从当前用户对象中预填充表单数据
    form = EditProfileForm(obj=current_user)

    # 2. 处理表单提交
    if form.validate_on_submit():
        try:
            # 3. 使用 form.populate_obj(current_user) 将表单中的所有数据，
            #    一次性地填充回 current_user 对象上。
            form.populate_obj(current_user)

            # 门店组用户完善后，标记为已完善
            if current_user.role in [RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER]:
                current_user.profile_completed = True

            # 4. 提交数据库会话，将所有更改保存
            db.session.commit()

            current_app.logger.info(f"用户 {current_user.username} 成功更新了自己的个人资料。")
            flash('您的个人资料已成功更新！', 'success')

            # 操作成功后，重定向回个人资料查看页面
            return redirect(url_for('user.profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"保存用户 {current_user.username} 的个人资料时发生错误: {e}", exc_info=True)
            flash('保存资料时发生未知错误，请联系管理员。', 'danger')

    # 如果是GET请求或表单验证失败，渲染编辑页面
    return render_template('user/edit_profile.html', form=form, title="编辑我的资料")


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    用户注册视图（已更新，处理店铺ID）
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # 根据角色决定是否需要店铺ID
        role = RoleType(form.role.data)
        store_id = form.store_id.data

        # 【核心业务逻辑】: 如果是门店组角色，必须选择一个店铺
        if role in [RoleType.BRANCH_MANAGER, RoleType.EMPLOYEE] and not store_id:
            flash('作为门店组成员，您必须选择一个所属店铺。', 'warning')
            # 因为验证失败，重新渲染表单，保留用户已填写的数据
            return render_template('user/register.html', form=form, title="注册")

        # 【核心业务逻辑】: 如果是管理组角色，强制将店铺ID设为None
        if role in [RoleType.ADMIN, RoleType.HEAD_MANAGER, RoleType.FINANCE]:
            store_id = None

        try:
            # 创建用户实例，现在包含所有信息
            new_user = User(
                username=form.username.data,
                role=role,
                store_id=store_id
            )
            new_user.set_password(form.password.data)

            db.session.add(new_user)
            db.session.commit()

            current_app.logger.info(f"新用户 {new_user.username} (角色: {role.name}) 注册成功。")
            login_user(new_user)  # 注册后自动登录
            flash('恭喜您，注册成功，已自动登录！', 'success')
            return redirect(url_for('main.index'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"用户注册时发生数据库错误: {e}", exc_info=True)
            flash('注册时发生未知错误，请稍后重试。', 'danger')

    return render_template('user/register.html', form=form, title="注册")


# --- 登录和登出视图保持不变 ---

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.user_status == 1 and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.last_login_time = db.func.now()  # 更新最后登录时间
            db.session.commit()
            current_app.logger.info(f"用户 {user.username} 登录成功。")
            return redirect(request.args.get('next') or url_for('main.index'))

        current_app.logger.warning(f"用户 {form.username.data} 登录失败：用户名或密码错误，或账户被禁用。")
        flash('用户名或密码无效，或账户已被禁用。', 'warning')

    return render_template('user/login.html', form=form, title="登录")


@user_bp.route('/logout')
@login_required
def logout():
    current_app.logger.info(f"用户 {current_user.username} 已登出。")
    logout_user()
    flash('您已成功登出。', 'success')
    return redirect(url_for('main.index'))

