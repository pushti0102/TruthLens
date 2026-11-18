from typing import Optional, Dict, Any
from pydantic import BaseModel


class ProvenanceRecordOut(BaseModel):
    schema_version: str = "1.0"
    asset_id: str
    sha256: str
    registered_at: str
    signing_key_id: str
    content_type: str
    issuer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    signature_b64: str
    publisher_id: Optional[int] = None
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None

    class Config:
        from_attributes = True

