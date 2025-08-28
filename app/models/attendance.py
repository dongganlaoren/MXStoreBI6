# app/models/attendance.py
from datetime import datetime
from typing import Optional

from app.extensions import db
from .enums import AttendanceAction, AttendanceSource


class AttendanceRecord(db.Model):
    """
    员工考勤打卡记录
    - 关联用户，可选关联店铺
    - 支持上/下班、来源（WEB/LINE/API）
    - 可选位置与照片
    """
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    store_id = db.Column(db.String(32), db.ForeignKey('stores.store_id'), nullable=True, index=True)

    action = db.Column(db.Enum(AttendanceAction), nullable=False)
    source = db.Column(db.Enum(AttendanceSource), nullable=False, default=AttendanceSource.WEB)

    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_name = db.Column(db.String(255), nullable=True)

    photo_path = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'store_id': self.store_id,
            'action': self.action.value if self.action else None,
            'source': self.source.value if self.source else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_name': self.location_name,
            'photo_path': self.photo_path,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create(
            *,
            user_id: int,
            store_id: Optional[str],
            action: AttendanceAction,
            source: AttendanceSource,
            timestamp: Optional[datetime] = None,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            location_name: Optional[str] = None,
            photo_path: Optional[str] = None,
            notes: Optional[str] = None,
    ):
        rec = AttendanceRecord(
            user_id=user_id,
            store_id=store_id,
            action=action,
            source=source,
            timestamp=timestamp or datetime.now(),
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            photo_path=photo_path,
            notes=notes,
        )
        db.session.add(rec)
        return rec
