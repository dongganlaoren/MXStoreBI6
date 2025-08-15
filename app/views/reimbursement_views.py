import logging
import os
import traceback
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask import current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms.reimbursement_forms import ReimbursementCreateForm, ReimbursementApproveForm
from app.models.enums import ReimbursementAttachmentType
from app.models.enums import ReimbursementStatus
from app.models.reimbursement import ReimbursementRequest, ReimbursementAttachment
from app.models.user import User
from app.utils.lang_dict import lang_dict
from app.utils.notify import send_notify_mail

bp = Blueprint('reimbursement', __name__, url_prefix='/reimbursement')


@bp.route('/')
@login_required
def list_requests():
    # 获取筛选参数
    category = request.args.get('category', 'todo')  # todo, done, mine
    status = request.args.get('status', 'all')
    # 取消默认7天时间范围
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = ReimbursementRequest.query
    role = getattr(current_user.role, 'value', None)
    if role in ['BRANCH_MANAGER', 'EMPLOYEE', 'HEAD_MANAGER']:
        # 只能看自己发起的，全部记录，按时间倒序
        query = query.filter(ReimbursementRequest.submitter_id == current_user.user_id)
    elif role in ['FINANCE', 'ADMIN']:
        # 默认显示“待我审批”的（我为审批人且待审批），全部记录
        query = query.filter(
            ReimbursementRequest.approver_id == current_user.user_id,
            ReimbursementRequest.status == ReimbursementStatus.PENDING
        )
    # 状态过滤
    if status != 'all':
        query = query.filter(ReimbursementRequest.status == getattr(ReimbursementStatus, status))
    requests = query.order_by(ReimbursementRequest.created_at.desc()).all()

    # 优先从请求参数获取语言
    current_lang = request.args.get('lang') or getattr(current_user, 'language', 'zh')
    lang = lang_dict.get(current_lang, lang_dict['zh'])
    return render_template('reimbursement/list.html',
                           requests=requests,
                           category=category,
                           status=status,
                           time_range=None,
                           start_date=start_date,
                           end_date=end_date,
                           lang=lang,
                           current_lang=current_lang
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
            # 多文件保存
            files = form.attachments.data or []
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    # 防止重名，拼接request_id和时间戳
                    save_name = f"{req.request_id}_{int(datetime.utcnow().timestamp())}_{filename}"
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
                save_name = f"{req.request_id}_{int(datetime.utcnow().timestamp())}_{filename}"
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
    return render_template('reimbursement/approve.html', form=form, req=req)


@bp.route('/approver_search')
@login_required
def approver_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    users = User.query.filter(
        User.user_status == 1,
        User.role.in_(['ADMIN', 'FINANCE']),
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
    if submitter:
        query = query.join(User, ReimbursementRequest.submitter_id == User.user_id)
        query = query.filter(
            (User.username.like(f"%{submitter}%")) |
            (User.real_name.like(f"%{submitter}%")) |
            (User.employee_number.like(f"%{submitter}%"))
        )
    if approver:
        query = query.join(User, ReimbursementRequest.approver_id == User.user_id)
        query = query.filter(
            (User.username.like(f"%{approver}%")) |
            (User.real_name.like(f"%{approver}%")) |
            (User.employee_number.like(f"%{approver}%"))
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
            req.updated_at = datetime.utcnow()
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
