"""
TruthLens Key Registry & Rotation Module
Member 2: Cryptography & Information Security

Maintains a secure, audited registry of public keys, their lifecycle status
(ACTIVE, RETIRED, REVOKED), and validity windows.

CRITICAL SECURITY DESIGN:
1. Validity vs Trust Separation:
   Mathematical signature validity only proves possession of the private key
   corresponding to the public key. It does NOT prove the key belongs to a
   trusted TruthLens authority.
2. Historic Verification Support:
   When an active signing key is rotated to 'RETIRED', historical provenance records
   previously signed with it remain valid and trusted.
3. Revocation Enforcement:
   If a key is compromised, marking it 'REVOKED' immediately prevents new signatures
   and invalidates trust on any provenance record referencing it.
4. No Private Keys in Registry:
   The registry stores ONLY public keys, identifiers, and lifecycle metadata.
"""

from __future__ import annotations

import datetime
import enum
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from member2_security.key_management.key_utils import (
    KeyManagementError,
    load_public_key_pem,
)


class KeyLifecycleStatus(str, enum.Enum):
    """Lifecycle status of a key in the registry."""
    ACTIVE = "ACTIVE"      # Currently authorized for signing new records
    RETIRED = "RETIRED"    # Former active key; valid for historical verification, forbidden for new signing
    REVOKED = "REVOKED"    # Compromised or invalidated; untrusted for all records


class KeyTrustStatus(str, enum.Enum):
    """Trust evaluation result for a key associated with a provenance record."""
    TRUSTED = "TRUSTED"    # Key is ACTIVE or RETIRED, within valid timeframe
    REVOKED = "REVOKED"    # Key is marked as revoked
    EXPIRED = "EXPIRED"    # Key expiration date has passed
    UNKNOWN = "UNKNOWN"    # Key is not present in the trusted registry


@dataclass
class KeyRecord:
    """Public key entry stored in the registry."""
    key_id: str
    algorithm: str  # e.g. "ECDSA-P256-SHA256"
    status: KeyLifecycleStatus
    public_key_pem: str
    created_at: str  # ISO-8601 UTC
    description: str = ""
    expires_at: Optional[str] = None  # ISO-8601 UTC

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> KeyRecord:
        return cls(
            key_id=data["key_id"],
            algorithm=data["algorithm"],
            status=KeyLifecycleStatus(data["status"]),
            public_key_pem=data["public_key_pem"],
            created_at=data["created_at"],
            description=data.get("description", ""),
            expires_at=data.get("expires_at"),
        )


class KeyRegistry:
    """
    Manages trusted public keys, lifecycle transitions, and trust policy evaluation.
    """

    def __init__(self) -> None:
        self._keys: Dict[str, KeyRecord] = {}

    def register_key(
        self,
        key_id: str,
        public_key_pem: Union[bytes, str],
        status: KeyLifecycleStatus = KeyLifecycleStatus.ACTIVE,
        algorithm: str = "ECDSA-P256-SHA256",
        description: str = "",
        expires_at: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> KeyRecord:
        """
        Register a public key in the trusted registry.

        Args:
            key_id: Unique identifier for the key.
            public_key_pem: Public key PEM bytes or string.
            status: Lifecycle status (ACTIVE, RETIRED, REVOKED).
            algorithm: Cryptographic algorithm identifier.
            description: Human-readable description (e.g. 'Production Signing Key 2026').
            expires_at: Optional ISO-8601 expiration timestamp.
            created_at: Optional ISO-8601 creation timestamp (defaults to UTC now).

        Returns:
            The registered KeyRecord.
        """
        if not key_id or not isinstance(key_id, str):
            raise KeyManagementError("key_id must be a non-empty string.")

        pem_str = public_key_pem.decode("utf-8") if isinstance(public_key_pem, bytes) else public_key_pem

        # Validate that public key PEM can be loaded and is SECP256R1
        load_public_key_pem(pem_str)

        now_iso = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

        # If marking new key as ACTIVE, ensure single active key invariant per algorithm if desired
        record = KeyRecord(
            key_id=key_id.strip(),
            algorithm=algorithm,
            status=status,
            public_key_pem=pem_str.strip(),
            created_at=now_iso,
            description=description,
            expires_at=expires_at,
        )
        self._keys[record.key_id] = record
        return record

    def rotate_key(
        self,
        new_key_id: str,
        new_public_key_pem: Union[bytes, str],
        algorithm: str = "ECDSA-P256-SHA256",
        description: str = "Rotated active signing key",
    ) -> KeyRecord:
        """
        Rotate the currently active signing key:
        1. Find all currently ACTIVE keys with the matching algorithm and set them to RETIRED.
        2. Register the new key as ACTIVE.

        This ensures historical signatures from retired keys remain verifiable while
        new signatures use the fresh active key.
        """
        for record in self._keys.values():
            if record.algorithm == algorithm and record.status == KeyLifecycleStatus.ACTIVE:
                record.status = KeyLifecycleStatus.RETIRED

        return self.register_key(
            key_id=new_key_id,
            public_key_pem=new_public_key_pem,
            status=KeyLifecycleStatus.ACTIVE,
            algorithm=algorithm,
            description=description,
        )

    def revoke_key(self, key_id: str, reason: str = "Key revoked due to policy/compromise") -> None:
        """Revoke a key immediately, marking it untrusted."""
        if key_id not in self._keys:
            raise KeyManagementError(f"Cannot revoke unknown key: {key_id}")
        self._keys[key_id].status = KeyLifecycleStatus.REVOKED
        self._keys[key_id].description = f"{self._keys[key_id].description} [REVOKED: {reason}]"

    def get_key_record(self, key_id: str) -> Optional[KeyRecord]:
        """Retrieve key record by ID, or None if not found."""
        return self._keys.get(key_id)

    def get_active_key(self, algorithm: str = "ECDSA-P256-SHA256") -> Optional[KeyRecord]:
        """Find the currently ACTIVE key for a given algorithm."""
        for record in self._keys.values():
            if record.algorithm == algorithm and record.status == KeyLifecycleStatus.ACTIVE:
                return record
        return None

    def evaluate_key_trust(self, key_id: str) -> tuple[KeyTrustStatus, Optional[KeyRecord]]:
        """
        Evaluate the trust status of a given key ID according to the registry.

        Returns:
            (KeyTrustStatus, KeyRecord or None)
        """
        record = self.get_key_record(key_id)
        if record is None:
            return KeyTrustStatus.UNKNOWN, None

        if record.status == KeyLifecycleStatus.REVOKED:
            return KeyTrustStatus.REVOKED, record

        # Check expiration date if specified
        if record.expires_at:
            try:
                exp_dt = datetime.datetime.fromisoformat(record.expires_at.replace("Z", "+00:00"))
                now = datetime.datetime.now(datetime.timezone.utc)
                if now > exp_dt:
                    return KeyTrustStatus.EXPIRED, record
            except Exception:
                pass

        if record.status in (KeyLifecycleStatus.ACTIVE, KeyLifecycleStatus.RETIRED):
            return KeyTrustStatus.TRUSTED, record

        return KeyTrustStatus.UNKNOWN, record

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Persist registry to a JSON file."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {k: r.to_dict() for k, r in self._keys.items()}
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> KeyRegistry:
        """Load key registry from a JSON file."""
        target = Path(file_path)
        if not target.exists():
            raise KeyManagementError(f"Key registry file not found: {file_path}")

        registry = cls()
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key_id, rec_dict in data.items():
            registry._keys[key_id] = KeyRecord.from_dict(rec_dict)

        return registry
