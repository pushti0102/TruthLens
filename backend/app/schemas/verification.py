from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class IntegrityDetail(BaseModel):
    status: str  # MATCH, MISMATCH, NO_REFERENCE, INVALID_INPUT
    algorithm: str = "sha256"
    current_sha256: str
    reference_sha256: Optional[str] = None
    bytes_hashed: Optional[int] = None
    message: str


class SignatureDetail(BaseModel):
    status: str  # VALID, INVALID, MISSING, MALFORMED
    key_id: Optional[str] = None
    key_trust_status: Optional[str] = None  # TRUSTED, REVOKED, EXPIRED, UNKNOWN
    algorithm: str = "ECDSA-P256-SHA256"
    message: str


class AIDetail(BaseModel):
    status: str  # SUCCESS, UNAVAILABLE, ERROR
    label: Optional[str] = None  # REAL, AI_GENERATED
    confidence: Optional[float] = None
    raw_scores: Optional[List[Dict[str, Any]]] = None
    model_id: Optional[str] = None
    inference_ms: Optional[float] = None
    ai_likelihood: Optional[str] = None  # high, moderate, low, inconclusive
    warning: Optional[str] = None
    document_domain_warning: Optional[str] = None
    message: Optional[str] = None


class TrustAssessmentDetail(BaseModel):
    status: str  # VERIFIED_TRUSTED, INTEGRITY_MISMATCH, INVALID_SIGNATURE, SUSPICIOUS_AI, INCONCLUSIVE
    score: int  # 0 to 100
    badge: str
    badge_color: str
    explanation: str
    signals_summary: Dict[str, Any]


class VerificationReport(BaseModel):
    verification_id: str
    filename: str
    file_size_bytes: int
    detected_format: Optional[str] = None
    dimensions: Optional[Dict[str, Any]] = None
    sha256: str
    integrity: IntegrityDetail
    signature: SignatureDetail
    ai: AIDetail
    trust_assessment: TrustAssessmentDetail
    timestamp: str
    processing_ms: float
    asset_id: Optional[str] = None

    class Config:
        from_attributes = True


class VerificationHistoryItem(BaseModel):
    verification_id: str
    filename: str
    sha256: str
    overall_status: str
    trust_score: int
    integrity_status: str
    ai_status: str
    ai_label: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

