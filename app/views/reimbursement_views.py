import logging
import os
import traceback
from datetime import datetime
from json import loads, JSONDecodeError

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask import current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy import or_, exists
from sqlalchemy.orm import aliased
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms.reimbursement_forms import ReimbursementCreateForm, ReimbursementApproveForm
from app.models.enums import ReimbursementAttachmentType
from app.models.enums import ReimbursementStatus
from app.models.reimbursement import ReimbursementRequest, ReimbursementAttachment, ReimbursementCCRecipient, \
    ReimbursementDefaultCCRecipient
from app.models.user import User
from app.utils.lang_dict import lang_dict
from app.utils.notify import send_notify_mail

bp = Blueprint('reimbursement', __name__, url_prefix='/reimbursement')


@bp.route('/')
@login_required
def list_requests():
    # 获取筛选参数
    category = request.args.get('category', 'todo')  # todo, done, mine
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    time_range = request.args.get('time_range', 'all')

    query = ReimbursementRequest.query
    role = getattr(current_user.role, 'value', None)
    # 门店组用户只能看到自己提交的
    if role in ['BRANCH_MANAGER', 'EMPLOYEE', 'HEAD_MANAGER']:
        query = query.filter(ReimbursementRequest.submitter_id == current_user.user_id)
    elif role in ['FINANCE', 'ADMIN']:
        if category == 'todo':
            query = query.filter(
                ReimbursementRequest.approver_id == current_user.user_id,
                ReimbursementRequest.status == ReimbursementStatus.PENDING
            )
        elif category == 'done':
            # 只查审批人为自己且状态为已审批（APPROVED/REJECTED）
            query = query.filter(
                ReimbursementRequest.approver_id == current_user.user_id,
                ReimbursementRequest.status.in_([ReimbursementStatus.APPROVED, ReimbursementStatus.REJECTED])
            )
        elif category == 'mine':
            # 只查提交人为自己
            query = query.filter(ReimbursementRequest.submitter_id == current_user.user_id)
        elif category == 'cc':
            # 新增：查看抄送给自己的申请
            query = query.join(ReimbursementCCRecipient).filter(
                ReimbursementCCRecipient.user_id == current_user.user_id
            )
        elif category == 'unchecked':
            # 新增：未核对（仅针对已审批通过但未核对的单据）
            try:
                from app.models.enums import ReimbursementCheckStatus
                query = query.filter(
                    ReimbursementRequest.status == ReimbursementStatus.APPROVED,
                    ReimbursementRequest.check_status == ReimbursementCheckStatus.UNCHECKED
                )
            except Exception:
                # 兜底：如导入失败，不进行筛选
                pass
        elif category == 'all':
            # 新增：全部状态（与我相关：我为审批人 或 我为提交人 或 抄送给我）
            try:
                # 使用 EXISTS 判断抄送
                cc_exists = exists().where(
                    (ReimbursementCCRecipient.request_id == ReimbursementRequest.request_id) &
                    (ReimbursementCCRecipient.user_id == current_user.user_id)
                )
                query = query.filter(or_(
                    ReimbursementRequest.approver_id == current_user.user_id,
                    ReimbursementRequest.submitter_id == current_user.user_id,
                    cc_exists
                ))
            except Exception:
                # 兜底：如出现异常，则退化为审批人为自己
                query = query.filter(ReimbursementRequest.approver_id == current_user.user_id)
        else:
            # 默认：审批人为自己
            query = query.filter(ReimbursementRequest.approver_id == current_user.user_id)
    # 时间筛选
    from datetime import datetime, timedelta
    # 财务/管理员在 todo、done 分类下使用 updated_at，以便包含转交等最新变更
    use_updated = (role in ['FINANCE', 'ADMIN']) and (category in ['todo', 'done'])
    date_field = ReimbursementRequest.updated_at if use_updated else ReimbursementRequest.created_at
    if time_range == '24h':
        begin = datetime.now() - timedelta(days=1)
        query = query.filter(date_field >= begin)
    elif time_range == '7d':
        begin = datetime.now() - timedelta(days=7)
        query = query.filter(date_field >= begin)
    elif time_range == '30d':
        begin = datetime.now() - timedelta(days=30)
        query = query.filter(date_field >= begin)
    elif time_range == 'custom' and start_date and end_date:
        try:
            begin = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(date_field >= begin, date_field < end)
        except Exception:
            pass
    requests = query.order_by(ReimbursementRequest.updated_at.desc()).all()

    # 优先从请求参数获取语言
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])

    class DummyForm(FlaskForm):
        pass

    form = DummyForm()

    return render_template('reimbursement/list.html',
                           requests=requests,
                           category=category,
                           time_range=time_range,
                           start_date=start_date,
                           end_date=end_date,
                           lang=lang,
                           current_lang=current_lang,
                           form=form
                           )


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ReimbursementCreateForm()
    if form.validate_on_submit():
        try:
            # 类型转换，确保与模型一致
            # 如果是公摊成本，store_id强制为None
            if form.primary_category.data == 'SHARED_COST':
                store_id = None
            else:
                store_id = form.store_id.data or None
            approver_id = int(form.approver_id.data) if form.approver_id.data else None

            # 重复提交拦截：同一提交人、同一门店/分类/金额/币种/事由，且提交日期相同
            try:
                from datetime import timedelta
                submit_day = form.submission_date.data
                if submit_day:
                    day_begin = datetime.combine(submit_day, datetime.min.time())
                    day_end = day_begin + timedelta(days=1)
                else:
                    # 兜底：以当天作为范围
                    now_day = datetime.now().date()
                    day_begin = datetime.combine(now_day, datetime.min.time())
                    day_end = day_begin + timedelta(days=1)
                existing = (ReimbursementRequest.query
                            .filter(
                    ReimbursementRequest.submitter_id == current_user.user_id,
                    ReimbursementRequest.store_id.is_(
                        None) if store_id is None else ReimbursementRequest.store_id == store_id,
                    ReimbursementRequest.primary_category == form.primary_category.data,
                    ReimbursementRequest.secondary_category == form.secondary_category.data,
                    ReimbursementRequest.amount == form.amount.data,
                    ReimbursementRequest.currency == form.currency.data,
                    ReimbursementRequest.description == form.reason.data,
                    ReimbursementRequest.created_at >= day_begin,
                    ReimbursementRequest.created_at < day_end
                )
                            .first())
                if existing:
                    flash('当天已存在相同报销申请，请勿重复提交', 'warning')
                    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
                    lang = lang_dict.get(current_lang, lang_dict['zh'])
                    return render_template('reimbursement/create.html', form=form, lang=lang, current_lang=current_lang)
            except Exception:
                # 兜底：任何异常不影响正常提交流程
                pass

            req = ReimbursementRequest(
                primary_category=form.primary_category.data,
                secondary_category=form.secondary_category.data,
                store_id=store_id,
                description=form.reason.data,  # 保证字段一致，模型字段为description
                amount=form.amount.data,
                currency=form.currency.data,  # 新增：保存货币单位
                status=ReimbursementStatus.PENDING,
                submitter_id=current_user.user_id,
                approver_id=approver_id
            )
            db.session.add(req)
            db.session.flush()  # 先获取request_id

            # 处理抄送人
            cc_recipients_data = form.cc_recipients.data
            cc_emails = []  # 用于收集抄送人邮箱
            processed_user_ids = set()  # 避免重复添加

            # 首先添加用户手动选择的抄送人
            if cc_recipients_data:
                try:
                    cc_user_ids = loads(cc_recipients_data)
                    for user_id in cc_user_ids:
                        if user_id and user_id != approver_id and user_id != current_user.user_id:
                            user_id = int(user_id)
                            if user_id not in processed_user_ids:
                                cc_recipient = ReimbursementCCRecipient(
                                    request_id=req.request_id,
                                    user_id=user_id
                                )
                                db.session.add(cc_recipient)
                                processed_user_ids.add(user_id)
                                # 收集抄送人邮箱
                                cc_user = User.query.get(user_id)
                                if cc_user and cc_user.email:
                                    cc_emails.append(cc_user.email)
                except (JSONDecodeError, ValueError) as e:
                    logging.warning(f"解析抄送人数据失败: {e}")

            # 自动添加默认抄送人
            default_cc_recipients = ReimbursementDefaultCCRecipient.query.filter_by(is_active=True).all()
            for default_cc in default_cc_recipients:
                user_id = default_cc.user_id
                # 避免重复添加（排除审批人、申请人和已经手动添加的用户）
                if (user_id != approver_id and
                        user_id != current_user.user_id and
                        user_id not in processed_user_ids):
                    try:
                        cc_recipient = ReimbursementCCRecipient(
                            request_id=req.request_id,
                            user_id=user_id
                        )
                        db.session.add(cc_recipient)
                        processed_user_ids.add(user_id)
                        # 收集默认抄送人邮箱
                        if default_cc.user and default_cc.user.email:
                            cc_emails.append(default_cc.user.email)
                    except Exception as e:
                        logging.warning(f"添加默认抄送人失败: user_id={user_id}, error={e}")

            # 多文件保存
            files = form.attachments.data or []
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    # 防止重名，拼接request_id和时间戳
                    save_name = f"{req.request_id}_{int(datetime.now().timestamp())}_{filename}"
                    file_path = os.path.join(upload_folder, save_name)
                    file.save(file_path)
                    rel_path = os.path.relpath(file_path, start=current_app.root_path)
                    att = ReimbursementAttachment(
                        request_id=req.request_id,
                        attachment_type=ReimbursementAttachmentType.SUBMISSION,
                        uploader_id=current_user.user_id,
                        original_filename=filename,
                        file_path=rel_path.replace('\\', '/'),
                        file_size=os.path.getsize(file_path),
                        mime_type=file.mimetype,
                    )
                    db.session.add(att)
            db.session.commit()
            logging.info(f"报销申请保存成功: {req}")

            # 邮件通知审核人
            approver = User.query.get(approver_id) if approver_id else None
            if approver and approver.email:
                subject = "【系统通知】有新的财务报销申请待您审批"
                body = f"您好，您有一条新的报销申请待审批。申请人：{current_user.real_name or current_user.username}，金额：{form.amount.data} {form.currency.data}。请及时登录系统处理。"
                send_notify_mail(subject, [approver.email], body)
            else:
                logging.warning(f"审核人未填写邮箱，无法发送报销通知邮件。审核人ID: {approver_id}")

            # 邮件通知抄送人
            if cc_emails:
                subject = "【系统通知】财务报销申请抄送"
                body = f"您好，有一条报销申请抄送给您查看。申请人：{current_user.real_name or current_user.username}，金额：{form.amount.data} {form.currency.data}。您可以登录系统查看详情。"
                send_notify_mail(subject, cc_emails, body)

            flash('报销申请已提交', 'success')
            return redirect(url_for('reimbursement.list_requests'))
        except Exception as e:
            db.session.rollback()
            logging.exception(f"报销申请保存失败: {e}")  # 输出完整堆栈
            print(traceback.format_exc())  # 控制台输出异常
            flash(f'保存失败: {e}', 'danger')
    else:
        print("表单校验失败:", form.errors)
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])
    return render_template('reimbursement/create.html', form=form, lang=lang, current_lang=current_lang)


