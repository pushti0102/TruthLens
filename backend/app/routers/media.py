import json
import time
import datetime
import uuid
from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.verification import VerificationRecord
from backend.app.schemas.verification import (
    VerificationReport,
    VerificationHistoryItem,
    IntegrityDetail,
    SignatureDetail,
    AIDetail,
    TrustAssessmentDetail,
)
from backend.app.security.auth import get_current_user_optional, get_current_user
from backend.app.services.ai_service import AIService
from backend.app.services.crypto_service import CryptoService
from backend.app.services.trust_engine import TrustAssessmentEngine
from backend.app.services.audit_service import AuditService

from member2_security.security.upload_validation import (
    validate_image_bytes,
    save_validated_upload,
    UploadValidationResult,
)
from member2_security.security.rate_limiting import RateLimitDependency

router = APIRouter(prefix="/api/media", tags=["Media Verification"])


@router.post(
    "/verify",
    response_model=VerificationReport,
    dependencies=[Depends(RateLimitDependency(settings.RATE_LIMIT_ANALYSIS, tag="verify"))],
)
async def verify_media(
    request: Request,
    file: UploadFile = File(...),
    asset_id: Optional[str] = Form(None),
    model: Optional[str] = Form("current"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    start_time = time.time()
    raw_bytes = await file.read()

    # 1. OWASP-compliant upload validation
    validation: UploadValidationResult = validate_image_bytes(
        file_bytes=raw_bytes,
        original_filename=file.filename,
        max_file_size=settings.MAX_UPLOAD_BYTES,
        max_pixels=settings.MAX_UPLOAD_PIXELS,
        max_width=settings.MAX_WIDTH,
        max_height=settings.MAX_HEIGHT,
    )

    if not validation.valid:
        AuditService.log_event(
            db,
            event_type="UPLOAD_REJECTED",
            action="Invalid media upload attempt",
            status="FAILURE",
            user_id=current_user.id if current_user else None,
            user_email=current_user.email if current_user else None,
            ip_address=request.client.host if request.client else None,
            details={"filename": file.filename, "error": validation.error_message, "code": validation.error_code},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": validation.error_code or "VALIDATION_ERROR",
                "message": validation.error_message or "Unsupported or corrupt image file.",
            },
        )

    # Validate model selection dynamically against registry — never silently fall back
    try:
        from src.detector import resolve_model_info
        model_clean = (model or "current").strip()
        model_info = resolve_model_info(model_clean)
        model_key = model_info["key"]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_MODEL_SELECTION",
                "message": str(exc),
            },
        )

    # 2. Compute SHA-256 Digest of unaltered binary bytes
    sha256_digest = CryptoService.compute_sha256(raw_bytes)

    # 3. Securely persist media under sanitized UUIDv4 filename outside webroot
    saved_path_str = save_validated_upload(
        file_bytes=raw_bytes,
        validation_result=validation,
        target_dir=settings.STORAGE_DIR,
    )
    saved_path = Path(saved_path_str)

    # 4. Cryptographic Integrity & Signature Verification
    integrity_dict, signature_dict, prov_record = CryptoService.verify_media_cryptography(
        db=db,
        current_sha256=sha256_digest,
        file_bytes_len=len(raw_bytes),
        target_asset_id=asset_id,
    )

    # Query prior verifications on identical SHA-256 to detect cross-model disagreements
    prior_records = db.query(VerificationRecord).filter(
        VerificationRecord.sha256 == sha256_digest
    ).order_by(VerificationRecord.created_at.desc()).all()

    prior_predictions = []
    for pr in prior_records:
        if pr.ai_status == "SUCCESS" and pr.ai_label:
            p_details = {}
            if pr.details_json:
                try:
                    p_details = json.loads(pr.details_json).get("ai", {})
                except Exception:
                    pass
            prior_predictions.append({
                "label": pr.ai_label,
                "model_id": p_details.get("model_id") or "prior model",
                "confidence": pr.ai_confidence,
            })

    # 5. Safe AI Forensic Inference (Honest readiness, explicit model routing)
    ai_dict = AIService.analyze_image(
        saved_path,
        model=model_key,
        prior_predictions=prior_predictions,
    )

    # 6. Multi-Signal Transparent Trust Assessment
    trust_dict = TrustAssessmentEngine.evaluate(
        integrity=integrity_dict,
        signature=signature_dict,
        ai=ai_dict,
    )

    processing_ms = round((time.time() - start_time) * 1000, 2)
    verification_id = str(uuid.uuid4())
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # 7. Record Verification in Database
    rec = VerificationRecord(
        id=verification_id,
        user_id=current_user.id if current_user else None,
        asset_id=prov_record.asset_id if prov_record else None,
        filename=file.filename or validation.sanitized_filename,
        file_size_bytes=len(raw_bytes),
        sha256=sha256_digest,
        detected_format=validation.detected_format,
        width=validation.width,
        height=validation.height,
        integrity_status=integrity_dict["status"],
        signature_status=signature_dict["status"],
        key_trust_status=signature_dict.get("key_trust_status"),
        provenance_status="VERIFIED" if prov_record else "UNAVAILABLE",
        ai_status=ai_dict["status"],
        ai_label=ai_dict.get("label"),
        ai_confidence=ai_dict.get("confidence"),
        ai_likelihood=ai_dict.get("ai_likelihood"),
        ai_inference_ms=ai_dict.get("inference_ms"),
        ai_warning=ai_dict.get("warning"),
        document_warning=ai_dict.get("document_domain_warning"),
        trust_score=trust_dict["score"],
        overall_status=trust_dict["status"],
        overall_explanation=trust_dict["explanation"],
        details_json=json.dumps({
            "integrity": integrity_dict,
            "signature": signature_dict,
            "ai": ai_dict,
            "trust": trust_dict,
        }),
    )
    db.add(rec)
    db.commit()

    # 8. Log Audit Event
    AuditService.log_event(
        db,
        event_type="MEDIA_VERIFY",
        action="Media verification executed",
        status="SUCCESS",
        user_id=current_user.id if current_user else None,
        user_email=current_user.email if current_user else None,
        ip_address=request.client.host if request.client else None,
        asset_id=prov_record.asset_id if prov_record else None,
        sha256=sha256_digest,
        details={
            "verification_id": verification_id,
            "overall_status": trust_dict["status"],
            "trust_score": trust_dict["score"],
            "integrity": integrity_dict["status"],
            "ai": ai_dict["status"],
        },
    )

    return VerificationReport(
        verification_id=verification_id,
        filename=file.filename or validation.sanitized_filename,
        file_size_bytes=len(raw_bytes),
        detected_format=validation.detected_format,
        dimensions={"width": validation.width, "height": validation.height},
        sha256=sha256_digest,
        integrity=IntegrityDetail(**integrity_dict),
        signature=SignatureDetail(**signature_dict),
        ai=AIDetail(**ai_dict),
        trust_assessment=TrustAssessmentDetail(**trust_dict),
        timestamp=now_iso,
        processing_ms=processing_ms,
        asset_id=prov_record.asset_id if prov_record else None,
    )


