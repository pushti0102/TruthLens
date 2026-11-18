import json
import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        action: str,
        status: str = "SUCCESS",
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        asset_id: Optional[str] = None,
        sha256: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        try:
            entry = AuditLog(
                timestamp=datetime.datetime.utcnow(),
                event_type=event_type,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
                asset_id=asset_id,
                sha256=sha256,
                action=action,
                status=status,
                details_json=json.dumps(details) if details else None,
            )
            db.add(entry)
            db.commit()
            return entry
        except Exception as e:
            # Audit logging must not crash main application request
            print(f"[!] Warning: Audit log failed: {e}")
            return None

