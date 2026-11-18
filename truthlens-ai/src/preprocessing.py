"""
src/preprocessing.py
====================
PURPOSE
-------
Validate, load, and resize images before they reach the detector model.

WHY THIS FILE EXISTS
--------------------
The detector expects a specific input format (a PIL Image object, correctly
sized and in RGB mode).  If we pass a corrupt file or an unsupported format,
transformers will raise cryptic internal errors.  This module catches those
problems early and converts them into clear, human-readable messages.

WHAT IT DOES
------------
1. Checks that the file actually exists.
2. Checks that the file extension is allowed (PNG, JPEG, WebP).
3. Tries to open and decode the image (catches truncated / corrupt files).
4. Converts the image to RGB (removes alpha channels, handles grayscale).
5. Returns a clean PIL Image, ready for the model's feature extractor.
"""

import os
from pathlib import Path
from typing import Union

from PIL import Image, UnidentifiedImageError


# File types this detector supports.
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class PreprocessingError(Exception):
    """Raised when an image cannot be loaded or is unsupported."""
    pass


def validate_image_path(image_path: Union[str, Path]) -> Path:
    """
    Check that the file exists and has a supported extension.

    Parameters
    ----------
    image_path : str or Path
        Path to the image file.

    Returns
    -------
    Path
        A resolved Path object.

    Raises
    ------
    PreprocessingError
        If the file does not exist or has an unsupported extension.
    """
    path = Path(image_path).resolve()

    if not path.exists():
        raise PreprocessingError(
            f"File not found: '{path}'\n"
            "Make sure you typed the correct path."
        )

    if not path.is_file():
        raise PreprocessingError(
            f"'{path}' is a directory, not a file."
        )

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise PreprocessingError(
            f"Unsupported file type: '{ext}'\n"
            f"TruthLens-AI accepts: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    return path


def load_image(image_path: Union[str, Path]) -> Image.Image:
    """
    Load an image from disk and convert it to RGB mode.

    This function validates the path, then tries to open the file.  It
    detects corrupt or truncated files and raises a clear error.

    Parameters
    ----------
    image_path : str or Path
        Path to a PNG, JPEG, or WebP image.

    Returns
    -------
    PIL.Image.Image
        An RGB image, ready to be passed to the model.

    Raises
    ------
    PreprocessingError
        If the file does not exist, is unsupported, or is corrupt / unreadable.
    """
    path = validate_image_path(image_path)

    try:
        # LOAD=True forces the entire file to be decoded, revealing truncation.
        img = Image.open(path)
        img.load()  # actually read all pixel data (catches truncated files)
    except UnidentifiedImageError:
        raise PreprocessingError(
            f"Cannot identify '{path.name}' as an image.\n"
            "The file may be corrupt, empty, or not actually an image despite "
            "its extension."
        )
    except OSError as exc:
        raise PreprocessingError(
            f"Failed to open '{path.name}': {exc}\n"
            "The file may be truncated or corrupt."
        )

    # Convert to RGB so the model always receives 3 channels.
    # This handles: RGBA (removes alpha), grayscale (L → RGB), palette (P → RGB).
    if img.mode != "RGB":
        img = img.convert("RGB")

    return img


def get_image_info(image: Image.Image) -> dict:
    """
    Return basic metadata about a loaded image.

    Parameters
    ----------
    image : PIL.Image.Image
        A PIL image (usually the output of load_image).

    Returns
    -------
    dict
        Dictionary with 'width', 'height', and 'mode'.
    """
    return {
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
    }


def check_document_characteristics(image: Image.Image) -> dict:
    """
    Inspect image geometry and visual surface evidence to determine if the image
    is likely a scanned document, ID card, or certificate.

    Aspect ratio alone is NEVER used as definitive proof because standard camera
    and smartphone photos commonly share similar aspect ratios (e.g., 4:3 = 1.333,
    3:2 = 1.500, 16:9 = 1.778). Instead, geometry is combined with visual/color
    evidence (background paper uniformity, low color saturation).

    If evidence is insufficient or conflicting, the document classification
    is reported as inconclusive (False).

    Returns
    -------
    dict with keys:
        aspect_ratio       (float): width / height
        is_likely_document (bool) : True if visual and geometric evidence confirms document
        document_hint      (str or None): Descriptive label if document-like, else None
    """
    w, h = image.size
    aspect_ratio = round(w / float(h), 4)

    # Standard photographic aspect ratios (within 3% tolerance)
    standard_photo_ratios = [
        4 / 3, 3 / 4,
        3 / 2, 2 / 3,
        16 / 9, 9 / 16,
        1.0,
    ]
    is_standard_photo_aspect = any(
        abs(aspect_ratio - r) / r < 0.03 for r in standard_photo_ratios
    )

    # Sample a small thumbnail to evaluate visual/color layout (fast, < 5ms)
    thumb = image.resize((128, 128)).convert("RGB")
    try:
        raw_data = thumb.get_flattened_data() if hasattr(thumb, "get_flattened_data") else list(thumb.getdata())
    except Exception:
        raw_data = list(thumb.getdata())

    total_pixels = 128 * 128
    light_paper_pixels = 0
    total_sat = 0.0

    if isinstance(raw_data, (bytes, bytearray)) or (raw_data and isinstance(raw_data[0], int)):
        for i in range(0, len(raw_data) - 2, 3):
            r, g, b = raw_data[i], raw_data[i + 1], raw_data[i + 2]
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            sat = (max_c - min_c) / max_c if max_c > 0 else 0.0
            total_sat += sat
            if min_c > 200 and sat < 0.15:
                light_paper_pixels += 1
    else:
        for r, g, b in raw_data:
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            sat = (max_c - min_c) / max_c if max_c > 0 else 0.0
            total_sat += sat
            if min_c > 200 and sat < 0.15:
                light_paper_pixels += 1

    paper_ratio = light_paper_pixels / total_pixels
    avg_sat = total_sat / total_pixels

    # ID-1 aspect ratio is approximately 1.586 (width/height for cards like PAN, Aadhaar, driving license)
    is_id_card_ratio = (1.52 <= aspect_ratio <= 1.66) or (0.60 <= aspect_ratio <= 0.66)

    is_document = False
    hint = None

    # Decision requiring visual paper evidence combined with geometry
    if paper_ratio >= 0.35 and is_id_card_ratio:
        # Uniform light card background with specific ID-1 geometry
        is_document = True
        hint = "Identity card / credential format (e.g. PAN card, ID-1 card, driving license)"
    elif paper_ratio >= 0.45 and avg_sat < 0.18:
        # Strong visual document evidence (predominantly light/white paper with low saturation text)
        is_document = True
        hint = "Document / certificate page format (e.g. A4 / Letter scan)"
    elif is_standard_photo_aspect and paper_ratio < 0.35:
        # Standard camera photo with natural color distribution
        is_document = False
        hint = None
    else:
        # Ambiguous geometry or low visual certainty -> report inconclusive (not flagged as document)
        is_document = False
        hint = None

    return {
        "aspect_ratio": aspect_ratio,
        "is_likely_document": is_document,
        "document_hint": hint,
    }

