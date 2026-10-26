"""
TruthLens Key Management Utilities
Member 2: Cryptography & Information Security

Provides utilities for generating, serializing, loading, and validating
cryptographic keys used in TruthLens:
- ECDSA NIST P-256 (SECP256R1) signing keys with optional password encryption (PKCS#8).
- AES-256 (256-bit symmetric keys) for authenticated encryption.
- Secure key generation, loading, and file storage with restrictive permissions.

SECURITY RULES:
1. Private keys must NEVER be logged, serialized to public APIs, or committed to Git.
2. File permissions for private key files must be restricted (0600 on UNIX).
3. Missing required keys must raise clear exceptions, NEVER silently generate new keys.
4. Loss of an encryption key renders all associated ciphertexts permanently unrecoverable.
"""

from __future__ import annotations

import base64
import os
import secrets
import stat
from pathlib import Path
from typing import Optional, Tuple, Union

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


class KeyManagementError(Exception):
    """Raised when key loading, parsing, generation, or validation fails."""
    pass


class MissingKeyError(KeyManagementError):
    """Raised when a required key file or environment variable is missing."""
    pass


def generate_ecdsa_key_pair(
    password: Optional[str] = None,
) -> Tuple[bytes, bytes]:
    """
    Generate a new ECDSA NIST P-256 (SECP256R1) private/public key pair in PEM format.

    Args:
        password: Optional passphrase to encrypt the private key file. If provided,
                  the private key is encrypted with PBKDF2 HMAC-SHA256 and AES-256-CBC
                  via BestAvailableEncryption. If None, NoEncryption is used.

    Returns:
        A tuple of (private_key_pem_bytes, public_key_pem_bytes).
    """
    # 1. Generate private key on NIST P-256
    private_key = ec.generate_private_key(ec.SECP256R1())

    # 2. Configure private key encryption
    if password is not None and len(password.strip()) > 0:
        encryption_algorithm: serialization.KeySerializationEncryption = (
            serialization.BestAvailableEncryption(password.encode("utf-8"))
        )
    else:
        encryption_algorithm = serialization.NoEncryption()

    # 3. Export private key in PKCS#8 format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm,
    )

    # 4. Export public key in SubjectPublicKeyInfo format
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def load_private_key_pem(
    pem_bytes: Union[bytes, str],
    password: Optional[str] = None,
) -> ec.EllipticCurvePrivateKey:
    """
    Load and validate an ECDSA private key from PEM bytes.

    Args:
        pem_bytes: Raw PEM byte data or string.
        password: Password string if the private key was encrypted, otherwise None.

    Returns:
        ec.EllipticCurvePrivateKey instance.

    Raises:
        KeyManagementError: If key is corrupt, wrong curve, or wrong password.
    """
    if isinstance(pem_bytes, str):
        data = pem_bytes.encode("utf-8")
    elif isinstance(pem_bytes, (bytes, bytearray)):
        data = bytes(pem_bytes)
    else:
        raise KeyManagementError(f"Expected bytes or string for PEM, got {type(pem_bytes).__name__}")

    pwd_bytes = password.encode("utf-8") if password is not None else None

    try:
        loaded_key = serialization.load_pem_private_key(data, password=pwd_bytes)
    except TypeError as exc:
        raise KeyManagementError(
            f"Private key loading error (password may be required or incorrect): {exc}"
        ) from exc
    except ValueError as exc:
        raise KeyManagementError(
            f"Failed to parse private key PEM (invalid format or bad password): {exc}"
        ) from exc
    except Exception as exc:
        raise KeyManagementError(f"Unexpected error loading private key: {exc}") from exc

    if not isinstance(loaded_key, ec.EllipticCurvePrivateKey):
        raise KeyManagementError(
            f"Expected EllipticCurvePrivateKey, but loaded key is {type(loaded_key).__name__}"
        )

    # Validate curve
    if not isinstance(loaded_key.curve, ec.SECP256R1):
        raise KeyManagementError(
            f"Security policy violation: Expected SECP256R1 (NIST P-256) curve, got {loaded_key.curve.name}."
        )

    return loaded_key


