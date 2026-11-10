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
    Inspect image geometry to identify document or ID card characteristics.

    Standard ID cards (ISO/IEC 7810 ID-1, such as Indian PAN cards, Aadhaar cards,
    driver licenses, credit cards) have a nominal aspect ratio of 1.586 (or 0.630 in portrait).
    Standard document formats (A4/Letter) have aspect ratios around 1.29 - 1.41 (or 0.70 - 0.77).

    Returns
    -------
    dict with keys:
        aspect_ratio             (float): width / height
        is_likely_document       (bool) : True if aspect ratio matches document / ID card
        document_hint            (str or None): Descriptive label if document-like
    """
    w, h = image.size
    aspect_ratio = round(w / float(h), 4)

    is_id_card = (1.42 <= aspect_ratio <= 1.75) or (0.57 <= aspect_ratio <= 0.70)
    is_doc_page = (1.20 <= aspect_ratio < 1.42) or (0.70 < aspect_ratio <= 0.83)

    if is_id_card:
        hint = "Identity card / credential format (e.g. PAN card, ID-1 card, driving license)"
    elif is_doc_page:
        hint = "Document / certificate page format (e.g. A4 / Letter scan)"
    else:
        hint = None

    return {
        "aspect_ratio": aspect_ratio,
        "is_likely_document": is_id_card or is_doc_page,
        "document_hint": hint,
    }

