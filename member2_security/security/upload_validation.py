"""
TruthLens Secure Image-Upload Validation Module
Member 2: Cryptography & Information Security

Implements multi-layered, defense-in-depth validation for user-submitted media files
in compliance with OWASP File Upload Security Guidance.

DEFENSE-IN-DEPTH LAYERS:
1. File Size Verification:
   Prevents Denial of Service via storage exhaustion or excessive memory consumption.
2. Magic Byte & Binary Header Inspection:
   Validates underlying file signatures (JPEG, PNG, WebP) independent of client MIME headers.
   Instantly detects disguised executables, documents (DOCX/PDF), and archive bombs.
3. Path Traversal & Filename Sanitization:
   Client filenames are stripped and discarded. A secure server-generated UUIDv4 asset ID
   is assigned to prevent overwrite attacks and directory climbing (../).
4. Decompression-Bomb & Truncation Defense:
   Limits Pillow's MAX_IMAGE_PIXELS. Uses image.verify() followed by full decoding load()
   to catch truncated image streams and malformed frame tables safely.
5. Byte Preservation:
   The original raw upload bytes are strictly preserved for SHA-256 integrity hashing;
   files are never silently re-encoded or compressed.
"""

from __future__ import annotations

import io
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Set, Tuple, Union

from PIL import Image, UnidentifiedImageError

# Configuration defaults
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_MAX_WIDTH = 8192
DEFAULT_MAX_HEIGHT = 8192
DEFAULT_MAX_PIXELS = 25_000_000  # 25 Megapixels (prevents decompression bombs)

# Supported image formats
SUPPORTED_FORMATS: Dict[str, Dict[str, Any]] = {
    "JPEG": {
        "extensions": {".jpg", ".jpeg"},
        "mime": "image/jpeg",
        "magic": b"\xff\xd8\xff",
    },
    "PNG": {
        "extensions": {".png"},
        "mime": "image/png",
        "magic": b"\x89PNG\r\n\x1a\n",
    },
    "WEBP": {
        "extensions": {".webp"},
        "mime": "image/webp",
        # WebP has 'RIFF' at 0..4 and 'WEBP' at 8..12
    },
}

# Known dangerous file signatures to reject explicitly
DANGEROUS_MAGIC_SIGNATURES: Dict[str, bytes] = {
    "PDF": b"%PDF",
    "ZIP_OR_OFFICE": b"PK\x03\x04",
    "WINDOWS_EXE": b"MZ",
    "LINUX_ELF": b"\x7fELF",
    "GIF": b"GIF8",
    "JAVA_CLASS": b"\xca\xfe\xba\xbe",
}

# Regex to detect path traversal sequences
PATH_TRAVERSAL_REGEX = re.compile(r"(\.\./|\.\.\\|/|\\)")


