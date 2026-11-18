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
import argparse
from pathlib import Path
from typing import Optional, Union, Dict

from src.preprocessing import (
    load_image,
    get_image_info,
    check_document_characteristics,
    PreprocessingError,
)
from src.detector import (
    TruthLensDetector,
    ModelNotAvailableError,
    DEFAULT_MODEL_KEY,
    resolve_model_info,
)


# Module-level registry cache — models are loaded on demand and cached per model key/id.
# This avoids reloading heavy weights on every request while ensuring distinct instances per model.
_detectors: Dict[str, TruthLensDetector] = {}


def _get_detector(model_name: str = DEFAULT_MODEL_KEY) -> TruthLensDetector:
    """
    Return the cached TruthLensDetector instance for the requested model,
    creating it on first call.

    Parameters
    ----------
    model_name : str
        Model shortcut ('current', 'smaug') or full Hugging Face model ID.

    Returns
    -------
    TruthLensDetector
    """
    global _detectors
    info = resolve_model_info(model_name)
    key = info["key"]

    if key not in _detectors:
        print(f"\nSelected Model Option  : {key}")
        print(f"Target Model Identifier: {info['model_id']}\n")
        _detectors[key] = TruthLensDetector(model_id=info["model_id"])

    return _detectors[key]


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


def run_inference(image_path: Union[str, Path], model: str = DEFAULT_MODEL_KEY) -> dict:
    """
    Analyse a single image and return a structured result dictionary.

    Parameters
    ----------
    image_path : str or Path
        Absolute or relative path to a PNG, JPEG, or WebP image.
    model : str
        Model selector ('current' or 'smaug'). Defaults to 'current'.

    Returns
    -------
    dict conforming to the structured output contract.
    """
    image_path = Path(image_path)
    file_name = image_path.name

    # ── Step 1: Resolve target model configuration ─────────────────────────
    try:
        model_info = resolve_model_info(model)
        target_model_id = model_info["model_id"]
    except ValueError as exc:
        return {
            "status": "error",
            "file_name": file_name,
            "error_type": "invalid_model_selection",
            "error": str(exc),
            "model_id": None,
        }

    # ── Step 2: Load and validate the image ────────────────────────────────
    try:
        image = load_image(image_path)
    except PreprocessingError as exc:
        return {
            "status": "error",
            "file_name": file_name,
            "error_type": "preprocessing_error",
            "error": str(exc),
            "model_id": target_model_id,
        }

    image_info = get_image_info(image)
    doc_meta = check_document_characteristics(image)
    image_info["aspect_ratio"] = doc_meta["aspect_ratio"]

    # ── Step 3: Load the detector (downloads weights on first call) ─────────
    try:
        detector = _get_detector(model_name=model)
    except (ModelNotAvailableError, Exception) as exc:
        # Strict rule: NEVER silently fall back to current model if Smaug fails!
        return {
            "status": "error",
            "file_name": file_name,
            "image_info": image_info,
            "error_type": "model_not_available",
            "error": str(exc),
            "model_id": target_model_id,
        }

    # Verify detector loaded the exact target model ID requested
    actual_model_id = getattr(detector, "model_id", None)
    if isinstance(actual_model_id, str) and actual_model_id != target_model_id:
        return {
            "status": "error",
            "file_name": file_name,
            "image_info": image_info,
            "error_type": "model_mismatch_error",
            "error": f"Model mismatch: requested '{target_model_id}', but loaded '{actual_model_id}'. Silent fallback is prohibited.",
            "model_id": actual_model_id,
        }

    print(f"Loaded Model ID        : {actual_model_id}\n")

    # ── Step 4: Run inference ───────────────────────────────────────────────
    try:
        prediction = detector.predict(image)
    except (ModelNotAvailableError, RuntimeError, Exception) as exc:
        return {
            "status": "error",
            "file_name": file_name,
            "image_info": image_info,
            "error_type": "inference_error",
            "error": str(exc),
            "model_id": actual_model_id or target_model_id,
        }

    # ── Step 5: Cautious categorization & domain analysis ──────────────────
    likelihood = compute_ai_likelihood(prediction["label"], prediction["confidence"])
    outcome = "INCONCLUSIVE" if likelihood == "inconclusive" else prediction["label"]

    warning_msg = "Experimental AI-image detection; this prediction does not prove authenticity."

    calibration_note = (
        "Raw softmax/sigmoid values reflect uncalibrated distance to the decision boundary. "
        "Extreme values (e.g. 99.9%) indicate high model confidence in visual feature separation, "
        "NOT a calibrated posterior probability of authenticity. "
        "Borderline scores (< 60%) or out-of-domain signals are treated as inconclusive."
    )

    result = {
        "status": "success",
        "file_name": file_name,
        "label": prediction["label"],
        "outcome": outcome,
        "confidence": prediction["confidence"],
        "raw_scores": prediction["raw_scores"],
        "model_id": prediction["model_id"],
        "model_name": model_info.get("name"),
        "architecture": model_info.get("architecture_name", model_info.get("architecture")),
        "inference_ms": prediction["inference_ms"],
        "ai_likelihood": likelihood,
        "warning": warning_msg,
        "calibration_note": calibration_note,
        "image_info": image_info,
        "domain_note": model_info.get("domain_note", model_info.get("description", "")),
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


def parse_args(args: Optional[list] = None):
    parser = argparse.ArgumentParser(
        description="TruthLens-AI Single Image Inference CLI with Multi-Model Support"
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="Path to the image file to analyse (PNG, JPEG, WebP).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_KEY,
        choices=["current", "smaug"],
        help="Model to use for inference: 'current' (dima806 ViT) or 'smaug' (abacusai EmbeddingGemma-2). Default: current.",
    )
    return parser.parse_args(args)


# ──────────────────────────────────────────────────────────────────────────────
# Command-line interface
# Run with:  python -m src.inference path/to/image.jpg [--model current|smaug]
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    img_path = args.image_path
    selected_model = args.model

    print(f"\nTruthLens-AI -- Analysing: {img_path}")
    result = run_inference(img_path, model=selected_model)

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
        err_type = result.get("error_type", "error")
        err_msg = result.get("error", "Unknown error")
        print(f"\n[ERROR] {err_type}: {err_msg}\n")
        sys.exit(1)

