import json
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.provenance import ProvenanceRecord
from backend.app.schemas.provenance import ProvenanceRecordOut
from backend.app.security.auth import get_current_user, require_role
from backend.app.security.keys import crypto_manager
from backend.app.services.crypto_service import CryptoService
from backend.app.services.audit_service import AuditService

from member2_security.security.upload_validation import (
    validate_image_bytes,
    save_validated_upload,
    UploadValidationResult,
)

router = APIRouter(prefix="/api/publishers", tags=["Trusted Publisher Registry"])


@router.post("/register-media", response_model=ProvenanceRecordOut, status_code=status.HTTP_201_CREATED)
async def register_media(
    request: Request,
    file: UploadFile = File(...),
    issuer_id: Optional[str] = Form("org_truthlens_official"),
    metadata_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PUBLISHER, UserRole.ADMIN)),
):
    raw_bytes = await file.read()

    # 1. Validate image
    validation: UploadValidationResult = validate_image_bytes(
        file_bytes=raw_bytes,
        original_filename=file.filename,
        max_file_size=settings.MAX_UPLOAD_BYTES,
        max_pixels=settings.MAX_UPLOAD_PIXELS,
        max_width=settings.MAX_WIDTH,
        max_height=settings.MAX_HEIGHT,
    )
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": validation.error_code, "message": validation.error_message},
        )

    # 2. Compute SHA-256
    sha256_digest = CryptoService.compute_sha256(raw_bytes)

    # Check if duplicate digest already registered
    existing = db.query(ProvenanceRecord).filter(ProvenanceRecord.sha256 == sha256_digest).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An asset with this exact SHA-256 digest ({sha256_digest[:16]}...) is already registered (Asset ID: {existing.asset_id}).",
        )

    # 3. Save file
    saved_path_str = save_validated_upload(
        file_bytes=raw_bytes,
        validation_result=validation,
        target_dir=settings.STORAGE_DIR,
    )

    # 4. Parse metadata if provided
    parsed_meta = None
    if metadata_json:
        try:
            parsed_meta = json.loads(metadata_json)
        except Exception:
            pass

    # 5. Create & ECDSA Sign Provenance Record
    asset_id = str(uuid.uuid4())
    content_type = f"image/{validation.detected_format.lower()}"
    if validation.detected_format == "JPEG":
        content_type = "image/jpeg"

    record = CryptoService.register_provenance_record(
        db=db,
        asset_id=asset_id,
        sha256=sha256_digest,
        content_type=content_type,
        original_filename=file.filename,
        file_size_bytes=len(raw_bytes),
        storage_path=str(saved_path_str),
        publisher_id=current_user.id,
        issuer_id=issuer_id or "org_truthlens_official",
        metadata=parsed_meta,
    )

    # 6. Audit Log
    AuditService.log_event(
        db,
        event_type="MEDIA_REGISTER",
        action="Trusted media registered and signed",
        status="SUCCESS",
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=request.client.host if request.client else None,
        asset_id=asset_id,
        sha256=sha256_digest,
        details={"issuer": issuer_id, "key_id": record.signing_key_id},
    )

    return ProvenanceRecordOut(
        schema_version="1.0",
        asset_id=record.asset_id,
        sha256=record.sha256,
        registered_at=record.registered_at,
        signing_key_id=record.signing_key_id,
        content_type=record.content_type,
        issuer_id=record.issuer_id,
        metadata=parsed_meta,
        signature_b64=record.signature_b64,
        publisher_id=record.publisher_id,
        original_filename=record.original_filename,
        file_size_bytes=record.file_size_bytes,
    )


@router.get("/records", response_model=List[ProvenanceRecordOut])
def list_provenance_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PUBLISHER, UserRole.ADMIN)),
):
    records = db.query(ProvenanceRecord).order_by(ProvenanceRecord.created_at.desc()).all()
    out = []
    for r in records:
        meta = None
        if r.metadata_json:
            try:
                meta = json.loads(r.metadata_json)
            except Exception:
                pass
        out.append(
            ProvenanceRecordOut(
                schema_version="1.0",
                asset_id=r.asset_id,
                sha256=r.sha256,
                registered_at=r.registered_at,
                signing_key_id=r.signing_key_id,
                content_type=r.content_type,
                issuer_id=r.issuer_id,
                metadata=meta,
                signature_b64=r.signature_b64,
                publisher_id=r.publisher_id,
                original_filename=r.original_filename,
                file_size_bytes=r.file_size_bytes,
            )
        )
    return out


@router.get("/keys")
def list_trusted_keys(
    current_user: User = Depends(require_role(UserRole.PUBLISHER, UserRole.ADMIN)),
):
    registry = crypto_manager.get_registry()
    return [k.to_dict() for k in registry._keys.values()]

