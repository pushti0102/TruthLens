"""
TruthLens Cryptography Subpackage
Member 2: Cryptography & Information Security
"""

from member2_security.crypto.canonicalization import (
    CanonicalizationError,
    canonicalize_json,
    canonicalize_record,
    validate_provenance_record_schema,
)
from member2_security.crypto.encryption import (
    DecryptionAuthenticationError,
    EncryptedEnvelope,
    EncryptionError,
    InvalidEnvelopeError,
    decrypt_bytes,
    encrypt_bytes,
)
from member2_security.crypto.hashing import (
    IntegrityResult,
    IntegrityStatus,
    compare_hashes,
    is_valid_sha256_hex,
    normalize_sha256,
    sha256_bytes,
    sha256_file,
    sha256_stream,
    verify_file_integrity,
)
from member2_security.crypto.signatures import (
    SignatureStatus,
    SignatureVerificationResult,
    sign_canonical_bytes,
    sign_record,
    verify_canonical_bytes_signature,
    verify_record_signature,
)

__all__ = [
    # Hashing
    "IntegrityStatus",
    "IntegrityResult",
    "sha256_bytes",
    "sha256_file",
    "sha256_stream",
    "compare_hashes",
    "is_valid_sha256_hex",
    "normalize_sha256",
    "verify_file_integrity",
    # Canonicalization
    "CanonicalizationError",
    "canonicalize_json",
    "canonicalize_record",
    "validate_provenance_record_schema",
    # Signatures
    "SignatureStatus",
    "SignatureVerificationResult",
    "sign_canonical_bytes",
    "sign_record",
    "verify_canonical_bytes_signature",
    "verify_record_signature",
    # Encryption
    "EncryptionError",
    "DecryptionAuthenticationError",
    "InvalidEnvelopeError",
    "EncryptedEnvelope",
    "encrypt_bytes",
    "decrypt_bytes",
]
