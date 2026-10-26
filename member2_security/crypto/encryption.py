"""
TruthLens Authenticated Encryption Module
Member 2: Cryptography & Information Security

Implements authenticated symmetric encryption using AES-256-GCM via the
cryptography.hazmat.primitives.ciphers.aead.AESGCM primitive.

CRITICAL SECURITY PRINCIPLES:
1. AES-256-GCM AEAD:
   Provides both confidentiality (AES-256) and integrity/authenticity (128-bit GHASH tag).
2. Fresh 96-bit Nonces:
   Every encryption generates a fresh, cryptographically secure 12-byte nonce via os.urandom.
   Nonces are NEVER reused under the same key.
3. Associated Authenticated Data (AAD):
   AAD is cryptographically authenticated by the GCM tag, guaranteeing contextual binding,
   but is NOT encrypted (remains plaintext).
4. All-or-Nothing Decryption:
   If ciphertext, nonce, tag, or AAD is modified by even one bit, or if the wrong key is
   provided, decryption fails completely. Partially decrypted or unauthenticated plaintext
   is NEVER returned.
5. No Secrets in Envelope:
   The encrypted envelope contains version, algorithm, key_id, nonce, and ciphertext+tag,
   but NEVER the secret key.
"""

from __future__ import annotations

import base64
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Cryptographic constants for AES-GCM
AES_256_KEY_BYTES = 32  # 256 bits
GCM_NONCE_BYTES = 12    # 96 bits (standard recommended GCM nonce length)
GCM_TAG_BYTES = 16      # 128 bits (AESGCM appends this tag to ciphertext)
ENVELOPE_VERSION = "1.0"
ALGORITHM_IDENTIFIER = "AES-256-GCM"


class EncryptionError(Exception):
    """Base exception for encryption and decryption errors."""
    pass


class DecryptionAuthenticationError(EncryptionError):
    """Raised when ciphertext authentication tag verification fails."""
    pass


class InvalidEnvelopeError(EncryptionError):
    """Raised when the encrypted envelope structure is malformed or invalid."""
    pass


@dataclass(frozen=True)
class EncryptedEnvelope:
    """
    Versioned container for ciphertext and cryptographic parameters.
    Does NOT contain the secret decryption key.
    """
    version: str
    algorithm: str
    key_id: str
    nonce: str  # Base64-encoded 12-byte nonce
    ciphertext_and_tag: str  # Base64-encoded ciphertext with appended 16-byte authentication tag
    aad_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert envelope to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EncryptedEnvelope:
        """Parse and validate an envelope from dictionary format."""
        if not isinstance(data, dict):
            raise InvalidEnvelopeError(f"Envelope must be a dict, got {type(data).__name__}")

        required = {"version", "algorithm", "key_id", "nonce", "ciphertext_and_tag"}
        missing = required - set(data.keys())
        if missing:
            raise InvalidEnvelopeError(f"Envelope missing required fields: {missing}")

        if data["algorithm"] != ALGORITHM_IDENTIFIER:
            raise InvalidEnvelopeError(
                f"Unsupported algorithm '{data.get('algorithm')}'. Expected '{ALGORITHM_IDENTIFIER}'."
            )

        return cls(
            version=str(data["version"]),
            algorithm=str(data["algorithm"]),
            key_id=str(data["key_id"]),
            nonce=str(data["nonce"]),
            ciphertext_and_tag=str(data["ciphertext_and_tag"]),
            aad_version=str(data["aad_version"]) if data.get("aad_version") is not None else None,
        )


