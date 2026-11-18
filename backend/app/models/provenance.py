import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"

    asset_id = Column(String(64), primary_key=True, index=True)
    sha256 = Column(String(64), index=True, nullable=False)
    registered_at = Column(String(64), nullable=False)
    signing_key_id = Column(String(128), nullable=False)
    content_type = Column(String(64), nullable=False)
    issuer_id = Column(String(128), nullable=True)
    metadata_json = Column(Text, nullable=True)
    signature_b64 = Column(Text, nullable=False)
    publisher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    original_filename = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    publisher = relationship("User", back_populates="provenance_records")

