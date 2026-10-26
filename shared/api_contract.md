# TruthLens Architecture & API Contract
**Module:** Member 2 — Cryptography, File Integrity & Information Security  
**Integration Stakeholders:** Member 1 (AI Detection Models), Member 3 (FastAPI Backend, Auth, DB, Frontend)  
**Schema Version:** 1.0.0

---

## 1. System Responsibilities & Boundaries

TruthLens combines Artificial Intelligence, Cryptography, and Secure System Design to deliver verifiable digital media provenance. To maintain clean boundaries:

| Member | Domain | Scope & Responsibilities | Excluded from Scope |
| :--- | :--- | :--- | :--- |
| **Member 1** | **AI & Media Forensics** | Deepfake detection, synthetic generation classification, local manipulation localization, model inference, and feature extraction. | Cryptographic hashing, digital signatures, key management, database schemas. |
| **Member 2** | **Cryptography & Security** | Raw-byte SHA-256 integrity, ECDSA P-256 provenance signatures, AES-256-GCM envelope encryption, key lifecycle management (active/retired/revoked), OWASP-compliant upload validation, and rate limiting. | AI model training, frontend UI, database ORM, user session/JWT authentication. |
| **Member 3** | **Application & Integration** | FastAPI REST routing, JWT authentication, role-based access control (RBAC), database persistence (PostgreSQL/SQLite), audit log aggregation, frontend React UI. | Raw cryptographic implementations, AI inference pipelines. |

> [!IMPORTANT]
> **Integrity vs. Authenticity:**  
> A SHA-256 hash or valid digital signature establishes **byte-level identity** and **origin non-repudiation** relative to a registered baseline. It does **not** prove that the depicted media is truthful, untampered prior to initial registration, or free from AI generation. Authentic provenance requires combining Member 2's cryptographic proofs with Member 1's AI forensic assessment.

---

## 2. Shared Data Schemas

### 2.1 Provenance Record Schema (`schema_version: "1.0"`)
This canonical data record is stored in the database by Member 3 and digitally signed by Member 2.

```json
{
  "schema_version": "1.0",
  "asset_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "registered_at": "2026-10-26T10:30:00Z",
  "signing_key_id": "tl-key-ecdsa-2026-v1",
  "content_type": "image/jpeg",
  "issuer_id": "org_truthlens_official",
  "metadata": {
    "capture_device": "Hardware Sentinel Mark II",
    "ingest_channel": "trusted_api"
  }
}
```

**Field Rules:**
- `schema_version`: Must be `"1.0"`.
- `asset_id`: Unique UUIDv4 identifier generated server-side.
- `sha256`: 64 lowercase hexadecimal characters representing the SHA-256 digest of the raw image bytes.
- `registered_at`: Strict ISO-8601 UTC timestamp ending in `Z` or `+00:00`.
- `signing_key_id`: Identifier of the ECDSA key used to sign the record.
- `content_type`: One of `"image/jpeg"`, `"image/png"`, `"image/webp"`.
- `issuer_id`: Optional string identifying the publishing entity.
- `signature`: **MUST NOT** be included inside the canonical payload. The signature is transmitted or stored as a separate field (`signature_b64`).

---

## 3. Cryptographic API Interfaces for Member 3

All security functions are imported from `member2_security`:

```python
from member2_security.crypto import (
    sha256_bytes,
    sha256_file,
    compare_hashes,
    IntegrityResult,
    IntegrityStatus,
    sign_record,
    verify_record_signature,
    SignatureVerificationResult,
    SignatureStatus,
    encrypt_bytes,
    decrypt_bytes,
    EncryptedEnvelope,
)
from member2_security.security import (
    validate_image_bytes,
    save_validated_upload,
    UploadValidationResult,
    RateLimitDependency,
)
from member2_security.key_management import (
    KeyRegistry,
    KeyTrustStatus,
)
```

---

### 3.1 File Integrity Verification

#### A. Compute Digest
```python
digest: str = sha256_file("/path/to/media.jpg")
# or for in-memory bytes:
digest: str = sha256_bytes(uploaded_file_bytes)
```

#### B. Compare Digest Against Reference
```python
result: IntegrityResult = compare_hashes(
    current_hash=digest,
    reference_hash=stored_provenance_record["sha256"]
)
```

#### Structured Output Contract:
```python
{
    "status": "MATCH",            # "MATCH" | "MISMATCH" | "NO_REFERENCE" | "INVALID_INPUT"
    "algorithm": "sha256",
    "current_sha256": "e3b0c442...",
    "reference_sha256": "e3b0c442...",
    "bytes_hashed": 1048576,      # Optional byte count
    "message": "Current file digest matches reference digest byte-for-byte."
}
```

**Status Definitions:**
- `MATCH`: Current file digest matches the trusted reference byte-for-byte.
- `MISMATCH`: Current file digest differs from the reference (indicates re-compression, transcoding, metadata edit, or tampering).
- `NO_REFERENCE`: No trusted reference digest is registered. (Never treated as MATCH or MISMATCH).
- `INVALID_INPUT`: Malformed digest string or missing file.

