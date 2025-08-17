# app/views/monitor_views.py

import os
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, func

from app.extensions import db
from app.models.system_monitor import (
    SystemLog, SystemMetric, SystemAlert, HealthCheck,
    LogLevel, AlertLevel, AlertStatus
)
from app.utils.monitor import system_monitor, health_checker

monitor_bp = Blueprint('monitor', __name__, url_prefix='/monitor')


@monitor_bp.route('/')
@login_required
def dashboard():
    """监控仪表盘"""
    # 获取系统状态概览
    system_status = system_monitor.get_system_status()

    # 获取最近的告警
    recent_alerts = SystemAlert.query.filter_by(status=AlertStatus.OPEN) \
        .order_by(desc(SystemAlert.created_at)).limit(5).all()

    # 获取最近的错误日志
    recent_errors = SystemLog.query.filter(
        SystemLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
    ).order_by(desc(SystemLog.timestamp)).limit(10).all()

    return render_template('monitor/dashboard.html',
                           system_status=system_status,
                           recent_alerts=[alert.to_dict() for alert in recent_alerts],
                           recent_errors=[log.to_dict() for log in recent_errors])


@monitor_bp.route('/logs')
@login_required
def logs():
    """日志查看页面"""
    page = request.args.get('page', 1, type=int)
    level = request.args.get('level', '')
    logger_name = request.args.get('logger', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search = request.args.get('search', '')

    # 构建查询
    query = SystemLog.query

    if level:
        query = query.filter(SystemLog.level == LogLevel(level))

    if logger_name:
        query = query.filter(SystemLog.logger_name.like(f'%{logger_name}%'))

    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(SystemLog.timestamp >= start_dt)

    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(SystemLog.timestamp < end_dt)

    if search:
        query = query.filter(SystemLog.message.like(f'%{search}%'))

    # 分页查询
    logs_pagination = query.order_by(desc(SystemLog.timestamp)) \
        .paginate(page=page, per_page=50, error_out=False)

    # 获取日志级别统计
    level_stats = db.session.query(
        SystemLog.level, func.count(SystemLog.id).label('count')
    ).group_by(SystemLog.level).all()

    # 获取日志来源统计
    logger_stats = db.session.query(
        SystemLog.logger_name, func.count(SystemLog.id).label('count')
    ).group_by(SystemLog.logger_name).order_by(desc('count')).limit(10).all()

    return render_template('monitor/logs.html',
                           logs=logs_pagination,
                           level_stats=level_stats,
                           logger_stats=logger_stats,
                           current_filters={
                               'level': level,
                               'logger': logger_name,
                               'start_date': start_date,
                               'end_date': end_date,
                               'search': search
                           })


@monitor_bp.route('/metrics')
@login_required
def metrics():
    """系统指标页面"""
    metric_type = request.args.get('type', 'cpu_usage')
    hours = request.args.get('hours', 24, type=int)

    # 获取指定时间范围内的指标数据
    start_time = datetime.utcnow() - timedelta(hours=hours)
    metrics_data = SystemMetric.query.filter(
        SystemMetric.metric_name == metric_type,
        SystemMetric.timestamp >= start_time
    ).order_by(SystemMetric.timestamp).all()

    # 获取可用的指标类型
    available_metrics = db.session.query(SystemMetric.metric_name) \
        .distinct().all()

    return render_template('monitor/metrics.html',
                           metrics_data=[m.to_dict() for m in metrics_data],
                           available_metrics=[m[0] for m in available_metrics],
                           current_metric=metric_type,
                           current_hours=hours)


@monitor_bp.route('/alerts')
@login_required
def alerts():
    """告警管理页面"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    level = request.args.get('level', '')

    # 构建查询
    query = SystemAlert.query

    if status:
        query = query.filter(SystemAlert.status == AlertStatus(status))

    if level:
        query = query.filter(SystemAlert.level == AlertLevel(level))

    # 分页查询
    alerts_pagination = query.order_by(desc(SystemAlert.created_at)) \
        .paginate(page=page, per_page=20, error_out=False)

    return render_template('monitor/alerts.html',
                           alerts=alerts_pagination,
                           current_filters={
                               'status': status,
                               'level': level
                           })


@monitor_bp.route('/health')
@login_required
def health():
    """健康检查页面"""
    # 运行健康检查
    health_results = health_checker.run_all_checks()

    # 获取历史健康检查记录
    recent_checks = HealthCheck.query.order_by(desc(HealthCheck.timestamp)) \
        .limit(50).all()

    return render_template('monitor/health.html',
                           health_results=health_results,
                           recent_checks=[check.to_dict() for check in recent_checks])


# API 端点
@monitor_bp.route('/api/system-status')
@login_required
def api_system_status():
    """API: 获取系统状态"""
    return jsonify(system_monitor.get_system_status())


@monitor_bp.route('/api/metrics/<metric_name>')
@login_required
def api_metrics(metric_name):
    """API: 获取指定指标数据"""
    hours = request.args.get('hours', 1, type=int)
    start_time = datetime.utcnow() - timedelta(hours=hours)

    metrics = SystemMetric.query.filter(
        SystemMetric.metric_name == metric_name,
        SystemMetric.timestamp >= start_time
    ).order_by(SystemMetric.timestamp).all()

    return jsonify([m.to_dict() for m in metrics])


@monitor_bp.route('/api/logs/stream')
@login_required
def api_logs_stream():
    """API: 实时日志流"""
    last_id = request.args.get('last_id', 0, type=int)
    level = request.args.get('level', '')

    query = SystemLog.query.filter(SystemLog.id > last_id)

    if level:
        query = query.filter(SystemLog.level == LogLevel(level))

    new_logs = query.order_by(SystemLog.timestamp).limit(100).all()

    return jsonify({
        'logs': [log.to_dict() for log in new_logs],
        'last_id': new_logs[-1].id if new_logs else last_id
    })


@monitor_bp.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def api_acknowledge_alert(alert_id):
    """API: 确认告警"""
    alert = SystemAlert.query.get_or_404(alert_id)

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()

    db.session.commit()

    return jsonify({'success': True, 'message': '告警已确认'})


@monitor_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def api_resolve_alert(alert_id):
    """API: 解决告警"""
    alert = SystemAlert.query.get_or_404(alert_id)

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()

    db.session.commit()

    return jsonify({'success': True, 'message': '告警已解决'})


@monitor_bp.route('/api/health/check')
@login_required
def api_health_check():
    """API: 执行健康检查"""
    results = health_checker.run_all_checks()
    return jsonify(results)


@monitor_bp.route('/api/logs/export')
@login_required
def api_export_logs():
    """API: 导出日志"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    level = request.args.get('level')

    query = SystemLog.query

    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(SystemLog.timestamp >= start_dt)

    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(SystemLog.timestamp < end_dt)

    if level:
        query = query.filter(SystemLog.level == LogLevel(level))

    logs = query.order_by(desc(SystemLog.timestamp)).limit(10000).all()

    return jsonify({
        'logs': [log.to_dict() for log in logs],
        'total': len(logs)
    })


@monitor_bp.route('/logfiles')
@login_required
def logfiles():
    """日志文件查看页面"""
    return render_template('monitor/logfiles.html')


@monitor_bp.route('/api/logfiles/list')
@login_required
def api_logfiles_list():
    """API: 获取可用的日志文件列表"""
    import glob

    log_files = []

    # 根据环境判断日志路径
    is_production = current_app.config.get('ENV') == 'production'

    if is_production:
        # 生产环境 - Ubuntu 服务器路径 (MXStoreBI6)
        log_patterns = [
            # 项目应用日志
            '/var/www/MXStoreBI6/app.log*',
            '/var/www/MXStoreBI6/logs/*.log*',

            # Nginx 日志 (MXStoreBI6)
            '/var/log/nginx/access.log*',
            '/var/log/nginx/error.log*',
            '/var/log/nginx/mixuebi_access.log*',
            '/var/log/nginx/mixuebi_error.log*',

            # Supervisor 日志 (MXStoreBI6)
            '/var/log/supervisor/supervisord.log*',
            '/var/log/supervisor/MXStoreBI6.log*',
            '/var/log/supervisor/MXStoreBI6_stderr.log*',
            '/var/log/supervisor/MXStoreBI6_stdout.log*',

            # 系统日志
            '/var/log/syslog*',
            '/var/log/auth.log*',
            '/var/log/kern.log*',

            # MySQL 日志
            '/var/log/mysql/error.log*',
            '/var/log/mysql/mysql.log*',

            # 项目备份日志
            '/var/backups/MXStoreBI6/logs/*.log*',

            # UFW 防火墙日志
            '/var/log/ufw.log*',
        ]
    else:
        # 开发环境路径
        log_patterns = [
            # 应用根目录的日志文件
            'app.log*',
            'error.log*',
            'access.log*',
            'flask.log*',
            # logs目录下的日志文件
            'logs/*.log*',
            # 当前目录及子目录的所有log文件
            '**/*.log'
        ]

    for pattern in log_patterns:
        try:
            if pattern.startswith('/'):
                # 绝对路径
                files = glob.glob(pattern, recursive=True)
            else:
                # 相对路径，从应用根目录开始
                files = glob.glob(os.path.join(current_app.root_path, '..', pattern), recursive=True)

            for file_path in files:
                if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
                    file_info = os.stat(file_path)

                    # 判断日志类型
                    log_type = classify_log_file(file_path)

                    log_files.append({
                        'name': os.path.basename(file_path),
                        'path': file_path,
                        'size': file_info.st_size,
                        'size_human': format_file_size(file_info.st_size),
                        'modified': datetime.fromtimestamp(file_info.st_mtime).isoformat(),
                        'type': log_type,
                        'readable': True,
                        'environment': 'production' if is_production else 'development'
                    })
        except (OSError, PermissionError) as e:
            current_app.logger.debug(f"无法访问日志路径 {pattern}: {e}")
            continue

    # 去重（基于文件路径）
    unique_files = {}
    for file_info in log_files:
        unique_files[file_info['path']] = file_info

    # 按修改时间排序
    sorted_files = sorted(unique_files.values(), key=lambda x: x['modified'], reverse=True)

    return jsonify({'files': sorted_files})


def format_file_size(size_bytes):
    """格式化文件大小为人类可读格式"""
    if size_bytes == 0:
        return "0B"

    size_names = ['B', 'KB', 'MB', 'GB', 'TB']
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def classify_log_file(file_path):
    """根据文件路径和名称分类日志文件"""
    path_lower = file_path.lower()
    name_lower = os.path.basename(file_path).lower()

    # Ubuntu 生产环境特定分类
    if '/var/log/nginx/' in path_lower:
        if 'mixuebi' in name_lower:
            if 'access' in name_lower:
                return 'nginx-mixuebi-access'
            elif 'error' in name_lower:
                return 'nginx-mixuebi-error'
            else:
                return 'nginx-mixuebi'
        elif 'access' in name_lower:
            return 'nginx-access'
        elif 'error' in name_lower:
            return 'nginx-error'
        else:
            return 'nginx'
    elif '/var/log/supervisor/' in path_lower:
        if 'mxstorebi6' in name_lower or 'mixuebi' in name_lower:
            if 'stderr' in name_lower:
                return 'supervisor-app-error'
            elif 'stdout' in name_lower:
                return 'supervisor-app-output'
            else:
                return 'supervisor-app'
        elif 'supervisord' in name_lower:
            return 'supervisor-daemon'
        else:
            return 'supervisor'
    elif '/var/log/mysql/' in path_lower:
        if 'error' in name_lower:
            return 'mysql-error'
        else:
            return 'mysql'
    elif '/var/log/' in path_lower:
        if 'syslog' in name_lower:
            return 'system'
        elif 'auth' in name_lower:
            return 'auth'
        elif 'kern' in name_lower:
            return 'kernel'
        elif 'ufw' in name_lower:
            return 'firewall'
        else:
            return 'system'
    elif '/var/www/mxstorebi6/' in path_lower or 'app.log' in name_lower:
        return 'application'
    elif 'error' in name_lower:
        return 'error'
    elif 'access' in name_lower:
        return 'access'
    else:
        return 'general'


@monitor_bp.route('/api/logfiles/content')
@login_required
def api_logfile_content():
    """API: 获取日志文件内容"""
    import os

    file_path = request.args.get('path')
    lines = request.args.get('lines', 100, type=int)
    search = request.args.get('search', '')

    if not file_path:
        return jsonify({'error': '缺少文件路径参数'}), 400

    # 安全检查：确保文件路径是���全的
    if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
        return jsonify({'error': '文件不存在或无法访问'}), 404

    # 额外安全检查：确保是允许的日志文件路径
    allowed_paths = [
        '/var/log/',
        '/var/www/MXStoreBI6/',
        '/var/backups/MXStoreBI6/'
    ]

    # 在生产环境下进行路径安全检查
    if current_app.config.get('ENV') == 'production':
        if not any(file_path.startswith(path) for path in allowed_paths):
            return jsonify({'error': '不允许访问此路径的文件'}), 403

    try:
        content_lines = []
        encoding_tried = ['utf-8', 'latin1', 'cp1252']

        for encoding in encoding_tried:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    all_lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue
        else:
            # ��果所有编码都失败，使用二进制模式
            with open(file_path, 'rb') as f:
                content = f.read()
                all_lines = content.decode('utf-8', errors='replace').splitlines(True)

        # 如果有搜索条件，过滤行
        if search:
            filtered_lines = [line for line in all_lines if search.lower() in line.lower()]
        else:
            filtered_lines = all_lines

        # 获取最后N行
        recent_lines = filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines

        return jsonify({
            'content': recent_lines,
            'total_lines': len(all_lines),
            'filtered_lines': len(filtered_lines),
            'displayed_lines': len(recent_lines),
            'file_info': {
                'name': os.path.basename(file_path),
                'path': file_path,
                'size': os.path.getsize(file_path),
                'size_human': format_file_size(os.path.getsize(file_path)),
                'type': classify_log_file(file_path)
            }
        })

    except Exception as e:
        current_app.logger.error(f"读取日志文件失败 {file_path}: {str(e)}")
        return jsonify({'error': f'读取文件失败: {str(e)}'}), 500


@monitor_bp.route('/api/logfiles/tail')
@login_required
def api_logfile_tail():
    """API: 实时获取日志文件新内容"""
    import os

    file_path = request.args.get('path')
    last_size = request.args.get('last_size', 0, type=int)

    if not file_path or not os.path.isfile(file_path):
        return jsonify({'error': '文件不存在'}), 404

    # 安全检查
    if current_app.config.get('ENV') == 'production':
        allowed_paths = ['/var/log/', '/var/www/MXStoreBI6/', '/var/backups/MXStoreBI6/']
        if not any(file_path.startswith(path) for path in allowed_paths):
            return jsonify({'error': '不允许访问此路径的文件'}), 403

    try:
        current_size = os.path.getsize(file_path)

        if current_size <= last_size:
            return jsonify({
                'new_content': [],
                'current_size': current_size,
                'has_new_content': False
            })

        # 如果文件变小了，可能是日志轮转
        if current_size < last_size:
            last_size = 0

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_size)
            new_content = f.read()

        new_lines = new_content.split('\n')
        # 移除最后一个空行
        if new_lines and not new_lines[-1]:
            new_lines.pop()

        return jsonify({
            'new_content': new_lines,
            'current_size': current_size,
            'has_new_content': len(new_lines) > 0,
            'bytes_read': len(new_content)
        })

    except Exception as e:
        current_app.logger.error(f"尾随日志文件失败 {file_path}: {str(e)}")
        return jsonify({'error': f'读取文件失败: {str(e)}'}), 500


