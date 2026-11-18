"""
tests/test_audit_e2e.py
=======================
Comprehensive End-to-End Audit & Verification Test Suite for TruthLens AI.
Covers:
- Task 1: AI Detection & Model Selection
- Task 2: Cryptographic Integrity & Authenticated Encryption
- Task 3: Backend Verification API & Trust Engine
- Task 4: Separation of Concerns & Independent Provenance
"""

import sys
import os
import io
import pytest
from pathlib import Path
from PIL import Image

# Ensure project root and submodules are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "truthlens-ai"))
sys.path.insert(0, str(PROJECT_ROOT / "member2_security"))

from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app, startup_event
from backend.app.services.trust_engine import TrustAssessmentEngine
from member2_security.crypto.hashing import sha256_bytes, is_valid_sha256_hex
from member2_security.crypto.signatures import sign_canonical_bytes, verify_canonical_bytes_signature
from member2_security.crypto.encryption import encrypt_bytes, decrypt_bytes, DecryptionAuthenticationError
from cryptography.hazmat.primitives.asymmetric import ec
from src.detector import resolve_model_info, TruthLensDetector, ModelNotAvailableError
from src.preprocessing import load_image, check_document_characteristics
from src.inference import run_inference


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_app():
    startup_event()


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: AI Detection & Model Selection
# ─────────────────────────────────────────────────────────────────────────────