class UploadValidationError(Exception):
    """Base exception for upload validation failures."""
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass(frozen=True)
class UploadValidationResult:
    """Structured result returned by secure image upload validation."""

    valid: bool
    detected_format: Optional[str] = None
    file_size_bytes: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    asset_id: Optional[str] = None
    sanitized_filename: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to a JSON-compatible dictionary."""
        return asdict(self)


def sanitize_client_filename(filename: Optional[str]) -> str:
    """
    Sanitize an incoming client-provided filename to extract only its safe base extension.
    Never trust the basename provided by the user.

    Args:
        filename: Client-supplied filename or path.

    Returns:
        Safe lowercased extension with leading dot (e.g. '.jpg'), or empty string if invalid.
    """
    if not filename or not isinstance(filename, str):
        return ""
    # Strip any directory path components regardless of OS
    clean_name = os.path.basename(filename.replace("\\", "/"))
    # Extract extension
    _, ext = os.path.splitext(clean_name)
    clean_ext = ext.strip().lower()
    # Ensure extension contains only alphanumeric characters
    if re.match(r"^\.[a-z0-9]{1,10}$", clean_ext):
        return clean_ext
    return ""


def detect_magic_format(header_bytes: bytes) -> Optional[str]:
    """
    Inspect the initial binary bytes of a file to detect its format.

    Args:
        header_bytes: At least the first 32 bytes of the file.

    Returns:
        Format identifier ('JPEG', 'PNG', 'WEBP') or None if unrecognized.
    """
    if not header_bytes or len(header_bytes) < 12:
        return None

    # Check JPEG
    if header_bytes.startswith(b"\xff\xd8\xff"):
        return "JPEG"

    # Check PNG
    if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"

    # Check WebP (RIFF....WEBP)
    if header_bytes.startswith(b"RIFF") and header_bytes[8:12] == b"WEBP":
        return "WEBP"

    return None


def check_dangerous_signatures(header_bytes: bytes) -> Optional[str]:
    """
    Check if the file starts with signatures of known non-image formats (PDF, DOCX, EXE).

    Returns:
        Description of detected non-image format, or None.
    """
    if not header_bytes:
        return None

    # Check XML/SVG
    header_lower = header_bytes[:64].lower()
    if b"<svg" in header_lower or b"<?xml" in header_lower:
        return "SVG/XML (SVG vectors are disallowed to prevent script injection)"

    for name, magic in DANGEROUS_MAGIC_SIGNATURES.items():
        if header_bytes.startswith(magic):
            return name

    return None


def validate_image_bytes(
    file_bytes: bytes,
    original_filename: Optional[str] = None,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> UploadValidationResult:
    """
    Perform rigorous server-side validation of image bytes.

    Checks:
    1. Size within bounds (0 < size <= max_file_size).
    2. Header magic bytes match supported image formats (JPEG, PNG, WebP).
    3. Rejection of dangerous formats (PDF, DOCX, EXE, SVG).
    4. Safe Pillow decoding with decompression-bomb guard (MAX_IMAGE_PIXELS).
    5. Dimensions check (width, height, total pixel count).
    6. Verification that file is not truncated or corrupted.

    Args:
        file_bytes: Raw binary content of the uploaded file.
        original_filename: Original client filename (for logging/extension comparison).
        max_file_size: Maximum allowed size in bytes.
        max_width: Maximum allowed image width in pixels.
        max_height: Maximum allowed image height in pixels.
        max_pixels: Maximum allowed total pixel count.

    Returns:
        UploadValidationResult with validation status and metadata.
    """
    size_bytes = len(file_bytes) if file_bytes else 0

    # 1. Size Check
    if size_bytes == 0:
        return UploadValidationResult(
            valid=False,
            file_size_bytes=0,
            error_code="EMPTY_FILE",
            error_message="Uploaded file is empty (0 bytes).",
        )

    if size_bytes > max_file_size:
        return UploadValidationResult(
            valid=False,
            file_size_bytes=size_bytes,
            error_code="FILE_TOO_LARGE",
            error_message=f"File size ({size_bytes} bytes) exceeds maximum limit of {max_file_size} bytes.",
        )

    # 2. Dangerous Signatures Check
    header = file_bytes[:64]
    dangerous = check_dangerous_signatures(header)
    if dangerous:
        return UploadValidationResult(
            valid=False,
            file_size_bytes=size_bytes,
            error_code="UNSUPPORTED_MEDIA_TYPE",
            error_message=f"File content signature matches unsupported format '{dangerous}'. "
                          "Only JPEG, PNG, and WebP raster images are accepted.",
        )

    # 3. Magic Bytes Check
    magic_format = detect_magic_format(header)
    if magic_format is None:
        return UploadValidationResult(
            valid=False,
            file_size_bytes=size_bytes,
            error_code="INVALID_MAGIC_BYTES",
            error_message="File binary header does not match any accepted image format (JPEG, PNG, WebP).",
        )

    # 4. Decompression Bomb Protection & Pillow Decoding
    # Configure Pillow pixel limit
    old_max_pixels = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels

    try:
        # Step 4a: Structural verification with verify()
        byte_stream = io.BytesIO(file_bytes)
        with Image.open(byte_stream) as img:
            detected_pil_format = img.format
            # Verify basic file headers and structural integrity
            img.verify()

        # Step 4b: Re-open to read dimensions and perform full raster load
        byte_stream.seek(0)
        with Image.open(byte_stream) as img:
            width, height = img.size
            total_pixels = width * height

            # Check dimensions
            if width <= 0 or height <= 0:
                return UploadValidationResult(
                    valid=False,
                    detected_format=magic_format,
                    file_size_bytes=size_bytes,
                    error_code="INVALID_DIMENSIONS",
                    error_message=f"Invalid image dimensions: {width}x{height}.",
                )

            if width > max_width or height > max_height:
                return UploadValidationResult(
                    valid=False,
                    detected_format=magic_format,
                    file_size_bytes=size_bytes,
                    width=width,
                    height=height,
                    error_code="DIMENSIONS_EXCEEDED",
                    error_message=f"Image dimensions ({width}x{height}) exceed maximum allowed ({max_width}x{max_height}).",
                )

            if total_pixels > max_pixels:
                return UploadValidationResult(
                    valid=False,
                    detected_format=magic_format,
                    file_size_bytes=size_bytes,
                    width=width,
                    height=height,
                    error_code="DECOMPRESSION_BOMB_RISK",
                    error_message=f"Image total pixels ({total_pixels}) exceed safe limit ({max_pixels}).",
                )

            # Full image load: actually decompress the image data to catch truncated or corrupted raster data
            img.load()

    except Image.DecompressionBombError as exc:
        return UploadValidationResult(
            valid=False,
            detected_format=magic_format,
            file_size_bytes=size_bytes,
            error_code="DECOMPRESSION_BOMB_RISK",
            error_message=f"Decompression bomb detected: {exc}",
        )
    except UnidentifiedImageError as exc:
        return UploadValidationResult(
            valid=False,
            detected_format=magic_format,
            file_size_bytes=size_bytes,
            error_code="CORRUPT_IMAGE",
            error_message=f"Image data is corrupted and cannot be identified: {exc}",
        )
    except (IOError, SyntaxError, ValueError) as exc:
        return UploadValidationResult(
            valid=False,
            detected_format=magic_format,
            file_size_bytes=size_bytes,
            error_code="MALFORMED_IMAGE_DATA",
            error_message=f"Image file is truncated or structurally malformed: {exc}",
        )
    finally:
        Image.MAX_IMAGE_PIXELS = old_max_pixels

    # 5. Generate secure server-side asset ID and storage filename
    asset_id = str(uuid.uuid4())
    # Choose standard extension matching the verified format
    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    safe_ext = ext_map.get(magic_format, ".bin")
    sanitized_filename = f"{asset_id}{safe_ext}"

    return UploadValidationResult(
        valid=True,
        detected_format=magic_format,
        file_size_bytes=size_bytes,
        width=width,
        height=height,
        asset_id=asset_id,
        sanitized_filename=sanitized_filename,
    )


def save_validated_upload(
    file_bytes: bytes,
    validation_result: UploadValidationResult,
    target_dir: Union[str, Path],
) -> Path:
    """
    Safely persist validated image bytes to disk under the server-generated asset filename.

    Args:
        file_bytes: Raw uncompressed original file bytes.
        validation_result: Successful UploadValidationResult.
        target_dir: Destination directory (MUST be outside public webroot).

    Returns:
        Absolute Path to saved file.

    Raises:
        UploadValidationError: If validation_result is invalid or target path traversal detected.
    """
    if not validation_result.valid or not validation_result.sanitized_filename:
        raise UploadValidationError(
            error_code="INVALID_UPLOAD",
            message="Cannot save unvalidated or rejected upload.",
        )

    # Prevent path traversal
    filename = validation_result.sanitized_filename
    if PATH_TRAVERSAL_REGEX.search(filename) or ".." in filename:
        raise UploadValidationError(
            error_code="PATH_TRAVERSAL_DETECTED",
            message="Security violation: Detected potential path traversal in filename.",
        )

    storage_dir = Path(target_dir).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)

    dest_path = (storage_dir / filename).resolve()

    # Ensure dest_path is strictly within storage_dir
    try:
        dest_path.relative_to(storage_dir)
    except ValueError as exc:
        raise UploadValidationError(
            error_code="PATH_TRAVERSAL_DETECTED",
            message="Target storage path escapes configured storage root.",
        ) from exc

    # Write file atomically with exclusive creation to prevent overwrite
    try:
        with open(dest_path, "xb") as f:
            f.write(file_bytes)
    except FileExistsError:
        raise UploadValidationError(
            error_code="FILE_ALREADY_EXISTS",
            message=f"Collision detected: File '{dest_path.name}' already exists.",
        )

    return dest_path