---

### 3.2 Digital Signatures (ECDSA NIST P-256)

#### A. Sign Provenance Record (Registration)
```python
signature_b64: str = sign_record(
    record=provenance_record_dict,
    private_key=loaded_private_key
)
```

#### B. Verify Signature (Verification Pipeline)
```python
result: SignatureVerificationResult = verify_record_signature(
    record=provenance_record_dict,
    signature_b64=signature_b64,
    public_key=optional_public_key,
    key_registry=trusted_key_registry  # Evaluates whether signing_key_id is TRUSTED, REVOKED, or EXPIRED
)
```

#### Structured Output Contract:
```python
{
    "status": "VALID",            # "VALID" | "INVALID" | "MISSING" | "MALFORMED"
    "key_id": "tl-key-ecdsa-2026-v1",
    "key_trust_status": "TRUSTED", # "TRUSTED" | "REVOKED" | "EXPIRED" | "UNKNOWN"
    "algorithm": "ECDSA-P256-SHA256",
    "message": "Signature mathematically verified under public key. Key is TRUSTED in the authority registry."
}
```

> [!WARNING]
> **Key Trust vs. Signature Validity:**  
> A signature status of `VALID` only guarantees mathematical correctness under a key. Check `key_trust_status == "TRUSTED"` before displaying an authoritative trust badge in the UI.

---

### 3.3 Authenticated Encryption (AES-256-GCM)

Used for encrypting sensitive audit logs, watermarking vectors, or restricted evidence payloads.

#### A. Encrypt
```python
envelope: EncryptedEnvelope = encrypt_bytes(
    plaintext=b"sensitive audit payload",
    key=aes_key_32_bytes,
    key_id="tl-aes-2026-v1",
    aad=b"asset_id:9b1deb4d"  # Contextual binding
)
envelope_dict = envelope.to_dict()
```

#### B. Decrypt
```python
plaintext: bytes = decrypt_bytes(
    envelope=envelope_dict,
    key=aes_key_32_bytes,
    aad=b"asset_id:9b1deb4d"
)
```

#### Structured Output Contract:
```python
{
    "version": "1.0",
    "algorithm": "AES-256-GCM",
    "key_id": "tl-aes-2026-v1",
    "nonce": "a1b2c3d4e5f6g7h8i9j0k1l2",     # 12-byte fresh nonce (Base64)
    "ciphertext_and_tag": "3v8B...x9Q=",      # Base64 ciphertext with appended 16-byte tag
    "aad_version": null
}
```
*Note: If ciphertext, key, nonce, or AAD is tampered with, `DecryptionAuthenticationError` is raised immediately. Partial plaintext is never returned.*

---

### 3.4 Upload Validation Pipeline

Must be called by Member 3 prior to storing files or invoking AI models:

```python
validation: UploadValidationResult = validate_image_bytes(
    file_bytes=raw_upload_bytes,
    original_filename=file.filename,
    max_file_size=10 * 1024 * 1024,
    max_pixels=25_000_000
)

if not validation.valid:
    raise HTTPException(status_code=400, detail={
        "error_code": validation.error_code,
        "message": validation.error_message
    })

# Securely persist under server-generated UUIDv4 asset filename:
saved_path = save_validated_upload(
    file_bytes=raw_upload_bytes,
    validation_result=validation,
    target_dir="/app/storage/verified_assets"
)
```

#### Structured Output Contract:
```python
{
    "valid": true,
    "detected_format": "JPEG",          # "JPEG" | "PNG" | "WEBP"
    "file_size_bytes": 1048576,
    "width": 1920,
    "height": 1080,
    "error_code": null,
    "error_message": null,
    "asset_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "sanitized_filename": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d.jpg"
}
```

---

### 3.5 Rate-Limiting Integration for FastAPI Routes

```python
from fastapi import FastAPI, Depends
from member2_security.security import RateLimitDependency

app = FastAPI()

# General endpoint rate limit (60 requests per minute)
@app.get("/api/v1/provenance/{asset_id}", dependencies=[Depends(RateLimitDependency("60/minute", tag="read"))])
async def get_provenance(asset_id: str):
    ...

# Expensive AI analysis / upload endpoint (10 requests per minute)
@app.post("/api/v1/verify", dependencies=[Depends(RateLimitDependency("10/minute", tag="verify"))])
async def verify_media(...):
    ...
```

**HTTP 429 Response Format:**
```json
{
  "detail": {
    "error_code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit of 10 requests per 60s exceeded.",
    "retry_after_seconds": 45
  }
}
```
**Headers:**
- `Retry-After: 45`
- `X-RateLimit-Limit: 10`
- `X-RateLimit-Remaining: 0`
- `X-RateLimit-Reset: 60`
