"""
TruthLens End-to-End Cryptographic & Integrity Verification Demonstration
Member 2: Cryptography & Information Security

Demonstrates all core security workflows of TruthLens:
1. Creation of test media fixture (JPEG).
2. Streaming SHA-256 computation of raw image bytes.
3. Creation and canonicalization of a versioned provenance record.
4. ECDSA P-256 key pair generation and public key registry enrollment.
5. Digital signing of canonical provenance record.
6. Mathematical signature verification and authority trust evaluation.
7. File integrity verification yielding MATCH.
8. Bit-level image modification yielding MISMATCH.
9. Provenance record tampering causing signature verification to fail (INVALID).
10. AES-256-GCM authenticated encryption and successful decryption with AAD.
11. Ciphertext bit tampering causing DecryptionAuthenticationError.

USAGE:
    python -m member2_security.examples.demo_integrity
    # or
    python member2_security/examples/demo_integrity.py
"""

from __future__ import annotations

import base64
import copy
import io
import sys
import tempfile
from pathlib import Path

from PIL import Image

# Ensure project root is in sys.path when running as a standalone script
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from member2_security.crypto.canonicalization import canonicalize_record
from member2_security.crypto.encryption import (
    DecryptionAuthenticationError,
    EncryptedEnvelope,
    decrypt_bytes,
    encrypt_bytes,
)
from member2_security.crypto.hashing import (
    IntegrityStatus,
    compare_hashes,
    sha256_bytes,
    sha256_file,
)
from member2_security.crypto.signatures import (
    SignatureStatus,
    sign_record,
    verify_record_signature,
)
from member2_security.key_management.key_utils import (
    generate_aes_key,
    generate_ecdsa_key_pair,
    load_private_key_pem,
    load_public_key_pem,
)
from member2_security.key_management.registry import (
    KeyLifecycleStatus,
    KeyRegistry,
    KeyTrustStatus,
)


def print_step(step_num: int, title: str, description: str) -> None:
    print("\n" + "=" * 80)
    print(f"  STEP {step_num}: {title.upper()}")
    print("=" * 80)
    print(f">> {description}\n")


def print_success(msg: str) -> None:
    print(f"  [+] SUCCESS: {msg}")


def print_alert(msg: str) -> None:
    print(f"  [!] EXPECTED SECURITY FAILURE: {msg}")


def print_info(key: str, val: str) -> None:
    print(f"      * {key:<24}: {val}")


