"""
TruthLens File Integrity Verification Module
Member 2: Cryptography & Information Security

Implements raw-byte SHA-256 file integrity verification with chunked streaming,
format validation, constant-time comparison, and structured result evaluation.

CRITICAL SECURITY PRINCIPLES:
1. Integrity != Authenticity or Truth:
   A SHA-256 digest establishes byte-level identity relative to a reference record.
   It does NOT establish whether an image is genuine, synthetic, deepfaked, or
   factually true.
2. Mismatch Context:
   A mismatch indicates byte divergence. This can occur from re-compression,
   transcoding, metadata edits, or benign resizing, as well as malicious tampering.
3. No Pre-processing:
   Original media bytes are never silently normalized, re-encoded, or altered
   prior to hashing.
4. Constant-Time Comparison:
   All digest comparisons use hmac.compare_digest to eliminate timing side-channels.
5. Reference Handling:
   An absent reference digest returns NO_REFERENCE and is never conflated with
   a MATCH or MISMATCH.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Optional, Union

# Standard 64-character hex pattern for SHA-256
SHA256_HEX_REGEX = re.compile(r"^[0-9a-f]{64}$")

# Default streaming chunk size: 64 KB (optimal for balance of I/O performance and memory footprint)
DEFAULT_CHUNK_SIZE = 65536


class IntegrityStatus(str, enum.Enum):
    """Integrity evaluation outcome status."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NO_REFERENCE = "NO_REFERENCE"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class IntegrityResult:
    """Structured result returned by file integrity evaluation."""

    status: IntegrityStatus
    algorithm: str = "sha256"
    current_sha256: Optional[str] = None
    reference_sha256: Optional[str] = None
    bytes_hashed: Optional[int] = None
    message: str = ""

    def to_dict(self) -> dict:
        """Serialize result to a JSON-compatible dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


def is_valid_sha256_hex(digest: Optional[str]) -> bool:
    """
    Validate whether a string is a well-formed 64-character hexadecimal SHA-256 digest.

    Args:
        digest: The digest string to validate.

    Returns:
        True if the string is non-empty and contains exactly 64 hexadecimal characters,
        False otherwise.
    """
    if not digest or not isinstance(digest, str):
        return False
    return bool(SHA256_HEX_REGEX.match(digest.strip().lower()))


def normalize_sha256(digest: str) -> str:
    """
    Normalize a SHA-256 digest string to stripped lowercase hexadecimal.

    Args:
        digest: Raw hex string.

    Returns:
        Lowercase normalized 64-character hex string.

    Raises:
        ValueError: If the string is not a valid 64-character hex digest.
    """
    if not isinstance(digest, str):
        raise ValueError(f"Expected digest string, got {type(digest).__name__}")
    normalized = digest.strip().lower()
    if not SHA256_HEX_REGEX.match(normalized):
        raise ValueError(f"Invalid SHA-256 hex digest: '{digest}' (expected 64 hex characters)")
    return normalized


def sha256_bytes(data: Union[bytes, bytearray, memoryview]) -> str:
    """
    Compute lowercase hexadecimal SHA-256 digest of raw byte content.

    Args:
        data: Raw binary data.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.

    Raises:
        TypeError: If input data is not bytes, bytearray, or memoryview.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"Expected bytes-like object, got {type(data).__name__}")
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest().lower()


def sha256_stream(stream: BinaryIO, chunk_size: int = DEFAULT_CHUNK_SIZE) -> tuple[str, int]:
    """
    Compute SHA-256 digest of a binary stream in chunks to minimize memory consumption.

    Args:
        stream: Readable binary stream.
        chunk_size: Size of byte chunks to read per iteration (default 64 KB).

    Returns:
        A tuple of (lowercase hex digest, total bytes read).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    hasher = hashlib.sha256()
    total_bytes = 0

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        total_bytes += len(chunk)

    return hasher.hexdigest().lower(), total_bytes


def sha256_file(path: Union[str, Path], chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """
    Compute lowercase hexadecimal SHA-256 digest of a file on disk using chunked streaming.

    Args:
        path: Filepath to hash.
        chunk_size: Streaming chunk size in bytes (default 64 KB).

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.

    Raises:
        FileNotFoundError: If the target file does not exist.
        IsADirectoryError: If path refers to a directory.
        PermissionError: If file read permission is denied.
        ValueError: If path is invalid or chunk_size <= 0.
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    if target.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {target}")

    with open(target, "rb") as f:
        digest, _ = sha256_stream(f, chunk_size=chunk_size)
        return digest


