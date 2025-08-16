from app.extensions import db
from app.models.enums import RoleType


class EmailReportConfig(db.Model):
    __tablename__ = 'email_report_config'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role = db.Column(db.Enum(RoleType), nullable=False, unique=True, comment='角色')
    daily_enabled = db.Column(db.Boolean, default=True, nullable=False)
    weekly_enabled = db.Column(db.Boolean, default=True, nullable=False)
    monthly_enabled = db.Column(db.Boolean, default=True, nullable=False)
    daily_time = db.Column(db.String(8), default='16:00', nullable=False)
    weekly_time = db.Column(db.String(8), default='09:00', nullable=False)
    monthly_time = db.Column(db.String(8), default='09:00', nullable=False)
    weekly_day = db.Column(db.String(2), default='1', nullable=False)
    monthly_day = db.Column(db.String(2), default='1', nullable=False)
    emails = db.Column(db.Text, default='', nullable=True)

    def to_dict(self):
        return {
            'emails': self.emails or '',
            'daily_enabled': self.daily_enabled,
            'weekly_enabled': self.weekly_enabled,
            'monthly_enabled': self.monthly_enabled,
            'daily_time': self.daily_time,
            'weekly_time': self.weekly_time,
            'monthly_time': self.monthly_time,
            'weekly_day': self.weekly_day,
            'monthly_day': self.monthly_day,
        }
