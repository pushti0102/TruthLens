"""
Unit and Security Tests for ECDSA Digital Signatures & Provenance Canonicalization
Member 2: Cryptography & Information Security
"""

import copy

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from member2_security.crypto.canonicalization import (
    CanonicalizationError,
    canonicalize_record,
    validate_provenance_record_schema,
)
from member2_security.crypto.signatures import (
    SignatureStatus,
    SignatureVerificationResult,
    sign_record,
    verify_record_signature,
)
from member2_security.key_management.key_utils import (
    generate_ecdsa_key_pair,
    load_private_key_pem,
    load_public_key_pem,
)
from member2_security.key_management.registry import (
    KeyLifecycleStatus,
    KeyRegistry,
    KeyTrustStatus,
)


@pytest.fixture
def test_keys():
    """Generate a fresh test ECDSA key pair."""
    priv_pem, pub_pem = generate_ecdsa_key_pair()
    priv_key = load_private_key_pem(priv_pem)
    pub_key = load_public_key_pem(pub_pem)
    return {
        "priv_pem": priv_pem,
        "pub_pem": pub_pem,
        "priv_key": priv_key,
        "pub_key": pub_key,
    }


@pytest.fixture
def alternate_keys():
    """Generate a second distinct ECDSA key pair."""
    priv_pem, pub_pem = generate_ecdsa_key_pair()
    return {
        "priv_key": load_private_key_pem(priv_pem),
        "pub_key": load_public_key_pem(pub_pem),
    }


@pytest.fixture
def valid_record():
    """A valid, schema-compliant TruthLens provenance record."""
    return {
        "schema_version": "1.0",
        "asset_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "registered_at": "2026-10-26T10:30:00Z",
        "signing_key_id": "tl-key-test-01",
        "content_type": "image/jpeg",
        "issuer_id": "org_truthlens_unit_tests",
    }


class TestCanonicalization:
    """Tests for deterministic JSON canonicalization and schema validation."""

    def test_canonicalization_field_order_invariant(self, valid_record):
        """Dict key ordering in memory must NOT alter the canonical byte sequence."""
        rec1 = dict(valid_record)
        # Reverse key insertion order
        rec2 = {k: rec1[k] for k in reversed(list(rec1.keys()))}

        bytes1 = canonicalize_record(rec1)
        bytes2 = canonicalize_record(rec2)

        assert bytes1 == bytes2
        assert isinstance(bytes1, bytes)

    def test_canonicalization_excludes_signature_field(self, valid_record):
        """If a record includes a 'signature' key, it must be excluded from canonical bytes."""
        rec_without = copy.deepcopy(valid_record)
        rec_with = copy.deepcopy(valid_record)
        rec_with["signature"] = "arbitrary_signature_string"

        assert canonicalize_record(rec_without) == canonicalize_record(rec_with)

    def test_canonicalization_rejects_sensitive_keys(self, valid_record):
        """Records containing private keys, passwords, or tokens must be rejected."""
        bad_rec = copy.deepcopy(valid_record)
        bad_rec["private_key"] = "leak_attempt"
        with pytest.raises(CanonicalizationError, match="Security violation"):
            canonicalize_record(bad_rec)

    def test_canonicalization_rejects_unsupported_version(self, valid_record):
        bad_rec = copy.deepcopy(valid_record)
        bad_rec["schema_version"] = "99.0"
        with pytest.raises(CanonicalizationError, match="Unsupported or missing 'schema_version'"):
            canonicalize_record(bad_rec)

    def test_canonicalization_rejects_malformed_timestamp(self, valid_record):
        bad_rec = copy.deepcopy(valid_record)
        bad_rec["registered_at"] = "not_a_valid_timestamp"
        with pytest.raises(CanonicalizationError, match="registered_at"):
            canonicalize_record(bad_rec)


