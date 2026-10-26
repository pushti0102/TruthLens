"""
TruthLens Digital Signatures Module
Member 2: Cryptography & Information Security

Implements ECDSA digital signatures using the NIST P-256 curve (SECP256R1)
with SHA-256 message digests for digital provenance records.

CRITICAL SECURITY PRINCIPLES:
1. Deterministic Canonicalization:
   Signatures are calculated over canonicalized UTF-8 bytes (RFC 8785) of the
   provenance record, not arbitrary JSON text.
2. Signature Separation:
   The signature itself is excluded from the signed canonical payload.
3. Trust != Mathematical Validity:
   A valid signature only proves that the record was signed by whoever holds the
   corresponding private key. Trust in the signer is evaluated separately via
   the KeyRegistry.
4. Non-Crashing Verification:
   All verification operations catch cryptographic anomalies (malformed DER,
   invalid Base64, schema errors) and return structured status codes rather than
   crashing the runtime.
5. No Private Key Exposure:
   Private keys are never exposed in return values, log statements, or exception strings.
"""

from __future__ import annotations

import base64
import enum
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from member2_security.crypto.canonicalization import (
    CanonicalizationError,
    canonicalize_record,
)
from member2_security.key_management.key_utils import load_public_key_pem
from member2_security.key_management.registry import KeyRegistry, KeyTrustStatus


class SignatureStatus(str, enum.Enum):
    """Mathematical signature verification outcome."""
    VALID = "VALID"          # Cryptographically valid under the supplied public key
    INVALID = "INVALID"      # Signature fails cryptographic verification (content modified or wrong key)
    MISSING = "MISSING"      # No signature was provided
    MALFORMED = "MALFORMED"  # Signature string or record payload cannot be parsed/decoded


@dataclass(frozen=True)
class SignatureVerificationResult:
    """Structured result returned by digital signature verification."""

    status: SignatureStatus
    key_id: Optional[str] = None
    key_trust_status: KeyTrustStatus = KeyTrustStatus.UNKNOWN
    algorithm: str = "ECDSA-P256-SHA256"
    message: str = ""

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return {
            "status": self.status.value,
            "key_id": self.key_id,
            "key_trust_status": self.key_trust_status.value,
            "algorithm": self.algorithm,
            "message": self.message,
        }


