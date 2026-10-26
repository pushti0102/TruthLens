"""
Unit and Security Tests for Key Management, Storage, and KeyRegistry
Member 2: Cryptography & Information Security
"""

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from member2_security.crypto.signatures import (
    SignatureStatus,
    sign_record,
    verify_record_signature,
)
from member2_security.key_management.key_utils import (
    KeyManagementError,
    MissingKeyError,
    export_private_key_pem,
    export_public_key_pem,
    generate_aes_key,
    generate_ecdsa_key_pair,
    generate_key_id,
    load_private_key_pem,
    load_public_key_pem,
    save_key_pair_to_files,
)
from member2_security.key_management.registry import (
    KeyLifecycleStatus,
    KeyRegistry,
    KeyTrustStatus,
)


class TestKeyGenerationAndSerialization:
    """Tests for cryptographic key generation and PEM serialization."""

    def test_generate_and_load_unencrypted_ecdsa_key_pair(self):
        priv_pem, pub_pem = generate_ecdsa_key_pair(password=None)

        assert b"BEGIN PRIVATE KEY" in priv_pem
        assert b"BEGIN PUBLIC KEY" in pub_pem

        priv_key = load_private_key_pem(priv_pem)
        pub_key = load_public_key_pem(pub_pem)

        assert isinstance(priv_key, ec.EllipticCurvePrivateKey)
        assert isinstance(pub_key, ec.EllipticCurvePublicKey)
        assert isinstance(priv_key.curve, ec.SECP256R1)
        assert isinstance(pub_key.curve, ec.SECP256R1)

    def test_generate_and_load_password_encrypted_ecdsa_key_pair(self):
        """Private key encrypted with passphrase must require that exact passphrase to load."""
        password = "StrictlySecretPassphrase2026!"
        priv_pem, pub_pem = generate_ecdsa_key_pair(password=password)

        assert b"ENCRYPTED" in priv_pem

        # Loading with correct password succeeds
        loaded_priv = load_private_key_pem(priv_pem, password=password)
        assert isinstance(loaded_priv, ec.EllipticCurvePrivateKey)

        # Loading with wrong password fails safely
        with pytest.raises(KeyManagementError):
            load_private_key_pem(priv_pem, password="WrongPassword123")

        # Loading without password fails safely
        with pytest.raises(KeyManagementError):
            load_private_key_pem(priv_pem, password=None)

    def test_reject_unsupported_elliptic_curve(self):
        """Loading a key on a curve other than NIST P-256 (e.g. SECP384R1) must be rejected."""
        wrong_curve_key = ec.generate_private_key(ec.SECP384R1())
        pub_pem = export_public_key_pem(wrong_curve_key.public_key())

        with pytest.raises(KeyManagementError, match="Expected SECP256R1"):
            load_public_key_pem(pub_pem)

    def test_generate_aes_key(self):
        key = generate_aes_key(32)
        assert isinstance(key, bytes)
        assert len(key) == 32

        # Insecure or invalid lengths rejected
        with pytest.raises(ValueError):
            generate_aes_key(16)

    def test_save_and_load_key_files(self, tmp_path):
        priv_pem, pub_pem = generate_ecdsa_key_pair()
        priv_path = tmp_path / "keys" / "private.pem"
        pub_path = tmp_path / "keys" / "public.pem"

        save_key_pair_to_files(priv_pem, pub_pem, priv_path, pub_path)

        assert priv_path.exists()
        assert pub_path.exists()

        loaded_priv = load_private_key_pem(priv_path.read_bytes())
        loaded_pub = load_public_key_pem(pub_path.read_bytes())

        assert isinstance(loaded_priv, ec.EllipticCurvePrivateKey)
        assert isinstance(loaded_pub, ec.EllipticCurvePublicKey)


class TestKeyRegistryAndRotation:
    """Tests for KeyRegistry, rotation lifecycles, and backwards verification compatibility."""

    def test_key_rotation_and_historic_verification(self):
        """
        Rotating a key:
        - Old key becomes RETIRED.
        - New key becomes ACTIVE.
        - Historical records signed with the retired key still verify as TRUSTED.
        """
        registry = KeyRegistry()

        # Phase 1: Key V1 is active
        priv1_pem, pub1_pem = generate_ecdsa_key_pair()
        priv1 = load_private_key_pem(priv1_pem)
        registry.register_key("tl-key-v1", pub1_pem, status=KeyLifecycleStatus.ACTIVE)

        # Create historical record signed with V1
        historic_record = {
            "schema_version": "1.0",
            "asset_id": "historical-media-001",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "registered_at": "2026-01-01T00:00:00Z",
            "signing_key_id": "tl-key-v1",
            "content_type": "image/jpeg",
        }
        historic_sig = sign_record(historic_record, priv1)

        # Phase 2: Rotate to Key V2
        priv2_pem, pub2_pem = generate_ecdsa_key_pair()
        registry.rotate_key(new_key_id="tl-key-v2", new_public_key_pem=pub2_pem)

        # Verify statuses
        rec1 = registry.get_key_record("tl-key-v1")
        rec2 = registry.get_key_record("tl-key-v2")
        assert rec1.status == KeyLifecycleStatus.RETIRED
        assert rec2.status == KeyLifecycleStatus.ACTIVE

        # Historic record MUST STILL VERIFY as VALID and TRUSTED under the retired key!
        res_historic = verify_record_signature(
            record=historic_record,
            signature_b64=historic_sig,
            key_registry=registry,
        )
        assert res_historic.status == SignatureStatus.VALID
        assert res_historic.key_trust_status == KeyTrustStatus.TRUSTED

    def test_revoked_key_untrusted(self):
        registry = KeyRegistry()
        priv_pem, pub_pem = generate_ecdsa_key_pair()
        registry.register_key("compromised-key", pub_pem, status=KeyLifecycleStatus.ACTIVE)

        # Revoke
        registry.revoke_key("compromised-key", reason="Private key leaked in incident #42")
        trust_status, key_rec = registry.evaluate_key_trust("compromised-key")

        assert trust_status == KeyTrustStatus.REVOKED
        assert key_rec.status == KeyLifecycleStatus.REVOKED

    def test_registry_file_persistence(self, tmp_path):
        registry = KeyRegistry()
        _, pub1 = generate_ecdsa_key_pair()
        _, pub2 = generate_ecdsa_key_pair()

        registry.register_key("k1", pub1, status=KeyLifecycleStatus.RETIRED)
        registry.register_key("k2", pub2, status=KeyLifecycleStatus.ACTIVE)

        reg_path = tmp_path / "trusted_registry.json"
        registry.save_to_file(reg_path)

        loaded = KeyRegistry.load_from_file(reg_path)
        assert loaded.get_key_record("k1").status == KeyLifecycleStatus.RETIRED
        assert loaded.get_key_record("k2").status == KeyLifecycleStatus.ACTIVE
