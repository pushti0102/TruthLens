# TruthLens Security & Cryptography Module
**TruthLens — AI-Powered Digital Media Authenticity & Provenance Verification System**  
**Role:** Member 2 — Cryptography & Information Security Engineer  
**Package:** `member2_security`

---

## 1. Module Overview & Responsibilities

The `member2_security` module provides the core cryptographic integrity, non-repudiation, authenticated encryption, upload validation, and rate-limiting foundations for TruthLens:

```
member2_security/
├── crypto/
│   ├── hashing.py           # Chunked SHA-256 streaming, constant-time comparison
│   ├── canonicalization.py  # RFC 8785 canonical JSON serialization & schema validation
│   ├── signatures.py        # ECDSA NIST P-256 (SECP256R1) signing & verification
│   └── encryption.py        # AES-256-GCM AEAD authenticated envelope encryption
├── key_management/
│   ├── key_utils.py         # Key pair generation, password-protected PEM, 256-bit AES
│   ├── registry.py          # KeyRegistry lifecycle (ACTIVE, RETIRED, REVOKED) & trust evaluation
│   └── README.md            # Key management & KMS deployment guide
├── security/
│   ├── upload_validation.py # OWASP-compliant JPEG/PNG/WebP validation & decompression bomb defense
│   └── rate_limiting.py     # User-aware sliding window rate limiter & FastAPI dependency
├── tests/                   # 82 automated pytest security tests
├── examples/
│   └── demo_integrity.py   # Comprehensive 11-step end-to-end executable demo
├── requirements.txt         # Security dependencies
└── README.md                # This documentation
```

### Team Division of Responsibilities
- **Member 1 (AI Models):** Deepfake detection, manipulation localization, feature inference.
- **Member 2 (This Module):** Cryptographic primitives, file hashing, ECDSA signatures, AES-256-GCM, upload sanitization, rate limiting.
- **Member 3 (FastAPI & Frontend):** API endpoints, database persistence, JWT authentication, React UI.

> [!IMPORTANT]
> **Integrity vs Authenticity Notice:**  
> A SHA-256 hash or digital signature proves **byte-level identity** and **origin non-repudiation** relative to a registered baseline record. It does **not** prove that an unregistered image is genuine, unedited, or factually truthful. A hash mismatch indicates byte divergence (which can occur from re-saving, transcoding, or resizing as well as malicious manipulation).

---

## 2. Requirements & Installation

### Python Version
- Python **3.11+** (tested and verified on Python 3.13.1).

### Dependencies
Install the required packages:
```bash
pip install -r member2_security/requirements.txt
```
Key libraries:
- `cryptography>=42.0.0` (Maintained by PyCA; OpenSSL/Rust backend for ECDSA and AESGCM).
- `pillow>=10.0.0` (Image structural validation and raster load verification).
- `fastapi>=0.100.0` (Endpoint integration).
- `slowapi>=0.1.9` (Optional rate-limiting adapter).
- `pytest>=8.0.0` (Testing framework).

---

## 3. Environment & Configuration

Copy `.env.example` to `.env` and configure appropriate values:
```bash
cp .env.example .env
```

Key environment settings:
- `TRUTHLENS_ACTIVE_KEY_ID`: Identifier for active signing key.
- `TRUTHLENS_ECDSA_PRIVATE_KEY_PATH`: Path to PEM private key file (kept outside webroot).
- `TRUTHLENS_ECDSA_PRIVATE_KEY_PASSWORD`: Passphrase protecting private key.
- `TRUTHLENS_UPLOAD_MAX_BYTES`: Maximum upload size in bytes (default: 10485760 = 10 MB).
- `TRUTHLENS_UPLOAD_MAX_PIXELS`: Decompression bomb limit (default: 25000000 = 25 MP).
- `TRUTHLENS_RATE_LIMIT_ANALYSIS`: Rate limit for verification endpoints (default: 10/minute).

---

## 4. API Usage Guide

### 4.1 SHA-256 File Integrity Verification

```python
from member2_security.crypto import (
    sha256_file,
    sha256_bytes,
    compare_hashes,
    IntegrityStatus,
)

# 1. Stream hash from disk in 64KB chunks (safe for large files)
current_hash = sha256_file("storage/sample.jpg")

# 2. Or compute directly from raw bytes
byte_hash = sha256_bytes(uploaded_raw_bytes)

# 3. Constant-time comparison against reference digest
result = compare_hashes(
    current_hash=current_hash,
    reference_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)

if result.status == IntegrityStatus.MATCH:
    print("File matches registered reference byte-for-byte.")
elif result.status == IntegrityStatus.MISMATCH:
    print("File has diverged from reference.")
elif result.status == IntegrityStatus.NO_REFERENCE:
    print("No baseline record exists for comparison.")
```