def sign_canonical_bytes(data: bytes, private_key: ec.EllipticCurvePrivateKey) -> str:
    """
    Sign raw canonical bytes using ECDSA with NIST P-256 and SHA-256.

    Args:
        data: Raw byte payload.
        private_key: Loaded EllipticCurvePrivateKey.

    Returns:
        Standard Base64-encoded DER signature string.

    Raises:
        ValueError: If data is empty or key is not EllipticCurvePrivateKey.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError(f"Expected bytes for signing, got {type(data).__name__}")
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("Invalid private key provided for signing.")

    # Cryptography library signs using DER-encoded ASN.1 sequence (r, s)
    der_signature = private_key.sign(bytes(data), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(der_signature).decode("ascii")


def sign_record(record: Dict[str, Any], private_key: ec.EllipticCurvePrivateKey) -> str:
    """
    Canonicalize a provenance record and sign it using ECDSA P-256 / SHA-256.

    Args:
        record: Provenance record dictionary conforming to TruthLens schema.
        private_key: Authorized ECDSA private key.

    Returns:
        Base64-encoded signature string.

    Raises:
        CanonicalizationError: If record fails schema validation.
    """
    canonical_bytes = canonicalize_record(record)
    return sign_canonical_bytes(canonical_bytes, private_key)


def verify_canonical_bytes_signature(
    data: bytes,
    signature_b64: str,
    public_key: ec.EllipticCurvePublicKey,
) -> bool:
    """
    Safely verify a Base64-encoded DER ECDSA signature over canonical bytes.

    Returns:
        True if signature mathematically verifies, False otherwise.
    """
    if not isinstance(data, (bytes, bytearray)) or not isinstance(signature_b64, str):
        return False

    try:
        raw_signature = base64.b64decode(signature_b64.strip(), validate=True)
    except Exception:
        return False

    try:
        public_key.verify(raw_signature, bytes(data), ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


def verify_record_signature(
    record: Dict[str, Any],
    signature_b64: Optional[str],
    public_key: Optional[ec.EllipticCurvePublicKey] = None,
    key_registry: Optional[KeyRegistry] = None,
) -> SignatureVerificationResult:
    """
    Verify the digital signature of a provenance record, evaluating both
    cryptographic validity and key trust status.

    Args:
        record: The provenance record dictionary.
        signature_b64: The Base64 DER signature string, or None if missing.
        public_key: Optional public key for verification. If omitted, it will
                    be looked up from key_registry using record['signing_key_id'].
        key_registry: Optional KeyRegistry to evaluate trust and look up public keys.

    Returns:
        Structured SignatureVerificationResult.
    """
    # 1. Check for missing signature
    if signature_b64 is None or not str(signature_b64).strip():
        return SignatureVerificationResult(
            status=SignatureStatus.MISSING,
            key_id=record.get("signing_key_id") if isinstance(record, dict) else None,
            key_trust_status=KeyTrustStatus.UNKNOWN,
            algorithm="ECDSA-P256-SHA256",
            message="No digital signature provided with record.",
        )

    # 2. Extract and validate key_id and canonicalize record
    try:
        canonical_bytes = canonicalize_record(record)
    except CanonicalizationError as exc:
        return SignatureVerificationResult(
            status=SignatureStatus.MALFORMED,
            key_id=record.get("signing_key_id") if isinstance(record, dict) else None,
            key_trust_status=KeyTrustStatus.UNKNOWN,
            algorithm="ECDSA-P256-SHA256",
            message=f"Provenance record payload is malformed: {exc}",
        )
    except Exception as exc:
        return SignatureVerificationResult(
            status=SignatureStatus.MALFORMED,
            key_id=record.get("signing_key_id") if isinstance(record, dict) else None,
            key_trust_status=KeyTrustStatus.UNKNOWN,
            algorithm="ECDSA-P256-SHA256",
            message=f"Failed to process record for verification: {exc}",
        )

    key_id = record.get("signing_key_id")

    # 3. Evaluate key trust via registry
    key_trust_status = KeyTrustStatus.UNKNOWN
    resolved_public_key = public_key

    if key_registry is not None and key_id:
        trust_status, key_record = key_registry.evaluate_key_trust(key_id)
        key_trust_status = trust_status

        if resolved_public_key is None and key_record is not None:
            try:
                resolved_public_key = load_public_key_pem(key_record.public_key_pem)
            except Exception:
                pass

    if resolved_public_key is None:
        return SignatureVerificationResult(
            status=SignatureStatus.MALFORMED,
            key_id=key_id,
            key_trust_status=key_trust_status,
            algorithm="ECDSA-P256-SHA256",
            message=f"Verification key could not be resolved for key_id '{key_id}'. "
                    "Public key must be supplied directly or present in the trusted registry.",
        )

    # 4. Decode signature bytes safely
    try:
        sig_bytes = base64.b64decode(signature_b64.strip(), validate=True)
    except Exception as exc:
        return SignatureVerificationResult(
            status=SignatureStatus.MALFORMED,
            key_id=key_id,
            key_trust_status=key_trust_status,
            algorithm="ECDSA-P256-SHA256",
            message=f"Signature is not a valid base64 string: {exc}",
        )

    # 4b. Validate ASN.1 DER structure of the ECDSA signature
    try:
        decode_dss_signature(sig_bytes)
    except Exception as exc:
        return SignatureVerificationResult(
            status=SignatureStatus.MALFORMED,
            key_id=key_id,
            key_trust_status=key_trust_status,
            algorithm="ECDSA-P256-SHA256",
            message=f"Malformed signature structure (invalid ASN.1/DER encoding): {exc}",
        )

    # 5. Cryptographic verification under public key
    try:
        resolved_public_key.verify(sig_bytes, canonical_bytes, ec.ECDSA(hashes.SHA256()))
        is_math_valid = True
    except InvalidSignature:
        is_math_valid = False
    except Exception as exc:
        return SignatureVerificationResult(
            status=SignatureStatus.MALFORMED,
            key_id=key_id,
            key_trust_status=key_trust_status,
            algorithm="ECDSA-P256-SHA256",
            message=f"Malformed signature structure (invalid ASN.1/DER encoding): {exc}",
        )

    if not is_math_valid:
        return SignatureVerificationResult(
            status=SignatureStatus.INVALID,
            key_id=key_id,
            key_trust_status=key_trust_status,
            algorithm="ECDSA-P256-SHA256",
            message="Digital signature does not match canonical record content or was signed with a different key.",
        )

    # 6. Mathematically valid: build descriptive message regarding trust
    if key_trust_status == KeyTrustStatus.TRUSTED:
        trust_msg = f"Key '{key_id}' is TRUSTED in the authority registry."
    elif key_trust_status == KeyTrustStatus.REVOKED:
        trust_msg = f"WARNING: Key '{key_id}' is REVOKED. Signature is mathematically valid but UNTRUSTED."
    elif key_trust_status == KeyTrustStatus.EXPIRED:
        trust_msg = f"WARNING: Key '{key_id}' is EXPIRED. Signature was signed by an expired key."
    else:
        trust_msg = f"Key '{key_id}' is UNKNOWN in the registry. Mathematical validity verified, but signer authority cannot be established."

    return SignatureVerificationResult(
        status=SignatureStatus.VALID,
        key_id=key_id,
        key_trust_status=key_trust_status,
        algorithm="ECDSA-P256-SHA256",
        message=f"Signature mathematically verified under public key. {trust_msg}",
    )
