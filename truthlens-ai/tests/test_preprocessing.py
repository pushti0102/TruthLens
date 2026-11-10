"""
tests/test_preprocessing.py
============================
Tests for the image loading and validation module (src/preprocessing.py).

These tests do NOT require the model weights to be downloaded.  They only
test file I/O and the PIL loading layer, so they run fast on any machine.

Run with:
    pytest tests/test_preprocessing.py -v
"""

import io
import os
import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image

from src.preprocessing import (
    load_image,
    validate_image_path,
    get_image_info,
    PreprocessingError,
    SUPPORTED_EXTENSIONS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — build tiny test images in memory without touching disk permanently
# ─────────────────────────────────────────────────────────────────────────────

def make_valid_jpeg(tmp_path: Path, filename: str = "test.jpg") -> Path:
    """Create a minimal valid 4×4 RGB JPEG on disk."""
    img = Image.new("RGB", (4, 4), color=(100, 150, 200))
    p = tmp_path / filename
    img.save(p, format="JPEG")
    return p


def make_valid_png(tmp_path: Path, filename: str = "test.png") -> Path:
    """Create a minimal valid 4×4 RGB PNG on disk."""
    img = Image.new("RGB", (4, 4), color=(10, 20, 30))
    p = tmp_path / filename
    img.save(p, format="PNG")
    return p


def make_rgba_png(tmp_path: Path) -> Path:
    """Create a 4×4 RGBA PNG (has an alpha channel)."""
    img = Image.new("RGBA", (4, 4), color=(10, 20, 30, 128))
    p = tmp_path / "rgba.png"
    img.save(p, format="PNG")
    return p


def make_grayscale_png(tmp_path: Path) -> Path:
    """Create a 4×4 grayscale PNG."""
    img = Image.new("L", (4, 4), color=128)
    p = tmp_path / "gray.png"
    img.save(p, format="PNG")
    return p


def make_corrupt_file(tmp_path: Path, filename: str = "corrupt.jpg") -> Path:
    """Write random bytes that are not a valid image."""
    p = tmp_path / filename
    p.write_bytes(b"\x00\x01\x02\x03\x04\x05\xff\xfe\xfd" * 10)
    return p


def make_truncated_jpeg(tmp_path: Path) -> Path:
    """Write the first few bytes of a valid JPEG, then stop (truncated)."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    full_bytes = buf.read()
    p = tmp_path / "truncated.jpg"
    # Write only the first 50 bytes of the JPEG
    p.write_bytes(full_bytes[:50])
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Tests: validate_image_path
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateImagePath:

    def test_valid_jpeg_path(self, tmp_path):
        """A real JPEG file should pass validation."""
        p = make_valid_jpeg(tmp_path)
        result = validate_image_path(p)
        assert result == p.resolve()

    def test_valid_png_path(self, tmp_path):
        """A real PNG file should pass validation."""
        p = make_valid_png(tmp_path)
        validate_image_path(p)  # should not raise

    def test_missing_file_raises(self, tmp_path):
        """A path pointing to a non-existent file should raise PreprocessingError."""
        fake_path = tmp_path / "does_not_exist.jpg"
        with pytest.raises(PreprocessingError, match="File not found"):
            validate_image_path(fake_path)

    def test_unsupported_extension_raises(self, tmp_path):
        """A .gif file should be rejected with a clear message."""
        p = tmp_path / "animation.gif"
        p.write_bytes(b"GIF89a")  # minimal GIF header
        with pytest.raises(PreprocessingError, match="Unsupported file type"):
            validate_image_path(p)

    def test_unsupported_extension_pdf(self, tmp_path):
        """A .pdf file should be rejected."""
        p = tmp_path / "document.pdf"
        p.write_bytes(b"%PDF-1.4")
        with pytest.raises(PreprocessingError, match="Unsupported file type"):
            validate_image_path(p)

    def test_directory_path_raises(self, tmp_path):
        """Passing a directory instead of a file should raise."""
        with pytest.raises(PreprocessingError):
            validate_image_path(tmp_path)

    def test_supported_extensions_set(self):
        """Verify all expected extensions are listed."""
        assert ".jpg" in SUPPORTED_EXTENSIONS
        assert ".jpeg" in SUPPORTED_EXTENSIONS
        assert ".png" in SUPPORTED_EXTENSIONS
        assert ".webp" in SUPPORTED_EXTENSIONS

    def test_string_path_accepted(self, tmp_path):
        """validate_image_path should accept plain strings, not just Path objects."""
        p = make_valid_jpeg(tmp_path)
        result = validate_image_path(str(p))
        assert isinstance(result, Path)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: load_image
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadImage:

    def test_load_jpeg_returns_pil_image(self, tmp_path):
        """Loading a valid JPEG should return a PIL Image."""
        p = make_valid_jpeg(tmp_path)
        img = load_image(p)
        assert isinstance(img, Image.Image)

    def test_load_png_returns_pil_image(self, tmp_path):
        """Loading a valid PNG should return a PIL Image."""
        p = make_valid_png(tmp_path)
        img = load_image(p)
        assert isinstance(img, Image.Image)

    def test_output_is_rgb(self, tmp_path):
        """load_image must always return an RGB image, regardless of input mode."""
        p = make_valid_jpeg(tmp_path)
        img = load_image(p)
        assert img.mode == "RGB"

    def test_rgba_converted_to_rgb(self, tmp_path):
        """An RGBA (4-channel) PNG should be converted to RGB."""
        p = make_rgba_png(tmp_path)
        img = load_image(p)
        assert img.mode == "RGB"

    def test_grayscale_converted_to_rgb(self, tmp_path):
        """A grayscale PNG should be converted to RGB."""
        p = make_grayscale_png(tmp_path)
        img = load_image(p)
        assert img.mode == "RGB"

    def test_corrupt_file_raises_preprocessing_error(self, tmp_path):
        """A file with garbage bytes should raise PreprocessingError."""
        p = make_corrupt_file(tmp_path)
        with pytest.raises(PreprocessingError):
            load_image(p)

    def test_missing_file_raises_preprocessing_error(self, tmp_path):
        """A non-existent file should raise PreprocessingError."""
        p = tmp_path / "ghost.jpg"
        with pytest.raises(PreprocessingError, match="File not found"):
            load_image(p)

    def test_wrong_extension_raises_preprocessing_error(self, tmp_path):
        """A .bmp file should raise PreprocessingError before even trying to open it."""
        p = tmp_path / "image.bmp"
        p.write_bytes(b"BM" + b"\x00" * 50)
        with pytest.raises(PreprocessingError, match="Unsupported file type"):
            load_image(p)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: get_image_info
# ─────────────────────────────────────────────────────────────────────────────

class TestGetImageInfo:

    def test_returns_correct_dimensions(self, tmp_path):
        """get_image_info should return the correct width and height."""
        img = Image.new("RGB", (64, 32), color=(0, 0, 0))
        info = get_image_info(img)
        assert info["width"] == 64
        assert info["height"] == 32

    def test_returns_mode(self, tmp_path):
        """get_image_info should include the image mode."""
        img = Image.new("RGB", (10, 10))
        info = get_image_info(img)
        assert info["mode"] == "RGB"

    def test_info_has_required_keys(self, tmp_path):
        """Result dictionary must contain width, height, and mode."""
        img = Image.new("RGB", (8, 8))
        info = get_image_info(img)
        assert "width" in info
        assert "height" in info
        assert "mode" in info