@bp.route('/<int:request_id>')
@login_required
def detail(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    attachments = req.attachments.all()
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])
    return render_template('reimbursement/detail.html', req=req, attachments=attachments, lang=lang,
                           current_lang=current_lang)


@bp.route('/<int:request_id>/approve', methods=['GET', 'POST'])
@login_required
def approve(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    # 已核对不可再修改
    if getattr(req, 'check_status', None) and str(req.check_status.value) == 'CHECKED':
        flash('报销单据已核对，不可再修改。', 'warning')
        return redirect(url_for('reimbursement.detail', request_id=request_id))
    form = ReimbursementApproveForm()
    if form.validate_on_submit():
        # 直接审批通过，无需status字段
        req.status = ReimbursementStatus.APPROVED
        req.approval_comments = form.approval_comments.data
        req.approved_at = datetime.now()
        # 保存审批附件
        files = request.files.getlist('attachments') if 'attachments' in request.files else []
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_name = f"{req.request_id}_{int(datetime.now().timestamp())}_{filename}"
                file_path = os.path.join(upload_folder, save_name)
                file.save(file_path)
                rel_path = os.path.relpath(file_path, start=current_app.root_path)
                att = ReimbursementAttachment(
                    request_id=req.request_id,
                    attachment_type=ReimbursementAttachmentType.APPROVAL,
                    uploader_id=current_user.user_id,
                    original_filename=filename,
                    file_path=rel_path.replace('\\', '/'),
                    file_size=os.path.getsize(file_path),
                    mime_type=file.mimetype,
                )
                db.session.add(att)
        db.session.commit()
        # 审批通过后邮件通知提交人
        submitter = User.query.get(req.submitter_id)
        if submitter and submitter.email:
            subject = "【系统通知】您的财务报销申请已审批通过"
            body = f"您好，您的报销申请已审批通过。金额：{req.amount} {req.currency}。审批意见：{req.approval_comments or '无'}。请及时登录系统查看详情。"
            send_notify_mail(subject, [submitter.email], body)
        else:
            logging.warning(f"提交人未填写邮箱，无法发送审批通过通知邮件。提交人ID: {req.submitter_id}")
        flash('审批已通过', 'success')
        return redirect(url_for('reimbursement.detail', request_id=request_id))

    # 获取当前语言并传递给模板
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])
    return render_template('reimbursement/approve.html', form=form, req=req, lang=lang, current_lang=current_lang)