class TestTask1AIDetection:

    def test_model_registry_resolution(self):
        """Current and Smaug must resolve to distinct, strictly correct model IDs."""
        cur = resolve_model_info("current")
        assert cur["model_id"] == "dima806/ai_vs_real_image_detection"
        assert cur["architecture"] == "vit"

        smaug = resolve_model_info("smaug")
        assert smaug["model_id"] == "abacusai/Smaug-AI-Image-Detector"
        assert smaug["architecture"] == "smaug"

    def test_invalid_model_fails_explicitly(self):
        """Requesting an unknown model must raise ValueError and not fall back."""
        with pytest.raises(ValueError, match="Unknown model identifier"):
            resolve_model_info("nonexistent_model_v9")

    def test_natural_aspect_ratios_do_not_trigger_document_warning(self):
        """Standard camera photos (4:3, 16:9) must not be falsely flagged as documents."""
        # 16:9 aspect ratio photo
        img_16_9 = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
        meta_16_9 = check_document_characteristics(img_16_9)
        assert meta_16_9["is_likely_document"] is False

        # 4:3 aspect ratio photo
        img_4_3 = Image.new("RGB", (1600, 1200), color=(120, 140, 160))
        meta_4_3 = check_document_characteristics(img_4_3)
        assert meta_4_3["is_likely_document"] is False

    def test_actual_document_triggers_domain_warning(self):
        """Document images with document geometry & high paper-white ratio trigger warning."""
        # A4 document with high paper-white ratio
        img_doc = Image.new("RGB", (1240, 1754), color=(252, 252, 252))
        meta_doc = check_document_characteristics(img_doc)
        assert meta_doc["is_likely_document"] is True
        assert meta_doc["document_hint"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Cryptographic Integrity & Security
# ─────────────────────────────────────────────────────────────────────────────

class TestTask2Cryptography:

    def test_sha256_hash_and_tamper_detection(self):
        """SHA-256 calculation matches original and detects single-byte tampering."""
        data = b"Authentic Camera Sensor Bytes"
        h = sha256_bytes(data)
        assert is_valid_sha256_hex(h) is True
        assert sha256_bytes(data) == h

        tampered_data = b"Authentic Camera Sensor Bytes!"
        assert sha256_bytes(tampered_data) != h

    def test_ecdsa_signature_verification_and_tampering(self):
        """ECDSA-P256 signature generation and verification rejects forged data."""
        priv_key = ec.generate_private_key(ec.SECP256R1())
        pub_key = priv_key.public_key()
        payload = b"Camera Forensic Evidence Payload"
        sig_b64 = sign_canonical_bytes(payload, priv_key)

        # Authentic verification
        assert verify_canonical_bytes_signature(payload, sig_b64, pub_key) is True

        # Tampered payload fails
        tampered_payload = b"Forged Forensic Evidence Payload"
        assert verify_canonical_bytes_signature(tampered_payload, sig_b64, pub_key) is False

        # Corrupted signature fails
        corrupted_sig = "A" * len(sig_b64)
        assert verify_canonical_bytes_signature(payload, corrupted_sig, pub_key) is False

    def test_aes_256_gcm_authenticated_encryption(self):
        """AES-256-GCM encrypts, decrypts, and rejects ciphertext tampering."""
        key = os.urandom(32)
        plaintext = b"Sensitive forensic metadata: Lat=28.6139, Lon=77.2090"
        aad = b"header-audit-context"

        envelope = encrypt_bytes(plaintext, key, key_id="key-001", aad=aad)
        decrypted = decrypt_bytes(envelope, key, aad=aad)
        assert decrypted == plaintext

        # Tampering with ciphertext fails authenticated decryption
        import base64
        raw_ct = bytearray(base64.b64decode(envelope.ciphertext_and_tag))
        raw_ct[0] ^= 0xFF
        tampered_env = {
            "version": envelope.version,
            "algorithm": envelope.algorithm,
            "key_id": envelope.key_id,
            "nonce": envelope.nonce,
            "ciphertext_and_tag": base64.b64encode(raw_ct).decode("ascii"),
        }
        with pytest.raises(DecryptionAuthenticationError):
            decrypt_bytes(tampered_env, key, aad=aad)

    def test_cryptography_is_independent_of_ai(self):
        """Cryptographic integrity status must not be modified by AI classification."""
        # Simulated scenario: valid crypto signature + AI predicted FAKE
        verdict = TrustAssessmentEngine.evaluate(
            integrity={"status": "MATCH"},
            signature={"status": "VALID", "key_trust_status": "TRUSTED"},
            ai={"status": "SUCCESS", "label": "AI_GENERATED", "ai_likelihood": "high", "confidence": 0.98},
        )
        # Provenance is intact, but AI conflict is flagged without branding file as tampered
        assert verdict["status"] == "VERIFIED_TRUSTED_WITH_AI_CONFLICT"
        assert verdict["score"] >= 80


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: Backend APIs & Trust Engine
# ─────────────────────────────────────────────────────────────────────────────

class TestTask3BackendAndTrustEngine:

    def test_missing_provenance_is_inconclusive_not_tampered(self):
        """Unregistered images must evaluate to INCONCLUSIVE, not tampered."""
        verdict = TrustAssessmentEngine.evaluate(
            integrity={"status": "NO_REFERENCE"},
            signature={"status": "MISSING", "key_trust_status": "UNKNOWN"},
            ai={"status": "SUCCESS", "label": "REAL", "confidence": 0.90, "ai_likelihood": "low"},
        )
        assert verdict["status"] == "INCONCLUSIVE"
        assert "provenance" in verdict["explanation"].lower()

    def test_api_verify_with_model_selection(self):
        """The /api/media/verify endpoint accepts model='current' and model='smaug'."""
        img = Image.new("RGB", (64, 64), color=(200, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        with patch("src.inference.run_inference") as mock_inf:
            mock_inf.side_effect = lambda path, model="current": {
                "status": "success",
                "label": "REAL",
                "confidence": 0.95,
                "model_id": "dima806/ai_vs_real_image_detection" if model == "current" else "abacusai/Smaug-AI-Image-Detector",
                "inference_ms": 12.0,
                "ai_likelihood": "low",
                "raw_scores": [{"label": "REAL", "score": 0.95}],
            }
            # 1. Verify with current model
            resp_cur = client.post(
                "/api/media/verify",
                files={"file": ("test.jpg", buf.getvalue(), "image/jpeg")},
                data={"model": "current"},
            )
            assert resp_cur.status_code == 200
            cur_json = resp_cur.json()
            assert cur_json["ai"]["model_id"] == "dima806/ai_vs_real_image_detection"

            # 2. Verify with smaug model
            resp_smaug = client.post(
                "/api/media/verify",
                files={"file": ("test.jpg", buf.getvalue(), "image/jpeg")},
                data={"model": "smaug"},
            )
            assert resp_smaug.status_code == 200
            smaug_json = resp_smaug.json()
            assert smaug_json["ai"]["model_id"] == "abacusai/Smaug-AI-Image-Detector"


# ─────────────────────────────────────────────────────────────────────────────
# Task 4: Separation of Concerns
# ─────────────────────────────────────────────────────────────────────────────

class TestTask4SeparationOfConcerns:

    def test_response_contract_separates_signals(self):
        """Verification response separates AI, integrity, signature, and trust assessment."""
        img = Image.new("RGB", (64, 64), color=(50, 100, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        with patch("src.inference.run_inference") as mock_inf:
            mock_inf.return_value = {
                "status": "success",
                "label": "REAL",
                "confidence": 0.91,
                "model_id": "dima806/ai_vs_real_image_detection",
                "inference_ms": 15.0,
                "ai_likelihood": "low",
                "warning": "Experimental AI detection; not proof of authenticity.",
                "raw_scores": [{"label": "REAL", "score": 0.91}],
            }
            resp = client.post(
                "/api/media/verify",
                files={"file": ("signals_test.jpg", buf.getvalue(), "image/jpeg")},
                data={"model": "current"},
            )
            assert resp.status_code == 200
            data = resp.json()

            # Check required architectural separation
            assert "ai" in data
            assert "integrity" in data
            assert "signature" in data
            assert "trust_assessment" in data
            assert "sha256" in data

            # AI warning states it is not proof of authenticity
            assert "warning" in data["ai"]
            assert "authenticity" in data["ai"]["warning"].lower()
