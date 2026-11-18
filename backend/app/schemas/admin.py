from typing import Optional, Dict, Any
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    timestamp: str
    event_type: str
    user_email: Optional[str] = None
    ip_address: Optional[str] = None
    action: str
    status: str
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    role: str

