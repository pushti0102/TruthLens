"""
Unit and Security Tests for Secure Image-Upload Validation Module
Member 2: Cryptography & Information Security
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from member2_security.security.upload_validation import (
    UploadValidationError,
    UploadValidationResult,
    check_dangerous_signatures,
    detect_magic_format,
    sanitize_client_filename,
    save_validated_upload,
    validate_image_bytes,
)


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Create a minimal, valid JPEG image."""
    buffer = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def valid_png_bytes() -> bytes:
    """Create a minimal, valid PNG image."""
    buffer = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(0, 255, 0))
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def valid_webp_bytes() -> bytes:
    """Create a minimal, valid WebP image."""
    buffer = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(0, 0, 255))
    img.save(buffer, format="WEBP")
    return buffer.getvalue()


class TestUploadValidationSuccess:
    """Tests for valid image uploads conforming to TruthLens standards."""

    def test_valid_jpeg_accepted(self, valid_jpeg_bytes):
        res = validate_image_bytes(valid_jpeg_bytes, original_filename="photo.jpg")
        assert res.valid is True
        assert res.detected_format == "JPEG"
        assert res.width == 100
        assert res.height == 100
        assert res.file_size_bytes == len(valid_jpeg_bytes)
        assert res.asset_id is not None
        assert res.sanitized_filename.endswith(".jpg")

    def test_valid_png_accepted(self, valid_png_bytes):
        res = validate_image_bytes(valid_png_bytes, original_filename="diagram.png")
        assert res.valid is True
        assert res.detected_format == "PNG"
        assert res.width == 100
        assert res.height == 100
        assert res.sanitized_filename.endswith(".png")

    def test_valid_webp_accepted(self, valid_webp_bytes):
        res = validate_image_bytes(valid_webp_bytes, original_filename="snapshot.webp")
        assert res.valid is True
        assert res.detected_format == "WEBP"
        assert res.width == 100
        assert res.height == 100
        assert res.sanitized_filename.endswith(".webp")


class TestUploadValidationSecurityFailures:
    """Tests verifying rejection of dangerous, malformed, or hostile files."""

    def test_empty_file_rejected(self):
        res = validate_image_bytes(b"", original_filename="empty.jpg")
        assert res.valid is False
        assert res.error_code == "EMPTY_FILE"

    def test_oversized_file_rejected(self, valid_jpeg_bytes):
        # Set max_file_size lower than fixture length
        res = validate_image_bytes(
            valid_jpeg_bytes,
            original_filename="large.jpg",
            max_file_size=50,
        )
        assert res.valid is False
        assert res.error_code == "FILE_TOO_LARGE"

    def test_renamed_executable_rejected(self):
        """A Windows PE executable renamed to .jpg must be rejected via magic bytes."""
        fake_exe = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100
        res = validate_image_bytes(fake_exe, original_filename="malicious.jpg")
        assert res.valid is False
        assert res.error_code == "UNSUPPORTED_MEDIA_TYPE"

    def test_renamed_pdf_rejected(self):
        """A PDF renamed to .png must be rejected."""
        fake_pdf = b"%PDF-1.7\n%Fake PDF content for test" + b"\x00" * 100
        res = validate_image_bytes(fake_pdf, original_filename="document.png")
        assert res.valid is False
        assert res.error_code == "UNSUPPORTED_MEDIA_TYPE"

    def test_renamed_docx_rejected(self):
        """A ZIP/DOCX file renamed to .webp must be rejected."""
        fake_docx = b"PK\x03\x04\x14\x00\x00\x00" + b"\x00" * 100
        res = validate_image_bytes(fake_docx, original_filename="resume.webp")
        assert res.valid is False
        assert res.error_code == "UNSUPPORTED_MEDIA_TYPE"

    def test_truncated_image_rejected(self, valid_jpeg_bytes):
        """A truncated JPEG stream must fail decode verification."""
        truncated_bytes = valid_jpeg_bytes[: len(valid_jpeg_bytes) // 3]
        res = validate_image_bytes(truncated_bytes, original_filename="truncated.jpg")
        assert res.valid is False
        assert res.error_code in ("MALFORMED_IMAGE_DATA", "CORRUPT_IMAGE")

    def test_decompression_bomb_dimensions_rejected(self):
        """An image whose dimensions exceed max_pixels must be rejected."""
        buffer = io.BytesIO()
        # Create image with 2000x2000 = 4,000,000 pixels
        img = Image.new("RGB", (2000, 2000), color=(128, 128, 128))
        img.save(buffer, format="PNG")
        big_pixels_bytes = buffer.getvalue()

        # Reject if limit is 1,000,000 pixels
        res = validate_image_bytes(
            big_pixels_bytes,
            original_filename="large_pixels.png",
            max_pixels=1_000_000,
        )
        assert res.valid is False
        assert res.error_code in ("DECOMPRESSION_BOMB_RISK", "DIMENSIONS_EXCEEDED")


class TestPathTraversalAndSafeStorage:
    """Tests ensuring client filenames cannot escape storage roots or overwrite files."""

    def test_sanitize_client_filename(self):
        assert sanitize_client_filename("../../etc/passwd.jpg") == ".jpg"
        assert sanitize_client_filename("C:\\Windows\\System32\\malware.png") == ".png"
        assert sanitize_client_filename("normal_picture.jpeg") == ".jpeg"
        assert sanitize_client_filename("no_extension") == ""
        assert sanitize_client_filename("script.exe.jpg") == ".jpg"

    def test_save_validated_upload_path_traversal_prevented(self, valid_jpeg_bytes, tmp_path):
        """Attempting to save with a path traversal sequence in filename must raise error."""
        storage_dir = tmp_path / "safe_storage"

        malicious_result = UploadValidationResult(
            valid=True,
            sanitized_filename="../../traversal.jpg",
            file_size_bytes=len(valid_jpeg_bytes),
        )

        with pytest.raises(UploadValidationError, match="path traversal"):
            save_validated_upload(valid_jpeg_bytes, malicious_result, storage_dir)

    def test_save_validated_upload_persists_unaltered_bytes(self, valid_jpeg_bytes, tmp_path):
        """Original file bytes must be preserved byte-for-byte upon saving."""
        storage_dir = tmp_path / "safe_storage"
        val = validate_image_bytes(valid_jpeg_bytes, original_filename="user_photo.jpg")

        saved_path = save_validated_upload(valid_jpeg_bytes, val, storage_dir)

        assert saved_path.exists()
        assert saved_path.read_bytes() == valid_jpeg_bytes
        # Filename should be server-assigned UUID, not original 'user_photo.jpg'
        assert saved_path.name != "user_photo.jpg"
        assert saved_path.name == val.sanitized_filename
