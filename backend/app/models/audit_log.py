import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from backend.app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # LOGIN, REGISTER, MEDIA_VERIFY, MEDIA_REGISTER, AUTH_FAILURE, RATE_LIMIT
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    asset_id = Column(String(64), nullable=True)
    sha256 = Column(String(64), nullable=True)
    action = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)  # SUCCESS, FAILURE, WARNING
    details_json = Column(Text, nullable=True)