@bp.route('/approver_search')
@login_required
def approver_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    from app.models.enums import RoleType
    users = User.query.filter(
        User.user_status == 1,
        User.role.in_([RoleType.ADMIN, RoleType.FINANCE]),
        or_(
            User.user_id.like(f"%{q}%"),
            User.username.like(f"%{q}%"),
            User.employee_number.like(f"%{q}%"),
            User.real_name.like(f"%{q}%"),
            User.phone.like(f"%{q}%"),
            User.line_id.like(f"%{q}%"),
            User.email.like(f"%{q}%")
        )
    ).limit(20).all()
    result = [
        {
            'user_id': u.user_id,
            'label': f"{u.real_name or ''}({u.username}) [{u.user_id}]",
            'username': u.username,
            'real_name': u.real_name,
            'employee_number': u.employee_number,
            'phone': u.phone,
            'line_id': u.line_id,
            'email': u.email
        }
        for u in users
    ]
    return jsonify(result)


@bp.route('/cc_recipients_search')
@login_required
def cc_recipients_search():
    """抄送人搜索接口 - 可搜索所有在职用户"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    users = User.query.filter(
        User.user_status == 1,  # 只搜索在职用户
        or_(
            User.user_id.like(f"%{q}%"),
            User.username.like(f"%{q}%"),
            User.employee_number.like(f"%{q}%"),
            User.real_name.like(f"%{q}%"),
            User.phone.like(f"%{q}%"),
            User.line_id.like(f"%{q}%"),
            User.email.like(f"%{q}%")
        )
    ).limit(20).all()
    result = [
        {
            'user_id': u.user_id,
            'label': f"{u.real_name or ''}({u.username}) [{u.user_id}]",
            'username': u.username,
            'real_name': u.real_name,
            'employee_number': u.employee_number,
            'phone': u.phone,
            'line_id': u.line_id,
            'email': u.email,
            'role': u.role.value if u.role else ''
        }
        for u in users
    ]
    return jsonify(result)


@bp.route('/all')
@login_required
def list_all():
    # 只允许admin/ADMIN访问
    if not (current_user.is_authenticated and current_user.username == 'admin' and getattr(current_user.role, 'name',
                                                                                           None) == 'ADMIN'):
        flash('无权限访问', 'danger')
        return redirect(url_for('main.index'))
    submitter = request.args.get('submitter', '').strip()
    approver = request.args.get('approver', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = ReimbursementRequest.query

    # 使用别名，避免双 JOIN users 产生歧义
    Submitter = aliased(User)
    Approver = aliased(User)
    if submitter:
        query = query.join(Submitter, ReimbursementRequest.submitter_id == Submitter.user_id)
        query = query.filter(
            (Submitter.username.like(f"%{submitter}%")) |
            (Submitter.real_name.like(f"%{submitter}%")) |
            (Submitter.employee_number.like(f"%{submitter}%"))
        )
    if approver:
        query = query.join(Approver, ReimbursementRequest.approver_id == Approver.user_id)
        query = query.filter(
            (Approver.username.like(f"%{approver}%")) |
            (Approver.real_name.like(f"%{approver}%")) |
            (Approver.employee_number.like(f"%{approver}%"))
        )
    from datetime import datetime, timedelta
    if start_date:
        try:
            begin = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(ReimbursementRequest.created_at >= begin)
        except Exception:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ReimbursementRequest.created_at < end)
        except Exception:
            pass
    requests = query.order_by(ReimbursementRequest.created_at.desc()).all()
    return render_template('reimbursement/list_all.html', requests=requests)


@bp.route('/<int:request_id>/withdraw', methods=['POST'])
@login_required
def withdraw(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    # 已核对不可再修改
    if getattr(req, 'check_status', None) and str(req.check_status.value) == 'CHECKED':
        flash('报销单据已核对，不可再修改。', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    if req.submitter_id != current_user.user_id:
        flash('无权撤回该申请', 'danger')
        return redirect(url_for('reimbursement.list_requests'))
    if req.status != ReimbursementStatus.PENDING:
        flash('仅待审批状态可撤回', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    req.status = ReimbursementStatus.DRAFT
    db.session.commit()
    flash('已撤回为草稿，可重新编辑', 'success')
    return redirect(url_for('reimbursement.list_requests'))


@bp.route('/<int:request_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    # 已核对不可再修改
    if getattr(req, 'check_status', None) and str(req.check_status.value) == 'CHECKED':
        flash('报销单据已核对，不可再修改。', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    if req.submitter_id != current_user.user_id or req.status != ReimbursementStatus.DRAFT:
        flash('仅本人草稿可编辑', 'danger')
        return redirect(url_for('reimbursement.list_requests'))
    form = ReimbursementCreateForm(obj=req)
    if form.validate_on_submit():
        try:
            if form.primary_category.data == 'SHARED_COST':
                req.store_id = None
            else:
                req.store_id = form.store_id.data or None
            req.primary_category = form.primary_category.data
            req.secondary_category = form.secondary_category.data
            req.description = form.reason.data
            req.amount = form.amount.data
            req.currency = form.currency.data
            req.approver_id = int(form.approver_id.data) if form.approver_id.data else None
            req.status = ReimbursementStatus.PENDING  # 重新提交
            req.updated_at = datetime.now()
            # 附件处理略（如需支持编辑附件可补充）
            db.session.commit()
            flash('草稿已提交', 'success')
            return redirect(url_for('reimbursement.list_requests'))
        except Exception as e:
            db.session.rollback()
            flash(f'保存失败: {e}', 'danger')
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])
    return render_template('reimbursement/create.html', form=form, lang=lang, current_lang=current_lang, is_edit=True)


@bp.route('/<int:request_id>/delete', methods=['POST'])
@login_required
def delete(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    # 已核对不可再改
    if getattr(req, 'check_status', None) and str(req.check_status.value) == 'CHECKED':
        flash('报销单据已核对，不可再修改。', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    if req.submitter_id != current_user.user_id or req.status != ReimbursementStatus.DRAFT:
        flash('仅本人草稿可删除', 'danger')
        return redirect(url_for('reimbursement.list_requests'))
    # 删除相关附件文件和数据库记录
    attachments = req.attachments.all()
    for att in attachments:
        try:
            file_path = os.path.join(current_app.root_path, att.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.warning(f"删除附件文件失败: {att.file_path}, 错误: {e}")
        db.session.delete(att)
    db.session.delete(req)
    db.session.commit()
    flash('草稿已删除', 'success')
    return redirect(url_for('reimbursement.list_requests'))


@bp.route('/<int:request_id>/transfer', methods=['POST'])
@login_required
def transfer_approver(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    print(
        f"[transfer] enter: req_id={request_id}, status={getattr(req.status, 'value', req.status)}, approver_id={req.approver_id}, current_user={getattr(current_user, 'user_id', None)}")
    # 已核对不可再修改
    if getattr(req, 'check_status', None) and str(req.check_status.value) == 'CHECKED':
        print("[transfer] blocked: CHECKED")
        flash('报销单据已核对，不可再修改。', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    # 仅待审批且当前用户为审批人才能转交
    if req.status != ReimbursementStatus.PENDING or req.approver_id != current_user.user_id:
        print(
            f"[transfer] blocked: status/approver mismatch, status={getattr(req.status, 'value', req.status)}, approver={req.approver_id}, me={current_user.user_id}")
        flash('仅待审批且您为当前审批人时可转交', 'danger')
        return redirect(url_for('reimbursement.list_requests'))
    new_approver_id = request.form.get('new_approver_id')
    print(f"[transfer] form new_approver_id={new_approver_id}")
    if not new_approver_id:
        print("[transfer] blocked: missing new_approver_id")
        flash('请选择新的审批人', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    # 校验新审批人权限
    try:
        new_approver = User.query.get(int(new_approver_id))
    except Exception as e:
        print(f"[transfer] invalid new_approver_id cast: {e}")
        new_approver = None
    if not new_approver or (new_approver.role and new_approver.role.value not in ['FINANCE', 'ADMIN']) is False:
        pass
    if not new_approver or new_approver.role is None or new_approver.role.value not in ['FINANCE', 'ADMIN']:
        print(
            f"[transfer] blocked: approver role invalid, user={getattr(new_approver, 'user_id', None)}, role={getattr(new_approver.role, 'value', None)}")
        flash('新审批人无审批权限', 'danger')
        return redirect(url_for('reimbursement.list_requests'))
    # 更新审批人
    req.approver_id = new_approver.user_id
    try:
        req.updated_at = datetime.now()
    except Exception:
        pass
    db.session.commit()
    print(f"[transfer] success: new approver_id={req.approver_id}")
    # 邮件通知新审批人
    if new_approver.email:
        subject = "【系统通知】有报销申请已转交给您审批"
        body = f"您好，报销申请(ID:{req.request_id})已由 {current_user.real_name or current_user.username} 转交给您。请及时登录系统处理。"
        send_notify_mail(subject, [new_approver.email], body)
    flash('已成功转交给新审批人', 'success')
    return redirect(url_for('reimbursement.list_requests'))


# 新增：默认抄送人管理接口（仅管理员可访问）
@bp.route('/default_cc_config', methods=['GET', 'POST'])
@login_required
def default_cc_config():
    """默认抄送人配置管理 - 仅管理员可访问"""
    if not (current_user.role and current_user.role.value in ['ADMIN']):
        flash('无权限访问该功能', 'danger')
        return redirect(url_for('reimbursement.list_requests'))

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')

        if action == 'add' and user_id:
            try:
                user_id = int(user_id)
                # 检查用户是否存在且有效
                user = User.query.filter_by(user_id=user_id, user_status=1).first()
                if not user:
                    flash('用户不存在或已禁用', 'danger')
                else:
                    # 检查是否已经是默认抄送人
                    existing = ReimbursementDefaultCCRecipient.query.filter_by(user_id=user_id).first()
                    if existing:
                        if existing.is_active:
                            flash('该用户已经是默认抄送人', 'warning')
                        else:
                            # 重新启用
                            existing.is_active = True
                            db.session.commit()
                            flash('已重新启用该默认抄送人', 'success')
                    else:
                        # 新增默认抄送人
                        default_cc = ReimbursementDefaultCCRecipient(
                            user_id=user_id,
                            created_by=current_user.user_id
                        )
                        db.session.add(default_cc)
                        db.session.commit()
                        flash('已添加默认抄送人', 'success')
            except (ValueError, TypeError):
                flash('无效的用户ID', 'danger')

        elif action == 'disable' and user_id:
            try:
                user_id = int(user_id)
                default_cc = ReimbursementDefaultCCRecipient.query.filter_by(user_id=user_id, is_active=True).first()
                if default_cc:
                    default_cc.is_active = False
                    db.session.commit()
                    flash('已禁用该默认抄送人', 'success')
                else:
                    flash('默认抄送人不存在', 'danger')
            except (ValueError, TypeError):
                flash('无效的用户ID', 'danger')

    # 获取当前的默认抄送人配置
    default_ccs = ReimbursementDefaultCCRecipient.query.filter_by(is_active=True).all()

    # 获取当前语言并传递给模板
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])

    return render_template('reimbursement/default_cc_config.html', default_ccs=default_ccs, lang=lang,
                           current_lang=current_lang)


@bp.route('/default_cc_search')
@login_required
def default_cc_search():
    """默认抄送人搜索接口 - 仅管理员可访问"""
    if not (current_user.role and current_user.role.value in ['ADMIN']):
        return jsonify([])

    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    # 使用 exists 避免 IN 子查询触发的 SAWarning
    subq = exists().where(
        (ReimbursementDefaultCCRecipient.user_id == User.user_id) &
        (ReimbursementDefaultCCRecipient.is_active.is_(True))
    )

    users = User.query.filter(
        User.user_status == 1,  # 只搜索在职用户
        ~subq,  # 排除已经是默认抄送人的用户
        or_(
            User.user_id.like(f"%{q}%"),
            User.username.like(f"%{q}%"),
            User.employee_number.like(f"%{q}%"),
            User.real_name.like(f"%{q}%"),
            User.phone.like(f"%{q}%"),
            User.line_id.like(f"%{q}%"),
            User.email.like(f"%{q}%")
        )
    ).limit(20).all()

    result = [
        {
            'user_id': u.user_id,
            'label': f"{u.real_name or ''}({u.username}) [{u.user_id}] - {u.role.value if u.role else ''}",
            'username': u.username,
            'real_name': u.real_name,
            'employee_number': u.employee_number,
            'phone': u.phone,
            'line_id': u.line_id,
            'email': u.email,
            'role': u.role.value if u.role else ''
        }
        for u in users
    ]
    return jsonify(result)


@bp.route('/<int:request_id>/mark_checked', methods=['POST'])
@login_required
def mark_checked(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    role = getattr(current_user.role, 'value', None)
    if role not in ['FINANCE', 'ADMIN']:
        flash('仅财务/管理员可执行核对操作', 'danger')
        return redirect(url_for('reimbursement.list_requests'))
    # 必须已审批通过，且未核对
    if req.status != ReimbursementStatus.APPROVED:
        flash('仅已审批通过的报销可标记为已核对', 'warning')
        return redirect(url_for('reimbursement.list_requests'))
    if getattr(req, 'check_status', None) and str(req.check_status.value) == 'CHECKED':
        flash('该报销单据已核对，无需重复操作', 'info')
        return redirect(url_for('reimbursement.list_requests'))
    try:
        from app.models.enums import ReimbursementCheckStatus
        req.check_status = ReimbursementCheckStatus.CHECKED
        req.updated_at = datetime.now()
        db.session.commit()
        flash('已标记为已核对', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'核对失败: {e}', 'danger')
    return redirect(url_for('reimbursement.list_requests'))