def verify_file_integrity(
    file_path: Union[str, Path],
    reference_hash: Optional[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> IntegrityResult:
    """
    Stream a file on disk, compute its SHA-256 digest, and compare against a reference.

    Args:
        file_path: Path to the target file.
        reference_hash: Trusted registered SHA-256 hex digest, or None if unregistered.
        chunk_size: Streaming chunk size.

    Returns:
        IntegrityResult with evaluation status and metadata.
    """
    try:
        target = Path(file_path)
        if not target.exists() or not target.is_file():
            return IntegrityResult(
                status=IntegrityStatus.INVALID_INPUT,
                algorithm="sha256",
                current_sha256=None,
                reference_sha256=reference_hash,
                message=f"Target file does not exist or is not a file: {file_path}",
            )

        with open(target, "rb") as f:
            current_hash, total_bytes = sha256_stream(f, chunk_size=chunk_size)

        result = compare_hashes(current_hash=current_hash, reference_hash=reference_hash)
        return IntegrityResult(
            status=result.status,
            algorithm="sha256",
            current_sha256=current_hash,
            reference_sha256=result.reference_sha256,
            bytes_hashed=total_bytes,
            message=result.message,
        )
    except Exception as exc:
        return IntegrityResult(
            status=IntegrityStatus.INVALID_INPUT,
            algorithm="sha256",
            current_sha256=None,
            reference_sha256=reference_hash,
            message=f"Failed to read file for hashing: {exc}",
        )


def compare_hashes(
    current_hash: Optional[str],
    reference_hash: Optional[str],
    bytes_hashed: Optional[int] = None,
) -> IntegrityResult:
    """
    Compare a computed current SHA-256 hash with an expected reference hash
    using constant-time comparison to prevent timing leaks.

    Outcomes:
        - NO_REFERENCE: Reference hash is None, empty, or whitespace.
        - INVALID_INPUT: Either current_hash is invalid or reference_hash is malformed.
        - MATCH: Both digests are valid and byte-for-byte identical.
        - MISMATCH: Both digests are valid but differ.

    Args:
        current_hash: The newly computed SHA-256 hex digest.
        reference_hash: The trusted reference SHA-256 hex digest (or None).
        bytes_hashed: Optional count of bytes hashed.

    Returns:
        Structured IntegrityResult.
    """
    # 1. Check for absence of reference
    if reference_hash is None or (isinstance(reference_hash, str) and not reference_hash.strip()):
        valid_curr = current_hash.strip().lower() if is_valid_sha256_hex(current_hash) else None
        return IntegrityResult(
            status=IntegrityStatus.NO_REFERENCE,
            algorithm="sha256",
            current_sha256=valid_curr,
            reference_sha256=None,
            bytes_hashed=bytes_hashed,
            message="No trusted reference digest provided for comparison. "
                    "File identity cannot be verified against a baseline.",
        )

    # 2. Validate current hash format
    if not is_valid_sha256_hex(current_hash):
        return IntegrityResult(
            status=IntegrityStatus.INVALID_INPUT,
            algorithm="sha256",
            current_sha256=current_hash,
            reference_sha256=reference_hash,
            bytes_hashed=bytes_hashed,
            message=f"Current hash is invalid: expected 64 hex characters, got '{current_hash}'.",
        )

    # 3. Validate reference hash format
    if not is_valid_sha256_hex(reference_hash):
        return IntegrityResult(
            status=IntegrityStatus.INVALID_INPUT,
            algorithm="sha256",
            current_sha256=current_hash.strip().lower() if current_hash else None,
            reference_sha256=reference_hash,
            bytes_hashed=bytes_hashed,
            message=f"Reference hash is malformed: expected 64 hex characters, got '{reference_hash}'.",
        )

    norm_current = current_hash.strip().lower()
    norm_reference = reference_hash.strip().lower()

    # 4. Constant-time comparison
    is_match = hmac.compare_digest(norm_current.encode("ascii"), norm_reference.encode("ascii"))

    if is_match:
        return IntegrityResult(
            status=IntegrityStatus.MATCH,
            algorithm="sha256",
            current_sha256=norm_current,
            reference_sha256=norm_reference,
            bytes_hashed=bytes_hashed,
            message="Current file digest matches reference digest byte-for-byte. "
                    "File has identical binary content to the registered record.",
        )
    else:
        return IntegrityResult(
            status=IntegrityStatus.MISMATCH,
            algorithm="sha256",
            current_sha256=norm_current,
            reference_sha256=norm_reference,
            bytes_hashed=bytes_hashed,
            message="Current file digest does NOT match reference digest. "
                    "Note: digest divergence indicates binary byte-level difference; "
                    "it does not by itself establish whether divergence is due to format "
                    "transcoding, re-saving, metadata changes, or malicious manipulation.",
        )
