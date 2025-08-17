# app/utils/monitor.py

import logging
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any

import psutil
from flask import request, g, current_app
from flask_login import current_user
from sqlalchemy import desc

from app.extensions import db
from app.models.system_monitor import (
    SystemLog, SystemMetric, SystemAlert, HealthCheck,
    LogLevel, AlertLevel, AlertStatus
)


class DatabaseLogHandler(logging.Handler):
    """自定义日志处理器，将日志写入数据库"""

    def emit(self, record):
        try:
            from flask import has_app_context
            if not has_app_context():
                # 自动获取当前app并进入上下文
                from flask import current_app
                with current_app.app_context():
                    self._emit_with_context(record)
            else:
                self._emit_with_context(record)
        except Exception as e:
            print(f"数据库日志处理器错误: {e}")

    def _emit_with_context(self, record):
        # 获取请求上下文信息
        request_id = getattr(g, 'request_id', None)
        user_id = None
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')[:500]
        if current_user and hasattr(current_user, 'id') and current_user.is_authenticated:
            user_id = current_user.id
        # 创建系统日志记录
        log_entry = SystemLog(
            timestamp=datetime.fromtimestamp(record.created),
            level=LogLevel(record.levelname),
            logger_name=record.name,
            module=record.module if hasattr(record, 'module') else None,
            function_name=record.funcName,
            line_number=record.lineno,
            message=record.getMessage(),
            exception_info=self.format_exception(record) if record.exc_info else None,
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log_entry)
        db.session.commit()

    def format_exception(self, record):
        """格式化异常信息"""
        if record.exc_info:
            return ''.join(traceback.format_exception(*record.exc_info))
        return None