class TestECDSASignatures:
    """Tests for ECDSA P-256 signing, verification, and tampering detection."""

    def test_sign_and_verify_valid(self, test_keys, valid_record):
        """A valid signature must mathematically verify."""
        signature = sign_record(valid_record, test_keys["priv_key"])
        assert isinstance(signature, str)
        assert len(signature) > 60

        result = verify_record_signature(
            record=valid_record,
            signature_b64=signature,
            public_key=test_keys["pub_key"],
        )
        assert result.status == SignatureStatus.VALID
        assert result.key_id == "tl-key-test-01"
        assert result.algorithm == "ECDSA-P256-SHA256"

    def test_tamper_sha256_invalidates_signature(self, test_keys, valid_record):
        """Modifying the media SHA-256 hash must cause signature verification to fail."""
        sig = sign_record(valid_record, test_keys["priv_key"])

        tampered_record = copy.deepcopy(valid_record)
        tampered_record["sha256"] = "a" * 64

        result = verify_record_signature(
            record=tampered_record,
            signature_b64=sig,
            public_key=test_keys["pub_key"],
        )
        assert result.status == SignatureStatus.INVALID

    def test_tamper_asset_id_invalidates_signature(self, test_keys, valid_record):
        """Modifying the asset_id must cause verification to fail."""
        sig = sign_record(valid_record, test_keys["priv_key"])

        tampered = copy.deepcopy(valid_record)
        tampered["asset_id"] = "modified-asset-id-uuid"

        result = verify_record_signature(
            record=tampered,
            signature_b64=sig,
            public_key=test_keys["pub_key"],
        )
        assert result.status == SignatureStatus.INVALID

    def test_tamper_registered_at_invalidates_signature(self, test_keys, valid_record):
        """Modifying the registration timestamp must cause verification to fail."""
        sig = sign_record(valid_record, test_keys["priv_key"])

        tampered = copy.deepcopy(valid_record)
        tampered["registered_at"] = "2026-10-26T11:00:00Z"

        result = verify_record_signature(
            record=tampered,
            signature_b64=sig,
            public_key=test_keys["pub_key"],
        )
        assert result.status == SignatureStatus.INVALID

    def test_verify_wrong_public_key_fails(self, test_keys, alternate_keys, valid_record):
        """Signature checked against a different public key must fail."""
        sig = sign_record(valid_record, test_keys["priv_key"])

        result = verify_record_signature(
            record=valid_record,
            signature_b64=sig,
            public_key=alternate_keys["pub_key"],
        )
        assert result.status == SignatureStatus.INVALID

    def test_verify_missing_signature(self, test_keys, valid_record):
        """Missing or empty signature must return MISSING without error."""
        res_none = verify_record_signature(
            record=valid_record,
            signature_b64=None,
            public_key=test_keys["pub_key"],
        )
        assert res_none.status == SignatureStatus.MISSING

        res_empty = verify_record_signature(
            record=valid_record,
            signature_b64="   ",
            public_key=test_keys["pub_key"],
        )
        assert res_empty.status == SignatureStatus.MISSING

    def test_verify_malformed_signature_string(self, test_keys, valid_record):
        """Garbage or malformed base64 must return MALFORMED safely."""
        res1 = verify_record_signature(
            record=valid_record,
            signature_b64="NotBase64!@#$%",
            public_key=test_keys["pub_key"],
        )
        assert res1.status == SignatureStatus.MALFORMED

        # Valid base64, but not valid ASN.1 DER ECDSA signature
        res2 = verify_record_signature(
            record=valid_record,
            signature_b64="AAAA",
            public_key=test_keys["pub_key"],
        )
        assert res2.status == SignatureStatus.MALFORMED

    def test_verify_malformed_record_returns_malformed(self, test_keys):
        """Malformed record data must return MALFORMED safely without crashing."""
        malformed_rec = {"corrupt": "data"}
        res = verify_record_signature(
            record=malformed_rec,
            signature_b64="dGVzdA==",
            public_key=test_keys["pub_key"],
        )
        assert res.status == SignatureStatus.MALFORMED


class TestSignatureKeyRegistryTrust:
    """Tests evaluating signature verification combined with KeyRegistry trust status."""

    def test_verify_with_trusted_key_registry(self, test_keys, valid_record):
        """Active key in registry must report key_trust_status as TRUSTED."""
        registry = KeyRegistry()
        registry.register_key(
            key_id="tl-key-test-01",
            public_key_pem=test_keys["pub_pem"],
            status=KeyLifecycleStatus.ACTIVE,
        )

        sig = sign_record(valid_record, test_keys["priv_key"])

        res = verify_record_signature(
            record=valid_record,
            signature_b64=sig,
            key_registry=registry,  # Resolved automatically via key_id
        )
        assert res.status == SignatureStatus.VALID
        assert res.key_trust_status == KeyTrustStatus.TRUSTED

    def test_verify_with_revoked_key(self, test_keys, valid_record):
        """Revoked key must report REVOKED trust status even if signature is valid."""
        registry = KeyRegistry()
        registry.register_key(
            key_id="tl-key-test-01",
            public_key_pem=test_keys["pub_pem"],
            status=KeyLifecycleStatus.ACTIVE,
        )
        # Revoke the key
        registry.revoke_key("tl-key-test-01", reason="Compromise investigation")

        sig = sign_record(valid_record, test_keys["priv_key"])

        res = verify_record_signature(
            record=valid_record,
            signature_b64=sig,
            key_registry=registry,
        )
        # Mathematical validity succeeds, but key is REVOKED
        assert res.status == SignatureStatus.VALID
        assert res.key_trust_status == KeyTrustStatus.REVOKED
        assert "REVOKED" in res.message

    def test_verify_with_unknown_key(self, test_keys, valid_record):
        """Key not in registry must report UNKNOWN trust status."""
        registry = KeyRegistry()  # Empty registry

        sig = sign_record(valid_record, test_keys["priv_key"])

        res = verify_record_signature(
            record=valid_record,
            signature_b64=sig,
            public_key=test_keys["pub_key"],
            key_registry=registry,
        )
        assert res.status == SignatureStatus.VALID
        assert res.key_trust_status == KeyTrustStatus.UNKNOWN
