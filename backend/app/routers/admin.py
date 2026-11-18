import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.audit_log import AuditLog
from backend.app.schemas.admin import AuditLogOut, RoleUpdate
from backend.app.schemas.auth import UserOut
from backend.app.security.auth import get_current_user, require_role

router = APIRouter(prefix="/api/admin", tags=["Administration & Audit"])


@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    out = []
    for l in logs:
        details = None
        if l.details_json:
            try:
                details = json.loads(l.details_json)
            except Exception:
                pass
        out.append(
            AuditLogOut(
                id=l.id,
                timestamp=l.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                event_type=l.event_type,
                user_email=l.user_email,
                ip_address=l.ip_address,
                action=l.action,
                status=l.status,
                details=details,
            )
        )
    return out


@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    new_role_str = role_update.role.upper().strip()
    if new_role_str not in [r.value for r in UserRole]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Allowed roles: {[r.value for r in UserRole]}",
        )

    target.role = UserRole(new_role_str)
    db.commit()
    db.refresh(target)
    return target

