"""
TruthLens Canonicalization Module
Member 2: Cryptography & Information Security

Implements deterministic JSON serialization and schema validation for
TruthLens digital provenance records in adherence to RFC 8785 principles.

CANONICALIZATION RULES:
1. Deterministic Key Ordering: Keys are sorted lexicographically at all nesting levels.
2. Compact Separators: No whitespace around separators (',' and ':').
3. Strict UTF-8: Direct UTF-8 byte serialization without ASCII escaping (ensure_ascii=False).
4. No Float Ambiguity: IEEE 754 floats are not permitted in integrity hashes; standard integers or
   normalized strings are used.
5. Signature Exclusion: The 'signature' field is explicitly excluded from canonical bytes.
6. Secrets Rejection: Records containing private keys, passwords, or tokens are rejected.
"""

from __future__ import annotations

import datetime
import json
import re
from typing import Any, Dict, Set

# Supported schema versions
SUPPORTED_SCHEMA_VERSIONS: Set[str] = {"1.0"}

# Allowed media content types for MVP
ALLOWED_CONTENT_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Forbidden keywords in provenance records to prevent secret leakage
FORBIDDEN_SENSITIVE_KEYS: Set[str] = {
    "private_key",
    "secret",
    "password",
    "token",
    "api_key",
    "private_pem",
    "authorization",
}

# Standard 64-character SHA-256 hex regex
SHA256_REGEX = re.compile(r"^[0-9a-f]{64}$")


class CanonicalizationError(ValueError):
    """Raised when record fails schema validation or canonicalization."""
    pass


def validate_iso8601_timestamp(timestamp_str: str) -> None:
    """
    Validate that timestamp is a strict ISO-8601 string with UTC indicator or timezone offset.

    Examples: '2026-10-26T10:30:00Z', '2026-10-26T10:30:00+00:00'.
    """
    if not isinstance(timestamp_str, str) or not timestamp_str.strip():
        raise CanonicalizationError("Field 'registered_at' must be a non-empty ISO-8601 string.")
    
    clean_ts = timestamp_str.strip()
    try:
        # datetime.fromisoformat handles standard ISO 8601 in Python 3.11+
        # normalize trailing 'Z' if needed
        ts_for_parse = clean_ts.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(ts_for_parse)
        if dt.tzinfo is None:
            raise CanonicalizationError(
                f"Field 'registered_at' ('{timestamp_str}') must include timezone information (e.g., UTC 'Z' or offset)."
            )
    except Exception as exc:
        raise CanonicalizationError(f"Field 'registered_at' is not a valid ISO-8601 timestamp: {exc}") from exc


def validate_provenance_record_schema(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that a dictionary conforms to the TruthLens Provenance Record schema.

    Required fields:
        - schema_version (str, currently "1.0")
        - asset_id (str, non-empty)
        - sha256 (str, 64 hex characters)
        - registered_at (str, ISO-8601 UTC timestamp)
        - signing_key_id (str, non-empty)
        - content_type (str, e.g. "image/jpeg", "image/png", "image/webp")

    Optional fields:
        - issuer_id (str, non-empty)
        - metadata (dict, arbitrary JSON-serializable key-values)

    Forbidden:
        - Passwords, private keys, secrets, tokens
        - Unsupported schema versions

    Returns:
        A sanitized shallow copy of the record with 'signature' excluded.
    """
    if not isinstance(record, dict):
        raise CanonicalizationError(f"Record must be a dictionary, got {type(record).__name__}")

    # Check for forbidden sensitive fields
    for key in record.keys():
        key_lower = str(key).lower()
        if any(secret_term in key_lower for secret_term in FORBIDDEN_SENSITIVE_KEYS):
            raise CanonicalizationError(
                f"Security violation: Record contains sensitive field '{key}'. "
                "Secrets and private keys must NEVER be stored in provenance records."
            )

    # 1. schema_version
    schema_version = record.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise CanonicalizationError(
            f"Unsupported or missing 'schema_version': '{schema_version}'. "
            f"Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    # 2. asset_id
    asset_id = record.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id.strip():
        raise CanonicalizationError("Field 'asset_id' must be a non-empty string.")

    # 3. sha256
    digest = record.get("sha256")
    if not isinstance(digest, str) or not SHA256_REGEX.match(digest.strip().lower()):
        raise CanonicalizationError(
            f"Field 'sha256' must be a 64-character lowercase hexadecimal string, got '{digest}'."
        )

    # 4. registered_at
    registered_at = record.get("registered_at")
    validate_iso8601_timestamp(registered_at)

    # 5. signing_key_id
    signing_key_id = record.get("signing_key_id")
    if not isinstance(signing_key_id, str) or not signing_key_id.strip():
        raise CanonicalizationError("Field 'signing_key_id' must be a non-empty string.")

    # 6. content_type
    content_type = record.get("content_type")
    if not isinstance(content_type, str) or content_type.strip().lower() not in ALLOWED_CONTENT_TYPES:
        raise CanonicalizationError(
            f"Field 'content_type' must be one of {sorted(ALLOWED_CONTENT_TYPES)}, got '{content_type}'."
        )

    # 7. issuer_id (optional)
    issuer_id = record.get("issuer_id")
    if issuer_id is not None and (not isinstance(issuer_id, str) or not issuer_id.strip()):
        raise CanonicalizationError("Field 'issuer_id', if provided, must be a non-empty string.")

    # 8. metadata (optional)
    metadata = record.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise CanonicalizationError("Field 'metadata', if provided, must be a dictionary.")

    # Build clean record payload, strictly excluding signature
    clean_record: Dict[str, Any] = {
        "schema_version": schema_version.strip(),
        "asset_id": asset_id.strip(),
        "sha256": digest.strip().lower(),
        "registered_at": registered_at.strip(),
        "signing_key_id": signing_key_id.strip(),
        "content_type": content_type.strip().lower(),
    }
    if issuer_id is not None:
        clean_record["issuer_id"] = issuer_id.strip()
    if metadata is not None:
        clean_record["metadata"] = metadata

    return clean_record


def canonicalize_json(data: Any) -> bytes:
    """
    Serialize any JSON-serializable Python data structure into deterministic UTF-8 bytes.

    Features:
    - Sort keys lexicographically.
    - Compact separators (no trailing or inline spaces).
    - ensure_ascii=False for direct UTF-8 preservation.
    - Disallow NaN and Infinity.
    """
    try:
        json_str = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return json_str.encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise CanonicalizationError(f"Failed to canonicalize data to JSON: {exc}") from exc


def canonicalize_record(record: Dict[str, Any]) -> bytes:
    """
    Validate a provenance record against the schema and serialize it into canonical bytes.

    Note:
    - If the input record contains a 'signature' key, it is excluded so that
      the returned canonical bytes represent the exact unsigned payload.
    - Keys are sorted deterministically.
    - Output is strict UTF-8 encoded bytes.

    Args:
        record: The provenance record dictionary.

    Returns:
        Canonical UTF-8 bytes ready for signing or verification.

    Raises:
        CanonicalizationError: If schema validation fails.
    """
    validated = validate_provenance_record_schema(record)
    return canonicalize_json(validated)