@monitor_bp.route('/api/logfiles/download')
@login_required
def api_logfile_download():
    """API: 下载日志文件"""
    import os
    from flask import send_file
    import tempfile
    import gzip

    file_path = request.args.get('path')
    compress = request.args.get('compress', 'false').lower() == 'true'

    if not file_path or not os.path.isfile(file_path):
        return jsonify({'error': '文件不存在'}), 404

    # 安全检查
    if current_app.config.get('ENV') == 'production':
        allowed_paths = ['/var/log/', '/var/www/MXStoreBI6/', '/var/backups/MXStoreBI6/']
        if not any(file_path.startswith(path) for path in allowed_paths):
            return jsonify({'error': '不允许访问此路径的文件'}), 403

    try:
        filename = os.path.basename(file_path)

        if compress:
            # 创建压缩文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gz') as temp_file:
                with open(file_path, 'rb') as source_file:
                    with gzip.open(temp_file.name, 'wb') as gz_file:
                        gz_file.write(source_file.read())

                response = send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=f"{filename}.gz",
                    mimetype='application/gzip'
                )

                # 在发送后删除临时文件
                @response.call_on_close
                def remove_temp_file():
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass

                return response
        else:
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='text/plain'
            )

    except Exception as e:
        current_app.logger.error(f"下载日志文件失败 {file_path}: {str(e)}")
        return jsonify({'error': f'下载文件失败: {str(e)}'}), 500


