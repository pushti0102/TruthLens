"""
src/inference.py
================
PURPOSE
-------
This is the main entry point for the AI/ML component.

It ties together:
  1. preprocessing.py  — loads and validates the image
  2. detector.py       — runs the actual AI model

Call `run_inference()` from a FastAPI endpoint, a command-line script, or
a test.  The function returns a single structured dictionary so that the
backend team can easily serialise it to JSON.

EXAMPLE (command line)
----------------------
    python -m src.inference path/to/image.jpg

EXAMPLE (Python / FastAPI)
--------------------------
    from src.inference import run_inference
    result = run_inference("uploads/photo.png")
    # result["label"] is "REAL" or "AI_GENERATED"
"""

import sys
import json
from pathlib import Path
from typing import Optional, Union

from src.preprocessing import (
    load_image,
    get_image_info,
    check_document_characteristics,
    PreprocessingError,
)
from src.detector import TruthLensDetector, ModelNotAvailableError


# Module-level singleton — the model is loaded once and reused across calls.
# This avoids reloading the ~330 MB weights on every request.
_detector: Optional[TruthLensDetector] = None


def _get_detector() -> TruthLensDetector:
    """
    Return the shared TruthLensDetector instance, creating it on first call.

    Using a module-level singleton means the model is loaded into memory only
    once per process, which is important when this module is used inside a
    FastAPI application handling many requests.
    """
    global _detector
    if _detector is None:
        _detector = TruthLensDetector()
    return _detector


def compute_ai_likelihood(label: str, confidence: float) -> str:
    """
    Compute cautious likelihood categorization based on model score.

    Avoids treating AI detection as an absolute binary true/false verdict.
    """
    if label == "AI_GENERATED":
        if confidence >= 0.80:
            return "high"
        elif confidence >= 0.60:
            return "moderate"
        else:
            return "inconclusive"
    elif label == "REAL":
        if confidence >= 0.80:
            return "low"
        elif confidence >= 0.60:
            return "moderate"
        else:
            return "inconclusive"
    return "inconclusive"


def run_inference(image_path: Union[str, Path]) -> dict:
    """
    Analyse a single image and return a structured result dictionary.

    This is the main public function of the AI/ML component.  It performs:
      - Path validation and file-type checking
      - Safe image decoding (catches corrupt files)
      - Actual model inference using the pretrained ViT detector
      - Returns a clean, serialisable dictionary

    Parameters
    ----------
    image_path : str or Path
        Absolute or relative path to a PNG, JPEG, or WebP image.

    Returns
    -------
    dict with keys:
        status       (str)  : "success" or "error"
        file_name    (str)  : basename of the input file
        label        (str)  : "REAL" or "AI_GENERATED"  (only on success)
        confidence   (float): model's confidence score in [0, 1]  (only on success)
        raw_scores   (list) : all class probabilities  (only on success)
        model_id     (str)  : model identifier  (only on success)
        inference_ms (float): inference time in milliseconds  (only on success)
        warning      (str)  : authenticity and experimental warning
        ai_likelihood(str)  : "high", "moderate", "low", or "inconclusive"
        image_info   (dict) : {"width", "height", "mode", "aspect_ratio"}
        error        (str)  : human-readable error message  (only on error)
        error_type   (str)  : category of error  (only on error)
    """
    image_path = Path(image_path)
    file_name = image_path.name

    # ── Step 1: Load and validate the image ────────────────────────────────
    try:
        image = load_image(image_path)
    except PreprocessingError as exc:
        return {
            "status": "error",
            "file_name": file_name,
            "error_type": "preprocessing_error",
            "error": str(exc),
        }

    image_info = get_image_info(image)
    doc_meta = check_document_characteristics(image)
    image_info["aspect_ratio"] = doc_meta["aspect_ratio"]

    # ── Step 2: Load the detector (downloads weights on first call) ─────────
    try:
        detector = _get_detector()
    except ModelNotAvailableError as exc:
        return {
            "status": "error",
            "file_name": file_name,
            "image_info": image_info,
            "error_type": "model_not_available",
            "error": str(exc),
        }

    # ── Step 3: Run inference ───────────────────────────────────────────────
    try:
        prediction = detector.predict(image)
    except (ModelNotAvailableError, RuntimeError) as exc:
        return {
            "status": "error",
            "file_name": file_name,
            "image_info": image_info,
            "error_type": "inference_error",
            "error": str(exc),
        }

    # ── Step 4: Cautious categorization & domain analysis ──────────────────
    likelihood = compute_ai_likelihood(prediction["label"], prediction["confidence"])

    warning_msg = "Experimental AI-image detection; this prediction does not prove authenticity."

    result = {
        "status": "success",
        "file_name": file_name,
        "label": prediction["label"],
        "confidence": prediction["confidence"],
        "raw_scores": prediction["raw_scores"],
        "model_id": prediction["model_id"],
        "inference_ms": prediction["inference_ms"],
        "ai_likelihood": likelihood,
        "warning": warning_msg,
        "image_info": image_info,
        "domain_note": "Model was trained on natural and artistic imagery (CIFAKE dataset). It has not been validated on ID cards, credentials, or document scans.",
        "provenance_note": "AI pattern detection does not establish provenance, legal validity, or document authenticity. Cryptographic integrity (SHA-256) and provenance checks must be evaluated independently.",
    }

    if doc_meta["is_likely_document"]:
        result["document_domain_warning"] = (
            f"Input format exhibits characteristics of a {doc_meta['document_hint']}. "
            "Pretrained vision transformers frequently produce high-confidence false positive "
            "AI detections on text documents and ID cards (e.g. PAN cards). This prediction "
            "should be treated with caution and verified using non-visual provenance tools."
        )

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Command-line interface
# Run with:  python -m src.inference path/to/image.jpg
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python -m src.inference <path-to-image>")
        print("Example: python -m src.inference data/real/photo.jpg")
        sys.exit(1)

    img_path = sys.argv[1]
    print(f"\nTruthLens-AI -- Analysing: {img_path}\n")

    result = run_inference(img_path)

    # Pretty-print the result as JSON
    print(json.dumps(result, indent=2))

    if result["status"] == "success":
        label = result["label"]
        conf = result["confidence"] * 100
        ms = result["inference_ms"]
        likelihood = result.get("ai_likelihood", "N/A")
        print(f"\n{'-'*65}")
        print(f"  Model Prediction       : {label}")
        print(f"  Confidence Score       : {conf:.1f}%")
        print(f"  AI-Generated Likelihood: {likelihood.upper()}")
        print(f"  Model ID               : {result['model_id']}")
        print(f"  Inference Time         : {ms:.1f} ms")
        print(f"{'-'*65}")
        print(f"  WARNING: {result['warning']}")

        if "document_domain_warning" in result:
            print(f"\n  [!] DOMAIN WARNING: {result['document_domain_warning']}")

        print("\n  AUTHENTICITY & PROVENANCE NOTICE:")
        print("  - Prediction is an AI visual pattern score, NOT proof of authenticity.")
        print("  - The model does not establish whether a document is genuine or fraudulent.")
        print("  - Cryptographic hashes (SHA-256) and provenance records remain independent.")
        print(f"{'-'*65}\n")
    else:
        print(f"\n[ERROR] {result['error_type']}: {result['error']}\n")
        sys.exit(1)

