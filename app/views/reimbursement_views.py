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
from datetime import datetime

bp = Blueprint('reimbursement', __name__, url_prefix='/reimbursement')

@bp.route('/')
@login_required
def list_requests():
    # 我的申请和待我审批的申请
    my_requests = ReimbursementRequest.query.filter_by(submitter_id=current_user.user_id).order_by(ReimbursementRequest.created_at.desc()).all()
    to_approve = ReimbursementRequest.query.filter_by(approver_id=current_user.user_id, status=ReimbursementStatus.PENDING).order_by(ReimbursementRequest.created_at.desc()).all()
    return render_template('reimbursement/list.html', my_requests=my_requests, to_approve=to_approve)

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
                description=form.reason.data,  # 保证字段一致
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
        req.status = ReimbursementStatus.APPROVED
        req.approval_comments = form.approval_comments.data
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