@monitor_bp.route('/system-info')
@login_required
def system_info():
    """系统信息页面"""
    import platform
    import psutil
    import sys
    import os
    from datetime import datetime

    # 收集系统信息
    system_data = {
        'platform': {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': sys.version,
            'architecture': platform.architecture()
        },
        'resources': {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used,
                'free': psutil.virtual_memory().free
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            }
        },
        'network': {
            'connections': len(psutil.net_connections()),
            'interfaces': list(psutil.net_if_addrs().keys())
        },
        'processes': {
            'total': len(psutil.pids()),
            'running': len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'running'])
        },
        'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        'current_time': datetime.now().isoformat()
    }

    # 应用信息
    app_info = {
        'flask_env': current_app.config.get('ENV'),
        'debug': current_app.config.get('DEBUG'),
        'database_uri': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').replace(
            current_app.config.get('DB_PASSWORD', ''), '***') if current_app.config.get(
            'SQLALCHEMY_DATABASE_URI') else None,
        'secret_key_set': bool(current_app.config.get('SECRET_KEY')),
        'monitoring_enabled': current_app.config.get('MONITORING_ENABLED', False),
        'project_path': '/var/www/MXStoreBI6' if current_app.config.get('ENV') == 'production' else os.getcwd()
    }

    return render_template('monitor/system_info.html',
                           system_data=system_data,
                           app_info=app_info)