@router.get("/history", response_model=List[VerificationHistoryItem])
def get_verification_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(VerificationRecord)
    if current_user and current_user.role.value != "ADMIN":
        query = query.filter(VerificationRecord.user_id == current_user.id)
    records = query.order_by(VerificationRecord.created_at.desc()).offset(offset).limit(limit).all()

    return [
        VerificationHistoryItem(
            verification_id=r.id,
            filename=r.filename,
            sha256=r.sha256,
            overall_status=r.overall_status,
            trust_score=r.trust_score,
            integrity_status=r.integrity_status,
            ai_status=r.ai_status,
            ai_label=r.ai_label,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        for r in records
    ]


@router.get("/models")
@router.get("/models/available")
def get_available_models():
    """Return available AI detection models dynamically from the model registry."""
    from src.detector import MODEL_REGISTRY
    models = []
    for key, info in MODEL_REGISTRY.items():
        models.append({
            "key": key,
            "model_id": info["model_id"],
            "name": info.get("name"),
            "short_name": info.get("short_name", info.get("name")),
            "architecture": info.get("architecture"),
            "architecture_name": info.get("architecture_name", info.get("architecture")),
            "description": info.get("description"),
            "badge": info.get("badge", ""),
        })
    return models


@router.get("/{verification_id}", response_model=VerificationReport)
def get_verification_by_id(
    verification_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    rec = db.query(VerificationRecord).filter(VerificationRecord.id == verification_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Verification report not found")

    if current_user and current_user.role.value != "ADMIN" and rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this verification record.")

    details = json.loads(rec.details_json) if rec.details_json else {}
    return VerificationReport(
        verification_id=rec.id,
        filename=rec.filename,
        file_size_bytes=rec.file_size_bytes,
        detected_format=rec.detected_format,
        dimensions={"width": rec.width, "height": rec.height},
        sha256=rec.sha256,
        integrity=IntegrityDetail(**details.get("integrity", {
            "status": rec.integrity_status,
            "algorithm": "sha256",
            "current_sha256": rec.sha256,
            "message": "Recorded verification.",
        })),
        signature=SignatureDetail(**details.get("signature", {
            "status": rec.signature_status,
            "key_trust_status": rec.key_trust_status,
            "algorithm": "ECDSA-P256-SHA256",
            "message": "Recorded verification.",
        })),
        ai=AIDetail(**details.get("ai", {
            "status": rec.ai_status,
            "label": rec.ai_label,
            "confidence": rec.ai_confidence,
            "ai_likelihood": rec.ai_likelihood,
            "inference_ms": rec.ai_inference_ms,
            "warning": rec.ai_warning,
            "document_domain_warning": rec.document_warning,
        })),
        trust_assessment=TrustAssessmentDetail(**details.get("trust", {
            "status": rec.overall_status,
            "score": rec.trust_score,
            "badge": rec.overall_status,
            "badge_color": "slate",
            "explanation": rec.overall_explanation,
            "signals_summary": {},
        })),
        timestamp=rec.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        processing_ms=0.0,
        asset_id=rec.asset_id,
    )