class SystemMonitor:
    """系统监控服务"""

    def __init__(self):
        self.alert_rules = self._load_alert_rules()

    def _load_alert_rules(self) -> Dict[str, Dict]:
        """加载告警规则配置"""
        return {
            'cpu_usage': {
                'threshold': 80.0,
                'level': AlertLevel.HIGH,
                'message': 'CPU使用率过高'
            },
            'memory_usage': {
                'threshold': 85.0,
                'level': AlertLevel.HIGH,
                'message': '内存使用率过高'
            },
            'disk_usage': {
                'threshold': 90.0,
                'level': AlertLevel.CRITICAL,
                'message': '磁盘使用率过高'
            },
            'error_rate': {
                'threshold': 5.0,  # 每分钟错误数
                'level': AlertLevel.MEDIUM,
                'message': '错误率过高'
            },
            'response_time': {
                'threshold': 3000.0,  # 毫秒
                'level': AlertLevel.MEDIUM,
                'message': '响应时间过长'
            }
        }

    def collect_system_metrics(self):
        """收集系统指标（仅生产环境启用）"""
        from flask import has_app_context, current_app
        # 环境保护：仅生产环境且MONITORING_ENABLED为True时才执行
        env = current_app.config.get('ENV', 'development')
        monitoring_enabled = current_app.config.get('MONITORING_ENABLED', True)
        if env != 'production' or not monitoring_enabled:
            current_app.logger.info(f"跳过系统指标收集（当前环境: {env}, MONITORING_ENABLED: {monitoring_enabled}）")
            return
        try:
            if not has_app_context():
                with current_app.app_context():
                    self._collect_system_metrics_with_context()
            else:
                self._collect_system_metrics_with_context()
        except Exception as e:
            current_app.logger.error(f"收集系统指标失败: {e}")

    def _collect_system_metrics_with_context(self):
        now = datetime.utcnow()
        metrics = []

        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(SystemMetric(
            timestamp=now,
            metric_name='cpu_usage',
            metric_value=cpu_percent,
            metric_unit='percent'
        ))

        # 内存使用率
        memory = psutil.virtual_memory()
        metrics.append(SystemMetric(
            timestamp=now,
            metric_name='memory_usage',
            metric_value=memory.percent,
            metric_unit='percent'
        ))

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        metrics.append(SystemMetric(
            timestamp=now,
            metric_name='disk_usage',
            metric_value=disk_percent,
            metric_unit='percent'
        ))

        # 网络连接数
        connections = len(psutil.net_connections())
        metrics.append(SystemMetric(
            timestamp=now,
            metric_name='network_connections',
            metric_value=connections,
            metric_unit='count'
        ))

        # 进程数
        process_count = len(psutil.pids())
        metrics.append(SystemMetric(
            timestamp=now,
            metric_name='process_count',
            metric_value=process_count,
            metric_unit='count'
        ))

        # 批量保存指标
        db.session.add_all(metrics)
        db.session.commit()

        # 检查告警条件
        self._check_alert_conditions(metrics)

    def _check_alert_conditions(self, metrics: List[SystemMetric]):
        """检查告警条件"""
        for metric in metrics:
            rule = self.alert_rules.get(metric.metric_name)
            if not rule:
                continue

            if metric.metric_value > rule['threshold']:
                # 检查是否已有相同类型的未解决告警
                existing_alert = SystemAlert.query.filter_by(
                    alert_type=metric.metric_name,
                    status=AlertStatus.OPEN
                ).first()

                if not existing_alert:
                    alert = SystemAlert(
                        alert_type=metric.metric_name,
                        level=rule['level'],
                        title=f"{rule['message']}: {metric.metric_value}{metric.metric_unit}",
                        description=f"指标 {metric.metric_name} 超过阈值 {rule['threshold']}{metric.metric_unit}",
                        source_data={
                            'metric_id': metric.id,
                            'current_value': metric.metric_value,
                            'threshold': rule['threshold']
                        }
                    )
                    db.session.add(alert)
                    db.session.commit()

                    # 发送告警通知
                    self._send_alert_notification(alert)

    def _send_alert_notification(self, alert: SystemAlert):
        """发送告警通知"""
        try:
            # 这里可以集成邮件、短信、钉钉等通知方式
            current_app.logger.warning(f"系统告警: {alert.title}")
            # TODO: 实现具体的通知逻辑
        except Exception as e:
            current_app.logger.error(f"发送告警通知失败: {e}")

    def get_error_rate(self, minutes: int = 5) -> float:
        """获取指定时间内的错误率"""
        start_time = datetime.utcnow() - timedelta(minutes=minutes)

        error_count = SystemLog.query.filter(
            SystemLog.timestamp >= start_time,
            SystemLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
        ).count()

        return error_count / minutes  # 每分钟错误数

    def get_latest_metrics(self, metric_names: List[str] = None, limit: int = 100) -> List[Dict]:
        """获取最新的系统指标"""
        query = SystemMetric.query

        if metric_names:
            query = query.filter(SystemMetric.metric_name.in_(metric_names))

        metrics = query.order_by(desc(SystemMetric.timestamp)).limit(limit).all()
        return [metric.to_dict() for metric in metrics]

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统整体状态"""
        # 获取最新指标
        latest_metrics = {}
        for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
            metric = SystemMetric.query.filter_by(metric_name=metric_name) \
                .order_by(desc(SystemMetric.timestamp)).first()
            if metric:
                latest_metrics[metric_name] = metric.metric_value

        # 获取未解决告警数量
        open_alerts_count = SystemAlert.query.filter_by(status=AlertStatus.OPEN).count()

        # 获取最近错误数量
        recent_errors = self.get_error_rate(minutes=5)

        return {
            'metrics': latest_metrics,
            'open_alerts': open_alerts_count,
            'error_rate': recent_errors,
            'status': 'healthy' if open_alerts_count == 0 and recent_errors < 1 else 'warning'
        }


class HealthChecker:
    """健康检查服务"""

    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'disk_space': self._check_disk_space,
            'memory': self._check_memory,
            'external_api': self._check_external_api,
            'nginx': self._check_nginx_status,
            'supervisor': self._check_supervisor_status,
            'mysql': self._check_mysql_status
        }

    def run_all_checks(self) -> Dict[str, Dict]:
        from flask import has_app_context, current_app
        results = {}
        try:
            if not has_app_context():
                with current_app.app_context():
                    results = self._run_all_checks_with_context()
            else:
                results = self._run_all_checks_with_context()
        except Exception as e:
            current_app.logger.error(f"健康检查任务失败: {e}")
        return results

    def _run_all_checks_with_context(self) -> Dict[str, Dict]:
        results = {}
        for check_name, check_func in self.checks.items():
            start_time = time.time()
            try:
                result = check_func()
                response_time = (time.time() - start_time) * 1000  # 毫秒
                health_check = HealthCheck(
                    check_name=check_name,
                    status=result['status'],
                    response_time=response_time,
                    details=result.get('details', {})
                )
                db.session.add(health_check)
                results[check_name] = {
                    'status': result['status'],
                    'response_time': response_time,
                    'details': result.get('details', {}),
                    'message': result.get('message', '')
                }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                health_check = HealthCheck(
                    check_name=check_name,
                    status='ERROR',
                    response_time=response_time,
                    details={'error': str(e)}
                )
                db.session.add(health_check)
                results[check_name] = {
                    'status': 'ERROR',
                    'response_time': response_time,
                    'details': {'error': str(e)},
                    'message': f'检查失败: {str(e)}'
                }
        try:
            db.session.commit()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"保存健康检查结果失败: {e}")
        return results

    def _check_database(self) -> Dict:
        """检查数据库连接"""
        try:
            # 执行简单查询测试数据库连接
            db.session.execute('SELECT 1')
            return {
                'status': 'OK',
                'message': '数据库连接正常'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'数据库连接失败: {str(e)}'
            }

    def _check_disk_space(self) -> Dict:
        """检查磁盘空间"""
        try:
            disk = psutil.disk_usage('/')
            free_percent = (disk.free / disk.total) * 100

            if free_percent < 10:
                status = 'ERROR'
                message = f'磁盘空间严重不足: {free_percent:.1f}%'
            elif free_percent < 20:
                status = 'WARNING'
                message = f'磁盘空间不足: {free_percent:.1f}%'
            else:
                status = 'OK'
                message = f'磁盘空间充足: {free_percent:.1f}%'

            return {
                'status': status,
                'message': message,
                'details': {
                    'free_percent': free_percent,
                    'free_gb': disk.free / (1024 ** 3),
                    'total_gb': disk.total / (1024 ** 3)
                }
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'磁盘检查失败: {str(e)}'
            }

    def _check_memory(self) -> Dict:
        """检查内存使用"""
        try:
            memory = psutil.virtual_memory()

            if memory.percent > 90:
                status = 'ERROR'
                message = f'内存使用率过高: {memory.percent:.1f}%'
            elif memory.percent > 80:
                status = 'WARNING'
                message = f'内存使用率较高: {memory.percent:.1f}%'
            else:
                status = 'OK'
                message = f'内存使用正常: {memory.percent:.1f}%'

            return {
                'status': status,
                'message': message,
                'details': {
                    'percent': memory.percent,
                    'available_gb': memory.available / (1024 ** 3),
                    'total_gb': memory.total / (1024 ** 3)
                }
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'内存检查失败: {str(e)}'
            }

    def _check_external_api(self) -> Dict:
        """检查外��API连接"""
        # 这里可以添加对外部服务的检查
        return {
            'status': 'OK',
            'message': '外部API连接正常'
        }

    def _check_nginx_status(self) -> Dict:
        """检查Nginx服务状态"""
        try:
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'nginx'],
                                    capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip() == 'active':
                return {
                    'status': 'OK',
                    'message': 'Nginx服务运行正常'
                }
            else:
                return {
                    'status': 'ERROR',
                    'message': f'Nginx服务异常: {result.stdout.strip()}'
                }
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'Nginx状态检查超时'
            }
        except FileNotFoundError:
            return {
                'status': 'WARNING',
                'message': 'systemctl命令不可用，可能不是systemd系统'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Nginx检查失败: {str(e)}'
            }

    def _check_supervisor_status(self) -> Dict:
        """检查Supervisor服务状态"""
        try:
            import subprocess
            # 检查supervisor服务状态
            result = subprocess.run(['systemctl', 'is-active', 'supervisor'],
                                    capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip() == 'active':
                # 进一步检查应用进程状态
                app_result = subprocess.run(['supervisorctl', 'status'],
                                            capture_output=True, text=True, timeout=5)

                running_processes = []
                stopped_processes = []

                if app_result.returncode == 0:
                    for line in app_result.stdout.strip().split('\n'):
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 2:
                                process_name = parts[0]
                                status = parts[1]
                                if status == 'RUNNING':
                                    running_processes.append(process_name)
                                else:
                                    stopped_processes.append(f"{process_name}({status})")  # 修复语法错误

                if stopped_processes:
                    return {
                        'status': 'WARNING',
                        'message': f'Supervisor运行正常，但有进程异常: {", ".join(stopped_processes)}',
                        'details': {
                            'running': running_processes,
                            'stopped': stopped_processes
                        }
                    }
                else:
                    return {
                        'status': 'OK',
                        'message': f'Supervisor运行正常，{len(running_processes)}个进程运行中',
                        'details': {
                            'running': running_processes,
                            'stopped': []
                        }
                    }
            else:
                return {
                    'status': 'ERROR',
                    'message': f'Supervisor服务异常: {result.stdout.strip()}'
                }
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'Supervisor状态检查超时'
            }
        except FileNotFoundError:
            return {
                'status': 'WARNING',
                'message': 'supervisorctl命令不可用'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Supervisor检查失败: {str(e)}'
            }

    def _check_mysql_status(self) -> Dict:
        """检查MySQL服务状态"""
        try:
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'mysql'],
                                    capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip() == 'active':
                # 进一步检查MySQL连接
                try:
                    # 这里复用数据库连接检查
                    db_check = self._check_database()
                    if db_check['status'] == 'OK':
                        return {
                            'status': 'OK',
                            'message': 'MySQL服务运行正常且数据库连接正常'
                        }
                    else:
                        return {
                            'status': 'WARNING',
                            'message': 'MySQL服务运行但数据库��接异常',
                            'details': db_check
                        }
                except Exception:
                    return {
                        'status': 'WARNING',
                        'message': 'MySQL服务运行但连接检查失败'
                    }
            else:
                return {
                    'status': 'ERROR',
                    'message': f'MySQL服务异常: {result.stdout.strip()}'
                }
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'MySQL状态检查超时'
            }
        except FileNotFoundError:
            return {
                'status': 'WARNING',
                'message': 'systemctl命令不可用，可能不是systemd系统'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'MySQL检���失败: {str(e)}'
            }


def generate_request_id():
    """生成请求ID"""
    return str(uuid.uuid4())


def setup_request_logging(app):
    """设置请求日志记录"""

    @app.before_request
    def before_request():
        g.request_id = generate_request_id()
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            response_time = (time.time() - g.start_time) * 1000
            app.logger.info(
                f"请求完成 - 方法: {request.method}, "
                f"路径: {request.path}, "
                f"状态码: {response.status_code}, "
                f"响应时间: {response_time:.2f}ms, "
                f"请求ID: {getattr(g, 'request_id', 'unknown')}"
            )
        return response


# 创建全局监控实例
system_monitor = SystemMonitor()
health_checker = HealthChecker()
