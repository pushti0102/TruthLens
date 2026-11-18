import json
import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.provenance import ProvenanceRecord
from backend.app.security.keys import crypto_manager

from member2_security.crypto.hashing import (
    sha256_bytes,
    compare_hashes,
    IntegrityResult,
    IntegrityStatus,
)
from member2_security.crypto.signatures import (
    sign_record,
    verify_record_signature,
    SignatureVerificationResult,
    SignatureStatus,
)
from member2_security.key_management.registry import KeyTrustStatus


class CryptoService:
    """Provides cryptographic operations for media registration and verification."""

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return sha256_bytes(file_bytes)

    @classmethod
    def register_provenance_record(
        cls,
        db: Session,
        asset_id: str,
        sha256: str,
        content_type: str,
        original_filename: str,
        file_size_bytes: int,
        storage_path: str,
        publisher_id: Optional[int] = None,
        issuer_id: Optional[str] = "org_truthlens_official",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceRecord:
        """
        Creates and digitally signs a canonical provenance record.
        """
        now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Canonical record dict strictly matching schema 1.0
        canonical_dict = {
            "schema_version": "1.0",
            "asset_id": asset_id,
            "sha256": sha256.lower(),
            "registered_at": now_iso,
            "signing_key_id": crypto_manager.active_key_id,
            "content_type": content_type,
            "issuer_id": issuer_id or "org_truthlens_official",
        }
        if metadata:
            canonical_dict["metadata"] = metadata

        # Sign record using active ECDSA private key
        private_key = crypto_manager.get_private_key()
        signature_b64 = sign_record(canonical_dict, private_key)

        # Persist to database
        record = ProvenanceRecord(
            asset_id=asset_id,
            sha256=sha256.lower(),
            registered_at=now_iso,
            signing_key_id=crypto_manager.active_key_id,
            content_type=content_type,
            issuer_id=issuer_id or "org_truthlens_official",
            metadata_json=json.dumps(metadata) if metadata else None,
            signature_b64=signature_b64,
            publisher_id=publisher_id,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            storage_path=str(storage_path) if storage_path else None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def verify_media_cryptography(
        cls,
        db: Session,
        current_sha256: str,
        file_bytes_len: int,
        target_asset_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[ProvenanceRecord]]:
        """
        Evaluates SHA-256 integrity and ECDSA provenance signature against database records.
        """
        # Look up registered reference by hash or asset_id
        prov_record: Optional[ProvenanceRecord] = None
        if target_asset_id:
            prov_record = db.query(ProvenanceRecord).filter(ProvenanceRecord.asset_id == target_asset_id).first()
        if not prov_record:
            prov_record = db.query(ProvenanceRecord).filter(ProvenanceRecord.sha256 == current_sha256.lower()).first()

        # 1. Integrity check
        if prov_record:
            integrity_res: IntegrityResult = compare_hashes(
                current_hash=current_sha256.lower(),
                reference_hash=prov_record.sha256,
            )
            integrity_dict = {
                "status": integrity_res.status.value,
                "algorithm": "sha256",
                "current_sha256": current_sha256.lower(),
                "reference_sha256": prov_record.sha256,
                "bytes_hashed": file_bytes_len,
                "message": integrity_res.message,
            }
        else:
            integrity_dict = {
                "status": IntegrityStatus.NO_REFERENCE.value,
                "algorithm": "sha256",
                "current_sha256": current_sha256.lower(),
                "reference_sha256": None,
                "bytes_hashed": file_bytes_len,
                "message": "No registered cryptographic baseline found for this file digest.",
            }

        # 2. Signature check
        if prov_record:
            # Reconstruct canonical record dictionary
            canonical_dict = {
                "schema_version": "1.0",
                "asset_id": prov_record.asset_id,
                "sha256": prov_record.sha256,
                "registered_at": prov_record.registered_at,
                "signing_key_id": prov_record.signing_key_id,
                "content_type": prov_record.content_type,
                "issuer_id": prov_record.issuer_id,
            }
            if prov_record.metadata_json:
                try:
                    canonical_dict["metadata"] = json.loads(prov_record.metadata_json)
                except Exception:
                    pass

            sig_res: SignatureVerificationResult = verify_record_signature(
                record=canonical_dict,
                signature_b64=prov_record.signature_b64,
                key_registry=crypto_manager.get_registry(),
            )

            signature_dict = {
                "status": sig_res.status.value,
                "key_id": sig_res.key_id,
                "key_trust_status": sig_res.key_trust_status.value if sig_res.key_trust_status else "UNKNOWN",
                "algorithm": sig_res.algorithm,
                "message": sig_res.message,
            }
        else:
            signature_dict = {
                "status": SignatureStatus.MISSING.value,
                "key_id": None,
                "key_trust_status": None,
                "algorithm": "ECDSA-P256-SHA256",
                "message": "No registered digital signature associated with this file.",
            }

        return integrity_dict, signature_dict, prov_record

