import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    asset_id = Column(String(64), nullable=True)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), index=True, nullable=False)
    detected_format = Column(String(32), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Cryptographic signals
    integrity_status = Column(String(32), nullable=False)  # MATCH, MISMATCH, NO_REFERENCE, INVALID_INPUT
    signature_status = Column(String(32), nullable=False)  # VALID, INVALID, MISSING, MALFORMED
    key_trust_status = Column(String(32), nullable=True)   # TRUSTED, REVOKED, EXPIRED, UNKNOWN
    provenance_status = Column(String(32), nullable=False) # VERIFIED, MISMATCH, UNAVAILABLE, INVALID

    # AI signals
    ai_status = Column(String(32), nullable=False)         # SUCCESS, UNAVAILABLE, ERROR
    ai_label = Column(String(32), nullable=True)           # REAL, AI_GENERATED
    ai_confidence = Column(Float, nullable=True)
    ai_likelihood = Column(String(32), nullable=True)      # high, moderate, low, inconclusive
    ai_inference_ms = Column(Float, nullable=True)
    ai_warning = Column(Text, nullable=True)
    document_warning = Column(Text, nullable=True)

    # Synthesis
    trust_score = Column(Integer, nullable=False)          # 0 to 100
    overall_status = Column(String(64), nullable=False)    # VERIFIED_TRUSTED, INTEGRITY_MISMATCH, SUSPICIOUS_AI, INCONCLUSIVE
    overall_explanation = Column(Text, nullable=False)
    details_json = Column(Text, nullable=True)             # Full payload
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="verifications")

