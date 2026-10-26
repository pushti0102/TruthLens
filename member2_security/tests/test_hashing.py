"""
Unit and Security Tests for SHA-256 File Integrity Module
Member 2: Cryptography & Information Security
"""

import hashlib
import tempfile
from pathlib import Path

import pytest

from member2_security.crypto.hashing import (
    IntegrityResult,
    IntegrityStatus,
    compare_hashes,
    is_valid_sha256_hex,
    normalize_sha256,
    sha256_bytes,
    sha256_file,
    sha256_stream,
    verify_file_integrity,
)


class TestSHA256Hashing:
    """Tests covering raw-byte SHA-256 calculation and format handling."""

    def test_sha256_bytes_deterministic(self):
        """Identical byte inputs must yield the exact same SHA-256 digest."""
        data = b"TruthLens authentic media sample 2026"
        digest1 = sha256_bytes(data)
        digest2 = sha256_bytes(data)
        expected = hashlib.sha256(data).hexdigest().lower()

        assert digest1 == digest2 == expected
        assert len(digest1) == 64
        assert digest1.islower()

    def test_sha256_bytes_different_inputs(self):
        """Distinct byte inputs must yield distinct SHA-256 digests."""
        data1 = b"Original unedited media frame"
        data2 = b"Manipulated media frame with 1 bit changed"
        assert sha256_bytes(data1) != sha256_bytes(data2)

    def test_sha256_bytes_empty(self):
        """Empty byte payload must match well-known SHA-256 of empty string."""
        empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert sha256_bytes(b"") == empty_hash

    def test_sha256_file_matches_bytes(self, tmp_path):
        """Chunked file hashing on disk must match in-memory byte hashing."""
        payload = b"Streaming file integrity verification test data." * 1000
        test_file = tmp_path / "sample_image.bin"
        test_file.write_bytes(payload)

        file_digest = sha256_file(test_file, chunk_size=256)
        byte_digest = sha256_bytes(payload)

        assert file_digest == byte_digest

    def test_sha256_file_nonexistent_raises(self, tmp_path):
        """Attempting to hash a missing file must raise FileNotFoundError."""
        nonexistent = tmp_path / "does_not_exist.jpg"
        with pytest.raises(FileNotFoundError):
            sha256_file(nonexistent)

    def test_sha256_file_directory_raises(self, tmp_path):
        """Attempting to hash a directory must raise IsADirectoryError."""
        with pytest.raises(IsADirectoryError):
            sha256_file(tmp_path)


class TestHashFormatValidation:
    """Tests for SHA-256 hex format validation and normalization."""

    def test_is_valid_sha256_hex_valid(self):
        valid_digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert is_valid_sha256_hex(valid_digest) is True
        # Uppercase should also be recognized as valid hex
        assert is_valid_sha256_hex(valid_digest.upper()) is True

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            "   ",
            None,
            12345,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85",  # 63 chars (too short)
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b8555",  # 65 chars (too long)
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b8zz",  # non-hex chars 'zz'
            "md5_is_not_allowed_12345678901234567890",
        ],
    )
    def test_is_valid_sha256_hex_invalid(self, invalid_input):
        assert is_valid_sha256_hex(invalid_input) is False

    def test_normalize_sha256(self):
        raw = "  E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855  "
        normalized = normalize_sha256(raw)
        assert normalized == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_normalize_sha256_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_sha256("invalid_hex")


class TestHashComparisonAndIntegrityResult:
    """Tests covering compare_hashes outcomes: MATCH, MISMATCH, NO_REFERENCE, INVALID_INPUT."""

    def test_compare_hashes_match(self):
        digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        result = compare_hashes(current_hash=digest, reference_hash=digest)

        assert isinstance(result, IntegrityResult)
        assert result.status == IntegrityStatus.MATCH
        assert result.algorithm == "sha256"
        assert result.current_sha256 == digest
        assert result.reference_sha256 == digest
        assert "matches reference digest" in result.message

    def test_compare_hashes_case_insensitive_match(self):
        lower = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        upper = "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
        result = compare_hashes(current_hash=lower, reference_hash=upper)

        assert result.status == IntegrityStatus.MATCH
        assert result.reference_sha256 == lower

    def test_compare_hashes_mismatch(self):
        digest1 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        digest2 = "a" * 64
        result = compare_hashes(current_hash=digest1, reference_hash=digest2)

        assert result.status == IntegrityStatus.MISMATCH
        assert result.current_sha256 == digest1
        assert result.reference_sha256 == digest2
        assert "does NOT match reference" in result.message
        assert "divergence" in result.message

    def test_compare_hashes_no_reference(self):
        """Absence of reference must return NO_REFERENCE, NEVER match or mismatch."""
        digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        result_none = compare_hashes(current_hash=digest, reference_hash=None)
        assert result_none.status == IntegrityStatus.NO_REFERENCE
        assert result_none.reference_sha256 is None
        assert "No trusted reference" in result_none.message

        result_empty = compare_hashes(current_hash=digest, reference_hash="")
        assert result_empty.status == IntegrityStatus.NO_REFERENCE

    def test_compare_hashes_invalid_input(self):
        """Malformed current or reference hashes must produce INVALID_INPUT."""
        valid = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        # Invalid current hash
        res1 = compare_hashes(current_hash="short", reference_hash=valid)
        assert res1.status == IntegrityStatus.INVALID_INPUT

        # Invalid reference hash
        res2 = compare_hashes(current_hash=valid, reference_hash="bad_reference_hex")
        assert res2.status == IntegrityStatus.INVALID_INPUT

    def test_verify_file_integrity(self, tmp_path):
        payload = b"TruthLens integrity verification fixture."
        file_path = tmp_path / "verified.bin"
        file_path.write_bytes(payload)

        expected_hash = sha256_bytes(payload)
        res = verify_file_integrity(file_path, reference_hash=expected_hash)

        assert res.status == IntegrityStatus.MATCH
        assert res.bytes_hashed == len(payload)

        # Alter file bytes
        file_path.write_bytes(payload + b"_tampered")
        res_tampered = verify_file_integrity(file_path, reference_hash=expected_hash)
        assert res_tampered.status == IntegrityStatus.MISMATCH
