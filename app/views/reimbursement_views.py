from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.forms.reimbursement_forms import ReimbursementCreateForm, ReimbursementApproveForm
from app.models.reimbursement import ReimbursementRequest, ReimbursementAttachment
from app.extensions import db
from app.models.enums import ReimbursementStatus
from app.models.user import User
from sqlalchemy import or_
import logging
import traceback
import os
from werkzeug.utils import secure_filename
from app.models.enums import ReimbursementAttachmentType
from flask import current_app
from datetime import datetime, timedelta

bp = Blueprint('reimbursement', __name__, url_prefix='/reimbursement')

@bp.route('/')
@login_required
def list_requests():
    # 获取筛选参数
    category = request.args.get('category', 'todo')  # todo, done, mine
    status = request.args.get('status', 'all')
    time_range = request.args.get('time_range', '7d')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # 时间范围处理
    now = datetime.now()
    if time_range == '24h':
        begin = now - timedelta(hours=24)
        end = now
    elif time_range == '7d':
        begin = now - timedelta(days=7)
        end = now
    elif time_range == '30d':
        begin = now - timedelta(days=30)
        end = now
    elif time_range == 'custom' and start_date and end_date:
        try:
            begin = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        except Exception:
            begin = now - timedelta(days=7)
            end = now
    else:
        begin = now - timedelta(days=7)
        end = now

    # 查询条件
    query = ReimbursementRequest.query
    if category == 'todo':
        query = query.filter(ReimbursementRequest.approver_id == current_user.user_id)
    elif category == 'done':
        query = query.filter(ReimbursementRequest.approver_id == current_user.user_id)
        query = query.filter(ReimbursementRequest.status == ReimbursementStatus.APPROVED)
    else:  # mine
        query = query.filter(ReimbursementRequest.submitter_id == current_user.user_id)
    if status != 'all':
        query = query.filter(ReimbursementRequest.status == getattr(ReimbursementStatus, status))
    query = query.filter(ReimbursementRequest.created_at >= begin, ReimbursementRequest.created_at < end)
    requests = query.order_by(ReimbursementRequest.created_at.desc()).all()

    return render_template('reimbursement/list.html',
        requests=requests,
        category=category,
        status=status,
        time_range=time_range,
        start_date=start_date,
        end_date=end_date
    )

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ReimbursementCreateForm()
    if form.validate_on_submit():
        try:
            # 类型转换，确保与模型一致
            store_id = form.store_id.data or None
            approver_id = int(form.approver_id.data) if form.approver_id.data else None
            req = ReimbursementRequest(
                primary_category=form.primary_category.data,
                secondary_category=form.secondary_category.data,
                store_id=store_id,
                description=form.reason.data,  # 保证字段一致，模型字段为description
                amount=form.amount.data,
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
            flash('报销申请已提交', 'success')
            return redirect(url_for('reimbursement.list_requests'))
        except Exception as e:
            db.session.rollback()
            logging.exception(f"报销申请保存失败: {e}")  # 输出完整堆栈
            print(traceback.format_exc())  # 控制台输出异常
            flash(f'保存失败: {e}', 'danger')
    else:
        print("表单校验失败:", form.errors)
    return render_template('reimbursement/create.html', form=form)

@bp.route('/<int:request_id>')
@login_required
def detail(request_id):
    req = ReimbursementRequest.query.get_or_404(request_id)
    attachments = req.attachments.all()
    return render_template('reimbursement/detail.html', req=req, attachments=attachments)

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
    if not (current_user.is_authenticated and current_user.username == 'admin' and getattr(current_user.role, 'name', None) == 'ADMIN'):
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