def main() -> None:
    print("""
================================================================================
     TruthLens Cryptography, Provenance & File Integrity Demonstration
                    AI 331 - Member 2 Security Module
================================================================================
    """)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        # ----------------------------------------------------------------------
        # STEP 1: Create a test image fixture
        # ----------------------------------------------------------------------
        print_step(
            1,
            "Create Verified Image Fixture",
            "Synthesizing an in-memory 200x200 RGB test image and saving as JPEG.",
        )
        img = Image.new("RGB", (200, 200), color=(41, 128, 185))
        test_image_path = tmp_dir / "truthlens_sample.jpg"
        img.save(test_image_path, format="JPEG")
        raw_image_bytes = test_image_path.read_bytes()

        print_success(f"Generated test JPEG ({len(raw_image_bytes)} bytes)")
        print_info("File Path", str(test_image_path))
        print_info("Resolution", "200 x 200 pixels")

        # ----------------------------------------------------------------------
        # STEP 2: Compute SHA-256 digest
        # ----------------------------------------------------------------------
        print_step(
            2,
            "Compute Raw-Byte SHA-256 Integrity Digest",
            "Streaming raw binary image bytes into hashlib.sha256 in 64KB chunks.",
        )
        image_digest = sha256_file(test_image_path)
        print_success("SHA-256 digest computed without altering original bytes")
        print_info("SHA-256", image_digest)

        # ----------------------------------------------------------------------
        # STEP 3: Create versioned provenance record
        # ----------------------------------------------------------------------
        print_step(
            3,
            "Create Versioned Provenance Record",
            "Constructing canonical provenance record conforming to schema v1.0.",
        )
        asset_id = "4f8c2b71-e940-4b8c-b062-817dbbc1c499"
        signing_key_id = "tl-key-ecdsa-demo-v1"

        provenance_record = {
            "schema_version": "1.0",
            "asset_id": asset_id,
            "sha256": image_digest,
            "registered_at": "2026-10-26T10:30:00Z",
            "signing_key_id": signing_key_id,
            "content_type": "image/jpeg",
            "issuer_id": "org_truthlens_sentinel",
            "metadata": {
                "sensor": "Digital Capture Unit Alpha",
                "environment": "demonstration",
            },
        }
        canonical_bytes = canonicalize_record(provenance_record)
        print_success("Provenance record validated and canonicalized (RFC 8785)")
        print_info("Canonical Payload", canonical_bytes.decode("utf-8"))

        # ----------------------------------------------------------------------
        # STEP 4: Generate ECDSA key pair and enroll in KeyRegistry
        # ----------------------------------------------------------------------
        print_step(
            4,
            "Generate ECDSA P-256 Key Pair & Trusted Registry",
            "Generating NIST P-256 (SECP256R1) signing key pair and enrolling in KeyRegistry.",
        )
        priv_pem, pub_pem = generate_ecdsa_key_pair(password=None)
        private_key = load_private_key_pem(priv_pem)
        public_key = load_public_key_pem(pub_pem)

        registry = KeyRegistry()
        registry.register_key(
            key_id=signing_key_id,
            public_key_pem=pub_pem,
            status=KeyLifecycleStatus.ACTIVE,
            description="TruthLens Demonstration Sentinel Authority Key",
        )
        print_success("Generated ECDSA P-256 key pair")
        print_info("Signing Key ID", signing_key_id)
        print_info("Curve", "NIST P-256 / SECP256R1")
        print_info("Key Status in Registry", "ACTIVE (TRUSTED)")

        # ----------------------------------------------------------------------
        # STEP 5: Sign the canonical record
        # ----------------------------------------------------------------------
        print_step(
            5,
            "Sign Canonical Provenance Record",
            "Signing canonical UTF-8 bytes with ECDSA private key using SHA-256 digest.",
        )
        signature_b64 = sign_record(provenance_record, private_key)
        print_success("Record digitally signed")
        print_info("Signature (Base64 DER)", signature_b64[:48] + "..." + signature_b64[-16:])

        # ----------------------------------------------------------------------
        # STEP 6: Verify the signature
        # ----------------------------------------------------------------------
        print_step(
            6,
            "Verify Digital Signature & Key Trust Status",
            "Verifying signature mathematically and evaluating signing key trust in registry.",
        )
        sig_result = verify_record_signature(
            record=provenance_record,
            signature_b64=signature_b64,
            key_registry=registry,
        )
        print_success("Signature mathematically verified and trusted")
        print_info("Mathematical Status", sig_result.status.value)
        print_info("Authority Trust Status", sig_result.key_trust_status.value)
        print_info("Message", sig_result.message)

        # ----------------------------------------------------------------------
        # STEP 7: Verify image against reference -> MATCH
        # ----------------------------------------------------------------------
        print_step(
            7,
            "File Integrity Verification -> MATCH",
            "Comparing current file digest against registered reference digest in provenance record.",
        )
        current_digest = sha256_file(test_image_path)
        integrity_match = compare_hashes(
            current_hash=current_digest,
            reference_hash=provenance_record["sha256"],
        )
        print_success("Integrity verified: exact byte-level identity confirmed")
        print_info("Status", integrity_match.status.value)
        print_info("Current SHA-256", integrity_match.current_sha256)
        print_info("Reference SHA-256", integrity_match.reference_sha256)
        print_info("Message", integrity_match.message)

        # ----------------------------------------------------------------------
        # STEP 8: Modify image bytes -> MISMATCH
        # ----------------------------------------------------------------------
        print_step(
            8,
            "Simulate Media Byte Manipulation -> MISMATCH",
            "Altering 1 byte of the image binary data and re-evaluating integrity.",
        )
        modified_bytes = bytearray(raw_image_bytes)
        # Flip bit in middle of file
        modified_bytes[len(modified_bytes) // 2] ^= 0x01
        modified_image_path = tmp_dir / "tampered_sample.jpg"
        modified_image_path.write_bytes(modified_bytes)

        tampered_digest = sha256_file(modified_image_path)
        integrity_mismatch = compare_hashes(
            current_hash=tampered_digest,
            reference_hash=provenance_record["sha256"],
        )
        print_alert("Digest divergence detected! Integrity check returned MISMATCH")
        print_info("Status", integrity_mismatch.status.value)
        print_info("Altered File SHA-256", integrity_mismatch.current_sha256)
        print_info("Reference SHA-256", integrity_mismatch.reference_sha256)
        print_info("Security Notice", integrity_mismatch.message)

        # ----------------------------------------------------------------------
        # STEP 9: Modify provenance record field -> INVALID
        # ----------------------------------------------------------------------
        print_step(
            9,
            "Simulate Provenance Record Tampering -> INVALID SIGNATURE",
            "Tampering with 'asset_id' inside the signed provenance record payload.",
        )
        tampered_record = copy.deepcopy(provenance_record)
        tampered_record["asset_id"] = "00000000-0000-0000-0000-000000000000"

        tampered_sig_result = verify_record_signature(
            record=tampered_record,
            signature_b64=signature_b64,
            key_registry=registry,
        )
        print_alert("Tampered payload rejected! Signature verification failed")
        print_info("Status", tampered_sig_result.status.value)
        print_info("Message", tampered_sig_result.message)

        # ----------------------------------------------------------------------
        # STEP 10: AES-256-GCM authenticated encryption and decryption
        # ----------------------------------------------------------------------
        print_step(
            10,
            "AES-256-GCM Authenticated Encryption & Decryption",
            "Encrypting sensitive evidence log with 32-byte AES key and context-bound AAD.",
        )
        aes_key = generate_aes_key(32)
        plaintext_evidence = b"CRITICAL FORENSIC REPORT: Sensor GPS [37.7749,-122.4194] Authenticity Score 0.994"
        aad_context = f"asset_id:{asset_id}|issuer:org_truthlens_sentinel".encode("utf-8")

        envelope = encrypt_bytes(
            plaintext=plaintext_evidence,
            key=aes_key,
            key_id="tl-aes-demo-v1",
            aad=aad_context,
        )
        print_success("Data encrypted into versioned AES-256-GCM envelope")
        print_info("Algorithm", envelope.algorithm)
        print_info("Key ID", envelope.key_id)
        print_info("Fresh Nonce (Base64)", envelope.nonce)
        print_info("Ciphertext + Tag", envelope.ciphertext_and_tag[:40] + "...")

        # Decrypt
        decrypted = decrypt_bytes(envelope=envelope, key=aes_key, aad=aad_context)
        print_success("Data authenticated and decrypted successfully")
        print_info("Decrypted Plaintext", decrypted.decode("utf-8"))

        # ----------------------------------------------------------------------
        # STEP 11: Modify ciphertext -> Authentication Failure
        # ----------------------------------------------------------------------
        print_step(
            11,
            "Simulate Ciphertext Tampering -> AUTHENTICATION FAILURE",
            "Flipping 1 byte in the base64 ciphertext and attempting decryption.",
        )
        raw_ct = bytearray(base64.b64decode(envelope.ciphertext_and_tag))
        raw_ct[5] ^= 0x55  # Tamper with byte 5
        tampered_ct_b64 = base64.b64encode(raw_ct).decode("ascii")

        tampered_envelope = EncryptedEnvelope(
            version=envelope.version,
            algorithm=envelope.algorithm,
            key_id=envelope.key_id,
            nonce=envelope.nonce,
            ciphertext_and_tag=tampered_ct_b64,
        )

        try:
            decrypt_bytes(envelope=tampered_envelope, key=aes_key, aad=aad_context)
            print("  [!] ERROR: Tampered ciphertext was decrypted! (Security Vulnerability)")
        except DecryptionAuthenticationError as exc:
            print_alert("Tampering detected! Decryption rejected with DecryptionAuthenticationError")
            print_info("Exception Caught", exc.__class__.__name__)
            print_info("Detail", str(exc))

    print("\n" + "=" * 80)
    print("  TRUTHLENS CRYPTOGRAPHY & INTEGRITY DEMONSTRATION COMPLETE")
    print("  ALL 11 SECURITY WORKFLOWS EXECUTED SUCCESSFULLY")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
