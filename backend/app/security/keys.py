import json
from pathlib import Path
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import ec

from backend.app.config import settings
from member2_security.key_management.key_utils import (
    generate_ecdsa_key_pair,
    load_private_key_pem,
    load_public_key_pem,
)
from member2_security.key_management.registry import (
    KeyRegistry,
    KeyLifecycleStatus,
)


class CryptographyManager:
    """Manages ECDSA keys and KeyRegistry integration for the TruthLens application."""

    def __init__(self):
        self.active_key_id = settings.ACTIVE_KEY_ID
        self.private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self.key_registry: Optional[KeyRegistry] = None
        self._ensure_keys_exist()

    def _ensure_keys_exist(self) -> None:
        """
        Check if keys and registry exist; if not, safely initialize local development keys.
        """
        settings.SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        priv_path = settings.ECDSA_PRIVATE_KEY_PATH
        pub_path = settings.ECDSA_PUBLIC_KEY_PATH
        registry_path = settings.TRUSTED_KEYS_PATH

        if not priv_path.exists() or not pub_path.exists() or not registry_path.exists():
            print("[+] Initializing default TruthLens cryptographic signing keys & registry...")
            priv_pem, pub_pem = generate_ecdsa_key_pair(password=None)

            # Write private key with secure file permissions
            with open(priv_path, "wb") as f:
                f.write(priv_pem)

            with open(pub_path, "wb") as f:
                f.write(pub_pem)

            # Initialize trusted registry
            registry = KeyRegistry()
            registry.register_key(
                key_id=self.active_key_id,
                public_key_pem=pub_pem.decode("utf-8"),
                status=KeyLifecycleStatus.ACTIVE,
                algorithm="ECDSA-P256-SHA256",
                description="TruthLens Master Authority Signing Key",
            )
            registry.save_to_file(registry_path)
            self.key_registry = registry
        else:
            self.key_registry = KeyRegistry.load_from_file(registry_path)

        # Load private key into memory
        with open(priv_path, "rb") as f:
            priv_data = f.read()
        pwd = settings.ECDSA_PRIVATE_KEY_PASSWORD if settings.ECDSA_PRIVATE_KEY_PASSWORD else None
        self.private_key = load_private_key_pem(priv_data, password=pwd)

    def get_private_key(self) -> ec.EllipticCurvePrivateKey:
        if self.private_key is None:
            self._ensure_keys_exist()
        return self.private_key

    def get_registry(self) -> KeyRegistry:
        if self.key_registry is None:
            self._ensure_keys_exist()
        return self.key_registry


# Singleton instance
crypto_manager = CryptographyManager()