def load_public_key_pem(pem_bytes: Union[bytes, str]) -> ec.EllipticCurvePublicKey:
    """
    Load and validate an ECDSA public key from PEM bytes.

    Args:
        pem_bytes: Raw PEM byte data or string.

    Returns:
        ec.EllipticCurvePublicKey instance.

    Raises:
        KeyManagementError: If public key is corrupt or curve is not SECP256R1.
    """
    if isinstance(pem_bytes, str):
        data = pem_bytes.encode("utf-8")
    elif isinstance(pem_bytes, (bytes, bytearray)):
        data = bytes(pem_bytes)
    else:
        raise KeyManagementError(f"Expected bytes or string for PEM, got {type(pem_bytes).__name__}")

    try:
        loaded_key = serialization.load_pem_public_key(data)
    except Exception as exc:
        raise KeyManagementError(f"Failed to parse public key PEM: {exc}") from exc

    if not isinstance(loaded_key, ec.EllipticCurvePublicKey):
        raise KeyManagementError(
            f"Expected EllipticCurvePublicKey, but loaded key is {type(loaded_key).__name__}"
        )

    # Validate curve
    if not isinstance(loaded_key.curve, ec.SECP256R1):
        raise KeyManagementError(
            f"Security policy violation: Expected SECP256R1 (NIST P-256) curve, got {loaded_key.curve.name}."
        )

    return loaded_key


def export_public_key_pem(public_key: ec.EllipticCurvePublicKey) -> bytes:
    """Export an EllipticCurvePublicKey to SubjectPublicKeyInfo PEM bytes."""
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise KeyManagementError(f"Expected EllipticCurvePublicKey, got {type(public_key).__name__}")
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def export_private_key_pem(
    private_key: ec.EllipticCurvePrivateKey,
    password: Optional[str] = None,
) -> bytes:
    """Export an EllipticCurvePrivateKey to PKCS#8 PEM bytes with optional password encryption."""
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise KeyManagementError(f"Expected EllipticCurvePrivateKey, got {type(private_key).__name__}")

    if password is not None and len(password.strip()) > 0:
        enc = serialization.BestAvailableEncryption(password.encode("utf-8"))
    else:
        enc = serialization.NoEncryption()

    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=enc,
    )


def generate_aes_key(length_bytes: int = 32) -> bytes:
    """
    Generate a cryptographically secure random symmetric key.

    Args:
        length_bytes: Key size in bytes (default 32 = 256 bits).

    Returns:
        Raw key bytes.
    """
    if length_bytes != 32:
        raise ValueError(f"TruthLens AES-256 requires exactly 32 bytes (256 bits), got {length_bytes}")
    return secrets.token_bytes(32)


def generate_key_id(prefix: str = "tl-key") -> str:
    """
    Generate a unique, structured identifier for a key (e.g. 'tl-key-a1b2c3d4e5f6').
    """
    rand_hex = secrets.token_hex(6)
    return f"{prefix}-{rand_hex}"


def save_key_pair_to_files(
    private_pem: bytes,
    public_pem: bytes,
    private_path: Union[str, Path],
    public_path: Union[str, Path],
    restrict_permissions: bool = True,
) -> None:
    """
    Save private and public PEM keys to disk.
    Applies restrictive file permissions (0600) on the private key file where supported (POSIX).
    """
    priv_file = Path(private_path)
    pub_file = Path(public_path)

    priv_file.parent.mkdir(parents=True, exist_ok=True)
    pub_file.parent.mkdir(parents=True, exist_ok=True)

    # Write private key
    with open(priv_file, "wb") as f:
        f.write(private_pem)

    # Restrict permissions on UNIX (owner read/write only)
    if restrict_permissions and os.name == "posix":
        try:
            priv_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except OSError:
            pass

    # Write public key
    with open(pub_file, "wb") as f:
        f.write(public_pem)
