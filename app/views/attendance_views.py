# app/views/attendance_views.py
import os
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db, csrf
from app.forms.attendance_forms import AttendancePunchForm
from app.models import AttendanceRecord, User
from app.models.enums import AttendanceAction, AttendanceSource, RoleType

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


# --- helpers ---

def _save_photo(file: Optional[FileStorage], user_id: int) -> Optional[str]:
    if not file or file.filename == '':
        return None
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        raise ValueError('不支持的图片类型')
    # 构建存储路径: app/static/uploads/attendance/{user_id}/{YYYYMMDD}/{uuid}{ext}
    base_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    date_folder = datetime.now().strftime('%Y%m%d')
    rel_dir = os.path.join('attendance', str(user_id), date_folder)
    abs_dir = os.path.join(base_folder, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(abs_dir, fname)
    file.save(abs_path)
    # 返回相对路径（相对 static 根目录），以便模板直接展示
    # 如果 UPLOAD_FOLDER 以 app/static 开头，则去掉前缀
    prefix = 'app/static/'
    if base_folder.startswith(prefix):
        return os.path.join(base_folder[len(prefix):], rel_dir, fname)
    # 否则返回相对项目根的路径
    return os.path.join(base_folder, rel_dir, fname)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None


def _daterange_days(start: date, end: date) -> Tuple[datetime, datetime]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    return start_dt, end_dt


def compute_attendance_days(user_id: int, start_d: date, end_d: date) -> Dict:
    """
    规则：按自然日汇总，同一天内：取最早 CLOCK_IN 与最晚 CLOCK_OUT 计算跨度，>= 9 小时记 1 天。
    缺少成对打卡视为 0 小时。仅统计 [start_d, end_d] 区间。
    返回：{"total_days": int, "details": [{"date": 'YYYY-MM-DD', "hours": float, "is_count": bool}]}
    """
    start_dt, end_dt = _daterange_days(start_d, end_d)
    # 拉取区间内该用户的打卡
    recs: List[AttendanceRecord] = (
        AttendanceRecord.query
        .filter(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.timestamp >= start_dt,
            AttendanceRecord.timestamp <= end_dt,
        )
        .order_by(AttendanceRecord.timestamp.asc())
        .all()
    )
    # 按日期归组
    per_day: Dict[date, List[AttendanceRecord]] = {}
    for r in recs:
        d = r.timestamp.date()
        per_day.setdefault(d, []).append(r)

    details = []
    total_days = 0
    cur = start_d
    while cur <= end_d:
        day_recs = per_day.get(cur, [])
        # 找最早CLOCK_IN与最晚CLOCK_OUT
        earliest_in = None
        latest_out = None
        for r in day_recs:
            if r.action == AttendanceAction.CLOCK_IN:
                if earliest_in is None or r.timestamp < earliest_in:
                    earliest_in = r.timestamp
            elif r.action == AttendanceAction.CLOCK_OUT:
                if latest_out is None or r.timestamp > latest_out:
                    latest_out = r.timestamp
        hours = 0.0
        counted = False
        if earliest_in and latest_out and latest_out > earliest_in:
            delta = latest_out - earliest_in
            hours = round(delta.total_seconds() / 3600.0, 2)
            counted = hours >= 9.0
        if counted:
            total_days += 1
        details.append({
            'date': cur.strftime('%Y-%m-%d'),
            'hours': hours,
            'is_count': counted,
        })
        cur += timedelta(days=1)

    return {'total_days': total_days, 'details': details}


# --- Web 页面：打卡 ---
@attendance_bp.route('/punch', methods=['GET', 'POST'])
@login_required
def punch():
    form = AttendancePunchForm()
    if form.validate_on_submit():
        try:
            action = AttendanceAction(form.action.data)
        except ValueError:
            flash('打卡类型无效', 'danger')
            return render_template('attendance/punch.html', form=form)
        lat = request.form.get('latitude') or form.latitude.data or None
        lng = request.form.get('longitude') or form.longitude.data or None
        try:
            lat = float(lat) if lat not in (None, '') else None
            lng = float(lng) if lng not in (None, '') else None
        except Exception:
            lat, lng = None, None
        try:
            photo_path = _save_photo(form.photo.data, current_user.user_id)
        except Exception as e:
            current_app.logger.warning(f'保存考勤照片失败: {e}')
            flash('图片保存失败，请重试或更换图片', 'warning')
            photo_path = None

        rec = AttendanceRecord.create(
            user_id=current_user.user_id,
            store_id=getattr(current_user, 'store_id', None),
            action=action,
            source=AttendanceSource.WEB,
            timestamp=datetime.now(),
            latitude=lat,
            longitude=lng,
            location_name=form.location_name.data or None,
            photo_path=photo_path,
            notes=form.notes.data or None,
        )
        db.session.commit()
        flash('打卡成功', 'success')
        return redirect(url_for('attendance.records'))

    return render_template('attendance/punch.html', form=form)


# --- Web 页面：记录列表 ---
@attendance_bp.route('/records')
@login_required
def records():
    page = int(request.args.get('page', 1))
    per_page = current_app.config.get('RECORDS_PER_PAGE', 20)

    q = AttendanceRecord.query
    # 管理组可查看全部，门店组仅查看自己的
    if current_user.role in (RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER):
        q = q.filter(AttendanceRecord.user_id == current_user.user_id)
    else:
        # 可选按用户过滤
        user_id = request.args.get('user_id')
        if user_id:
            try:
                q = q.filter(AttendanceRecord.user_id == int(user_id))
            except Exception:
                pass
    q = q.order_by(AttendanceRecord.timestamp.desc())
    pager = q.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('attendance/records.html', pager=pager)


# --- Web 页面：出勤天数查询 ---
@attendance_bp.route('/days', methods=['GET'])
@login_required
def days_page():
    # 默认当月
    today = date.today()
    start_d = date(today.year, today.month, 1)
    end_d = today
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')
    q_user_id = request.args.get('user_id')

    sd = _parse_date(start_str) or start_d
    ed = _parse_date(end_str) or end_d
    if ed < sd:
        sd, ed = ed, sd

    # 权限：门店组只能看自己
    if current_user.role in (RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER):
        uid = current_user.user_id
    else:
        uid = None
        if q_user_id:
            try:
                uid = int(q_user_id)
            except Exception:
                uid = None
        if uid is None:
            uid = current_user.user_id

    result = compute_attendance_days(uid, sd, ed)

    return render_template(
        'attendance/days.html',
        start_date=sd.strftime('%Y-%m-%d'),
        end_date=ed.strftime('%Y-%m-%d'),
        user_id=uid,
        result=result,
    )


# --- API：供 LINE 或外部调用打卡 ---
@attendance_bp.route('/api/punch', methods=['POST'])
@csrf.exempt
def api_punch():
    data = request.get_json(silent=True) or {}
    # 识别用户：优先 user_id，其次 line_id
    user: Optional[User] = None
    user_id = data.get('user_id')
    line_id = data.get('line_id')
    if user_id:
        user = User.query.filter_by(user_id=int(user_id)).first()
    elif line_id:
        user = User.query.filter_by(line_id=line_id).first()
        if not user:
            return jsonify({'ok': False, 'error': '请完善Mira信息'}), 404
    if not user:
        return jsonify({'ok': False, 'error': '用户不存在'}), 404

    action_str = data.get('action', 'CLOCK_IN')
    try:
        action = AttendanceAction(action_str)
    except ValueError:
        return jsonify({'ok': False, 'error': 'action 无效'}), 400

    ts_str = data.get('timestamp')
    ts = None
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            pass

    lat = data.get('latitude')
    lng = data.get('longitude')
    try:
        lat = float(lat) if lat is not None else None
        lng = float(lng) if lng is not None else None
    except Exception:
        lat, lng = None, None

    # 此 API 暂不支持图片上传，若需要可后续扩展 multipart/form-data
    rec = AttendanceRecord.create(
        user_id=user.user_id,
        store_id=getattr(user, 'store_id', None),
        action=action,
        source=AttendanceSource.LINE if line_id else AttendanceSource.API,
        timestamp=ts or datetime.now(),
        latitude=lat,
        longitude=lng,
        location_name=data.get('location_name'),
        photo_path=None,
        notes=data.get('notes'),
    )
    db.session.commit()
    # 返回员工编号+上班/下班打卡成功（中泰双语）
    if action == AttendanceAction.CLOCK_IN:
        action_text_cn = '上班'
        action_text_th = 'เข้างาน'
    else:
        action_text_cn = '下班'
        action_text_th = 'ออกงาน'
    msg = f'{user.employee_number}{action_text_cn}打卡成功 {action_text_th}บันทึกสำเร็จ'
    return jsonify({'ok': True, 'msg': msg, 'data': rec.to_dict()})


# --- API：出勤天数查询 ---
@attendance_bp.route('/api/days', methods=['GET', 'POST'])
@csrf.exempt
def api_days():
    # 支持 JSON 或 querystring
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id') or request.args.get('user_id')
    start_date_s = payload.get('start_date') or request.args.get('start_date')
    end_date_s = payload.get('end_date') or request.args.get('end_date')

    # 权限：门店组只能查自己
    if current_user.is_authenticated and current_user.role in (RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER):
        uid = current_user.user_id
    else:
        try:
            uid = int(user_id) if user_id is not None else None
        except Exception:
            uid = None
        if uid is None and current_user.is_authenticated:
            uid = current_user.user_id
    if uid is None:
        return jsonify({'ok': False, 'error': 'user_id 必填或请先登录'}), 400

    sd = _parse_date(start_date_s)
    ed = _parse_date(end_date_s)
    if sd is None or ed is None:
        # 默认当月
        today = date.today()
        sd = sd or date(today.year, today.month, 1)
        ed = ed or today
    if ed < sd:
        sd, ed = ed, sd

    data = compute_attendance_days(uid, sd, ed)
    return jsonify({'ok': True, 'data': data})


# --- API：测试页面 ---
@attendance_bp.route('/api_test', methods=['GET'])
def api_test_page():
    return render_template('attendance/api_test.html')
