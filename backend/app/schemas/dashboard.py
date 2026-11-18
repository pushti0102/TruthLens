from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_verifications: int
    ai_analyses_completed: int
    provenance_matched: int
    integrity_mismatches: int
    unregistered_count: int
    model_ready: bool
    model_id: str
    crypto_ready: bool
    active_key_id: str
    recent_activity: List[Dict[str, Any]]

