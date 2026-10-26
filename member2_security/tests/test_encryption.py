"""
Unit and Security Tests for AES-256-GCM Authenticated Encryption
Member 2: Cryptography & Information Security
"""

import base64
import copy

import pytest

from member2_security.crypto.encryption import (
    DecryptionAuthenticationError,
    EncryptedEnvelope,
    EncryptionError,
    InvalidEnvelopeError,
    decrypt_bytes,
    encrypt_bytes,
)
from member2_security.key_management.key_utils import generate_aes_key


@pytest.fixture
def aes_key():
    """Generate a fresh 32-byte (256-bit) AES key."""
    return generate_aes_key()


@pytest.fixture
def alternate_aes_key():
    """Generate a second distinct 32-byte AES key."""
    return generate_aes_key()


class TestAES256GCMEncryption:
    """Tests covering authenticated symmetric encryption, decryption, and tampering detection."""

    def test_encrypt_decrypt_roundtrip(self, aes_key):
        """Plaintext encrypted and decrypted with the same key must match original bytes."""
        plaintext = b"Sensitive forensic analysis report and deepfake detection score"
        key_id = "tl-aes-test-01"

        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id=key_id)

        assert isinstance(envelope, EncryptedEnvelope)
        assert envelope.algorithm == "AES-256-GCM"
        assert envelope.key_id == key_id
        assert envelope.version == "1.0"

        decrypted = decrypt_bytes(envelope=envelope, key=aes_key)
        assert decrypted == plaintext

    def test_encrypt_decrypt_with_associated_authenticated_data(self, aes_key):
        """Encryption with AAD must succeed when matching AAD is provided at decryption."""
        plaintext = b"Proprietary evidence data payload"
        aad = b"asset_id:9b1deb4d|timestamp:2026-10-26T10:30:00Z"

        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id="key-01", aad=aad)
        decrypted = decrypt_bytes(envelope=envelope, key=aes_key, aad=aad)

        assert decrypted == plaintext

    def test_tamper_aad_fails_authentication(self, aes_key):
        """Mismatched or altered AAD must cause decryption authentication to fail."""
        plaintext = b"Bound contextual payload"
        aad_correct = b"tenant:org_alpha"
        aad_tampered = b"tenant:org_beta"

        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id="key-01", aad=aad_correct)

        with pytest.raises(DecryptionAuthenticationError):
            decrypt_bytes(envelope=envelope, key=aes_key, aad=aad_tampered)

    def test_wrong_key_fails_authentication(self, aes_key, alternate_aes_key):
        """Attempting decryption with the wrong key must fail authentication."""
        plaintext = b"Confidential watermark verification vector"
        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id="key-01")

        with pytest.raises(DecryptionAuthenticationError):
            decrypt_bytes(envelope=envelope, key=alternate_aes_key)

    def test_tamper_ciphertext_fails_authentication(self, aes_key):
        """Flipping even a single bit in the ciphertext must cause authentication failure."""
        plaintext = b"Original uncorrupted data payload"
        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id="key-01")

        # Decode ciphertext, flip one byte, and re-encode
        raw_ct = bytearray(base64.b64decode(envelope.ciphertext_and_tag))
        raw_ct[0] ^= 0x01  # Flip 1 bit in ciphertext
        tampered_b64 = base64.b64encode(raw_ct).decode("ascii")

        tampered_envelope = EncryptedEnvelope(
            version=envelope.version,
            algorithm=envelope.algorithm,
            key_id=envelope.key_id,
            nonce=envelope.nonce,
            ciphertext_and_tag=tampered_b64,
        )

        with pytest.raises(DecryptionAuthenticationError):
            decrypt_bytes(envelope=tampered_envelope, key=aes_key)

    def test_tamper_tag_fails_authentication(self, aes_key):
        """Flipping a bit in the appended 16-byte authentication tag must cause authentication failure."""
        plaintext = b"Integrity protected payload"
        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id="key-01")

        raw_ct = bytearray(base64.b64decode(envelope.ciphertext_and_tag))
        # The authentication tag is the last 16 bytes of ciphertext_and_tag
        raw_ct[-1] ^= 0xFF  # Corrupt last byte of tag
        tampered_b64 = base64.b64encode(raw_ct).decode("ascii")

        tampered_envelope = EncryptedEnvelope(
            version=envelope.version,
            algorithm=envelope.algorithm,
            key_id=envelope.key_id,
            nonce=envelope.nonce,
            ciphertext_and_tag=tampered_b64,
        )

        with pytest.raises(DecryptionAuthenticationError):
            decrypt_bytes(envelope=tampered_envelope, key=aes_key)

    def test_tamper_nonce_fails_authentication(self, aes_key):
        """Modifying the nonce must fail authentication tag check."""
        plaintext = b"Data with altered nonce"
        envelope = encrypt_bytes(plaintext=plaintext, key=aes_key, key_id="key-01")

        raw_nonce = bytearray(base64.b64decode(envelope.nonce))
        raw_nonce[0] ^= 0x01
        tampered_nonce_b64 = base64.b64encode(raw_nonce).decode("ascii")

        tampered_envelope = EncryptedEnvelope(
            version=envelope.version,
            algorithm=envelope.algorithm,
            key_id=envelope.key_id,
            nonce=tampered_nonce_b64,
            ciphertext_and_tag=envelope.ciphertext_and_tag,
        )

        with pytest.raises(DecryptionAuthenticationError):
            decrypt_bytes(envelope=tampered_envelope, key=aes_key)

    def test_nonce_uniqueness_across_encryptions(self, aes_key):
        """Every call to encrypt_bytes must produce a fresh, unique nonce."""
        nonces = set()
        for _ in range(500):
            env = encrypt_bytes(plaintext=b"constant payload", key=aes_key, key_id="key-01")
            assert env.nonce not in nonces
            nonces.add(env.nonce)

    @pytest.mark.parametrize("invalid_key_length", [0, 16, 24, 31, 33, 64])
    def test_invalid_key_length_rejected(self, invalid_key_length):
        """Keys that are not exactly 32 bytes (256 bits) must be rejected."""
        bad_key = b"A" * invalid_key_length
        with pytest.raises(EncryptionError, match="AES-256 requires exactly 32 bytes"):
            encrypt_bytes(plaintext=b"data", key=bad_key, key_id="key-01")

        with pytest.raises(EncryptionError, match="AES-256 requires exactly 32 bytes"):
            decrypt_bytes(
                envelope={"version": "1.0", "algorithm": "AES-256-GCM", "key_id": "k", "nonce": "n", "ciphertext_and_tag": "c"},
                key=bad_key,
            )

    def test_malformed_envelope_dict_rejected(self, aes_key):
        """Envelopes missing required keys or specifying unsupported algorithms must be rejected."""
        with pytest.raises(InvalidEnvelopeError):
            decrypt_bytes(envelope={"incomplete": "envelope"}, key=aes_key)

        with pytest.raises(InvalidEnvelopeError, match="Unsupported algorithm"):
            decrypt_bytes(
                envelope={
                    "version": "1.0",
                    "algorithm": "DES-CBC-INSECURE",
                    "key_id": "k1",
                    "nonce": "n1",
                    "ciphertext_and_tag": "c1",
                },
                key=aes_key,
            )