def encrypt_bytes(
    plaintext: Union[bytes, bytearray, memoryview],
    key: bytes,
    key_id: str,
    aad: Optional[bytes] = None,
    aad_version: Optional[str] = None,
) -> EncryptedEnvelope:
    """
    Encrypt plaintext bytes using AES-256-GCM with a fresh 12-byte nonce.

    Args:
        plaintext: Raw data to encrypt.
        key: 32-byte (256-bit) symmetric AES key.
        key_id: Identifier of the key used (for key management/rotation).
        aad: Optional Associated Authenticated Data to bind to the ciphertext.
        aad_version: Optional version identifier for AAD structure.

    Returns:
        EncryptedEnvelope containing base64 parameters and ciphertext+tag.

    Raises:
        EncryptionError: If parameters are invalid or key length is not 32 bytes.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) != AES_256_KEY_BYTES:
        raise EncryptionError(
            f"AES-256 requires exactly {AES_256_KEY_BYTES} bytes key, got {len(key) if hasattr(key, '__len__') else type(key)}"
        )

    if not isinstance(plaintext, (bytes, bytearray, memoryview)):
        raise EncryptionError(f"Plaintext must be bytes-like, got {type(plaintext).__name__}")

    if not key_id or not isinstance(key_id, str):
        raise EncryptionError("key_id must be a non-empty string.")

    # Generate fresh cryptographically secure random 12-byte nonce
    nonce = os.urandom(GCM_NONCE_BYTES)

    try:
        aesgcm = AESGCM(bytes(key))
        # AESGCM.encrypt returns ciphertext with appended 16-byte authentication tag
        ct_and_tag = aesgcm.encrypt(nonce, bytes(plaintext), aad)
    except Exception as exc:
        raise EncryptionError(f"Encryption failed: {exc}") from exc

    return EncryptedEnvelope(
        version=ENVELOPE_VERSION,
        algorithm=ALGORITHM_IDENTIFIER,
        key_id=key_id.strip(),
        nonce=base64.b64encode(nonce).decode("ascii"),
        ciphertext_and_tag=base64.b64encode(ct_and_tag).decode("ascii"),
        aad_version=aad_version,
    )


def decrypt_bytes(
    envelope: Union[EncryptedEnvelope, Dict[str, Any]],
    key: bytes,
    aad: Optional[bytes] = None,
) -> bytes:
    """
    Decrypt and verify an AES-256-GCM encrypted envelope.

    Args:
        envelope: EncryptedEnvelope instance or serialized dictionary.
        key: 32-byte (256-bit) symmetric AES key matching the envelope's key.
        aad: Optional Associated Authenticated Data that was bound during encryption.

    Returns:
        Decrypted raw plaintext bytes.

    Raises:
        DecryptionAuthenticationError: If the ciphertext, nonce, tag, key, or AAD has been
                                       tampered with or does not match.
        InvalidEnvelopeError: If the envelope cannot be parsed.
        EncryptionError: If the key length is invalid.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) != AES_256_KEY_BYTES:
        raise EncryptionError(
            f"AES-256 requires exactly {AES_256_KEY_BYTES} bytes key, got {len(key) if hasattr(key, '__len__') else type(key)}"
        )

    if isinstance(envelope, dict):
        env = EncryptedEnvelope.from_dict(envelope)
    elif isinstance(envelope, EncryptedEnvelope):
        env = envelope
    else:
        raise InvalidEnvelopeError(f"Expected EncryptedEnvelope or dict, got {type(envelope).__name__}")

    # Decode nonce
    try:
        nonce = base64.b64decode(env.nonce, validate=True)
        if len(nonce) != GCM_NONCE_BYTES:
            raise InvalidEnvelopeError(
                f"Invalid nonce length: expected {GCM_NONCE_BYTES} bytes, got {len(nonce)}"
            )
    except Exception as exc:
        raise InvalidEnvelopeError(f"Failed to decode base64 nonce: {exc}") from exc

    # Decode ciphertext and tag
    try:
        ct_and_tag = base64.b64decode(env.ciphertext_and_tag, validate=True)
        if len(ct_and_tag) < GCM_TAG_BYTES:
            raise InvalidEnvelopeError(
                f"Ciphertext too short to contain {GCM_TAG_BYTES}-byte authentication tag."
            )
    except Exception as exc:
        raise InvalidEnvelopeError(f"Failed to decode base64 ciphertext: {exc}") from exc

    # Authenticated Decryption
    try:
        aesgcm = AESGCM(bytes(key))
        plaintext = aesgcm.decrypt(nonce, ct_and_tag, aad)
        return plaintext
    except InvalidTag as exc:
        raise DecryptionAuthenticationError(
            "Authentication tag verification failed. Ciphertext, key, nonce, or associated data "
            "has been tampered with or is invalid."
        ) from exc
    except Exception as exc:
        raise DecryptionAuthenticationError(f"Decryption failed: {exc}") from exc
