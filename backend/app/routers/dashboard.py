import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models.verification import VerificationRecord
from backend.app.models.provenance import ProvenanceRecord
from backend.app.schemas.dashboard import DashboardSummary
from backend.app.security.keys import crypto_manager
from backend.app.services.ai_service import AIService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_verifications = db.query(func.count(VerificationRecord.id)).scalar() or 0
    ai_analyses_completed = (
        db.query(func.count(VerificationRecord.id))
        .filter(VerificationRecord.ai_status == "SUCCESS")
        .scalar()
        or 0
    )
    provenance_matched = (
        db.query(func.count(VerificationRecord.id))
        .filter(VerificationRecord.integrity_status == "MATCH")
        .scalar()
        or 0
    )
    integrity_mismatches = (
        db.query(func.count(VerificationRecord.id))
        .filter(VerificationRecord.integrity_status == "MISMATCH")
        .scalar()
        or 0
    )
    unregistered_count = (
        db.query(func.count(VerificationRecord.id))
        .filter(VerificationRecord.integrity_status == "NO_REFERENCE")
        .scalar()
        or 0
    )

    ai_ready, ai_info = AIService.is_available()
    crypto_ready = crypto_manager.get_private_key() is not None

    recent_recs = (
        db.query(VerificationRecord)
        .order_by(VerificationRecord.created_at.desc())
        .limit(10)
        .all()
    )
    recent_activity = [
        {
            "id": r.id,
            "filename": r.filename,
            "overall_status": r.overall_status,
            "trust_score": r.trust_score,
            "integrity_status": r.integrity_status,
            "ai_status": r.ai_status,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        for r in recent_recs
    ]

    try:
        from src.detector import resolve_model_info, DEFAULT_MODEL_KEY
        resolved_model_id = resolve_model_info(DEFAULT_MODEL_KEY)["model_id"]
    except Exception:
        resolved_model_id = "ai_detection_model"

    return DashboardSummary(
        total_verifications=total_verifications,
        ai_analyses_completed=ai_analyses_completed,
        provenance_matched=provenance_matched,
        integrity_mismatches=integrity_mismatches,
        unregistered_count=unregistered_count,
        model_ready=ai_ready,
        model_id=resolved_model_id,
        crypto_ready=crypto_ready,
        active_key_id=crypto_manager.active_key_id,
        recent_activity=recent_activity,
    )