---

### 4.2 ECDSA Digital Signatures (NIST P-256 / SECP256R1)

#### Canonical Provenance Record Format:
The signed record must adhere to `schema_version: "1.0"`:
```python
provenance_record = {
    "schema_version": "1.0",
    "asset_id": "4f8c2b71-e940-4b8c-b062-817dbbc1c499",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "registered_at": "2026-10-26T10:30:00Z",
    "signing_key_id": "tl-key-ecdsa-2026-v1",
    "content_type": "image/jpeg",
    "issuer_id": "org_truthlens_official"
}
```

#### Signing & Verifying:
```python
from member2_security.crypto import sign_record, verify_record_signature, SignatureStatus
from member2_security.key_management import KeyRegistry, load_private_key_pem

# Sign record
signature_b64 = sign_record(provenance_record, private_key)

# Verify signature
verification = verify_record_signature(
    record=provenance_record,
    signature_b64=signature_b64,
    key_registry=trusted_registry
)

# Status: VALID | INVALID | MISSING | MALFORMED
if verification.status == SignatureStatus.VALID:
    # Trust status: TRUSTED | REVOKED | EXPIRED | UNKNOWN
    print(f"Signature verified. Key Trust: {verification.key_trust_status}")
```

---

### 4.3 AES-256-GCM Authenticated Encryption

```python
from member2_security.crypto import encrypt_bytes, decrypt_bytes

# Encrypt with fresh 12-byte nonce and context-binding AAD
envelope = encrypt_bytes(
    plaintext=b"Confidential forensic audit notes",
    key=aes_32_byte_key,
    key_id="tl-aes-2026-v1",
    aad=b"asset_id:4f8c2b71"  # Authenticated Associated Data
)

# Serialized envelope format for DB/JSON storage
envelope_dict = envelope.to_dict()

# Decrypt and authenticate
decrypted = decrypt_bytes(
    envelope=envelope_dict,
    key=aes_32_byte_key,
    aad=b"asset_id:4f8c2b71"
)
```

---

### 4.4 Secure Image-Upload Validation

```python
from member2_security.security import validate_image_bytes, save_validated_upload

# Validate upload bytes before saving or invoking AI inference
validation = validate_image_bytes(
    file_bytes=upload_bytes,
    original_filename="user_upload.jpg",
    max_file_size=10 * 1024 * 1024,
    max_pixels=25_000_000
)

if not validation.valid:
    print(f"Rejected ({validation.error_code}): {validation.error_message}")
else:
    # Save safely under server-generated UUIDv4 asset filename
    saved_path = save_validated_upload(
        file_bytes=upload_bytes,
        validation_result=validation,
        target_dir="storage/verified_assets"
    )
    print(f"Saved safely to {saved_path}")
```

---

### 4.5 Rate-Limiting Integration for FastAPI

```python
from fastapi import FastAPI, Depends
from member2_security.security import RateLimitDependency

app = FastAPI()

# Enforce limit of 10 requests per minute on expensive verification route
@app.post("/api/v1/verify", dependencies=[Depends(RateLimitDependency("10/minute", tag="verify"))])
async def verify_endpoint():
    return {"status": "ok"}
```

---

## 5. Verification & Testing

### Running Automated Test Suite
To run the complete 82-test automated test suite:
```bash
python -m pytest member2_security/tests/ -v
```

### Running the End-to-End Demonstration
Execute the 11-step cryptographic and integrity demonstration:
```bash
python member2_security/examples/demo_integrity.py
```

---

## 6. Known Limitations & Security Assumptions

1. **In-Memory Rate Limiting:** The default `SlidingWindowRateLimiter` maintains state per worker process. In multi-worker deployments (e.g. `uvicorn -w 4`), connect an external cache such as Redis.
2. **Key Storage:** Local file storage with `chmod 0600` is intended for development. Production deployments must integrate with AWS KMS, Google Cloud KMS, Azure Key Vault, or HashiCorp Vault.
3. **Loss of Symmetric Key:** AES-256-GCM ciphertexts cannot be decrypted without the secret key. Robust backup and rotation procedures are required.
4. **Scope Separation:** Cryptographic integrity establishes that a media file has not altered since registration; it does not replace Member 1's AI forensic model for detecting pre-registration deepfakes or edits.
