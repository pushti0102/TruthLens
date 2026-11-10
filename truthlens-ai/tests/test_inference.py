"""
tests/test_inference.py
=======================
Tests for the top-level inference pipeline (src/inference.py).

These tests verify that run_inference() always returns a structured
dictionary and never raises an exception, regardless of the input.

Tests that require model weights are guarded with @pytest.mark.integration.

Run without model weights:
    pytest tests/test_inference.py -v

Run with model weights (first run downloads ~330 MB):
    pytest tests/test_inference.py -v --integration
"""

import io
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from src.inference import run_inference
from src.detector import ModelNotAvailableError


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_jpeg(tmp_path: Path, name: str = "photo.jpg") -> Path:
    img = Image.new("RGB", (64, 64), color=(80, 160, 240))
    p = tmp_path / name
    img.save(p, format="JPEG")
    return p


def make_png(tmp_path: Path, name: str = "photo.png") -> Path:
    img = Image.new("RGB", (32, 32), color=(200, 100, 50))
    p = tmp_path / name
    img.save(p, format="PNG")
    return p


def make_corrupt(tmp_path: Path, name: str = "bad.jpg") -> Path:
    p = tmp_path / name
    p.write_bytes(b"\xff\xd8\xff" + b"\x00" * 5)  # truncated JPEG header
    return p


def make_unsupported(tmp_path: Path) -> Path:
    p = tmp_path / "clip.gif"
    p.write_bytes(b"GIF89a\x01\x00\x01\x00")
    return p


def mock_predict_result(label: str = "REAL", confidence: float = 0.95):
    """Build what TruthLensDetector.predict() returns."""
    other_label = "AI_GENERATED" if label == "REAL" else "REAL"
    return {
        "label": label,
        "confidence": confidence,
        "raw_scores": [
            {"label": label, "score": confidence},
            {"label": other_label, "score": round(1.0 - confidence, 4)},
        ],
        "model_id": "dima806/ai_vs_real_image_detection",
        "inference_ms": 123.4,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tests: output structure on success
# ─────────────────────────────────────────────────────────────────────────────

class TestInferenceSuccess:
    """These tests mock the detector so no model weights are needed."""

    @pytest.fixture(autouse=True)
    def patch_detector(self):
        """Replace _get_detector() with a mock that always returns REAL."""
        mock_detector = MagicMock()
        mock_detector.model_id = "dima806/ai_vs_real_image_detection"
        mock_detector.predict.return_value = mock_predict_result("REAL", 0.93)
        with patch("src.inference._get_detector", return_value=mock_detector):
            yield

    def test_returns_dict(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p)
        assert isinstance(result, dict)

    def test_status_is_success(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p)
        assert result["status"] == "success"

    def test_has_all_required_keys(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p)
        for key in ("status", "label", "confidence", "raw_scores",
                    "model_id", "inference_ms", "image_info", "file_name"):
            assert key in result, f"Missing key in result: '{key}'"

    def test_label_is_canonical(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p)
        assert result["label"] in ("REAL", "AI_GENERATED")

    def test_confidence_in_range(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_image_info_contains_dimensions(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p)
        info = result["image_info"]
        assert "width" in info
        assert "height" in info
        assert info["width"] == 64
        assert info["height"] == 64

    def test_file_name_is_basename(self, tmp_path):
        p = make_jpeg(tmp_path, "my_photo.jpg")
        result = run_inference(p)
        assert result["file_name"] == "my_photo.jpg"

    def test_png_input_works(self, tmp_path):
        p = make_png(tmp_path)
        result = run_inference(p)
        assert result["status"] == "success"

    def test_string_path_accepted(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(str(p))  # pass a string, not a Path
        assert result["status"] == "success"

    def test_ai_generated_label(self, tmp_path):
        """When model says FAKE, label should be AI_GENERATED."""
        mock_det = MagicMock()
        mock_det.model_id = "dima806/ai_vs_real_image_detection"
        mock_det.predict.return_value = mock_predict_result("AI_GENERATED", 0.87)
        with patch("src.inference._get_detector", return_value=mock_det):
            p = make_jpeg(tmp_path)
            result = run_inference(p)
        assert result["label"] == "AI_GENERATED"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: error handling — never raises, always returns dict with error keys
# ─────────────────────────────────────────────────────────────────────────────

class TestInferenceErrors:

    def test_missing_file_returns_error_dict(self, tmp_path):
        """A non-existent file should return an error dict, not raise."""
        result = run_inference(tmp_path / "ghost.jpg")
        assert result["status"] == "error"
        assert "error" in result
        assert "error_type" in result

    def test_missing_file_error_type(self, tmp_path):
        result = run_inference(tmp_path / "ghost.jpg")
        assert result["error_type"] == "preprocessing_error"

    def test_unsupported_extension_returns_error(self, tmp_path):
        p = make_unsupported(tmp_path)
        result = run_inference(p)
        assert result["status"] == "error"
        assert result["error_type"] == "preprocessing_error"

    def test_corrupt_file_returns_error(self, tmp_path):
        p = make_corrupt(tmp_path)
        result = run_inference(p)
        assert result["status"] == "error"

    def test_model_not_available_returns_error(self, tmp_path):
        """If the model can't load, return an error dict (not raise)."""
        p = make_jpeg(tmp_path)
        with patch("src.inference._get_detector",
                   side_effect=ModelNotAvailableError("No weights")):
            result = run_inference(p)
        assert result["status"] == "error"
        assert result["error_type"] == "model_not_available"
        assert "No weights" in result["error"]

    def test_inference_runtime_error_returns_error(self, tmp_path):
        """If detector.predict() raises RuntimeError, return an error dict."""
        p = make_jpeg(tmp_path)
        mock_det = MagicMock()
        mock_det.model_id = "dima806/ai_vs_real_image_detection"
        mock_det.predict.side_effect = RuntimeError("GPU OOM")
        with patch("src.inference._get_detector", return_value=mock_det):
            result = run_inference(p)
        assert result["status"] == "error"
        assert result["error_type"] == "inference_error"

    def test_error_dict_always_has_file_name(self, tmp_path):
        """Even on error, file_name should be present if derivable."""
        result = run_inference(tmp_path / "missing.png")
        assert result.get("file_name") == "missing.png"

    def test_never_raises_for_missing_file(self, tmp_path):
        """run_inference must not raise Python exceptions for bad inputs."""
        try:
            run_inference(tmp_path / "does_not_exist.jpg")
        except Exception as exc:
            pytest.fail(f"run_inference raised an exception: {exc}")

    def test_never_raises_for_unsupported_type(self, tmp_path):
        p = make_unsupported(tmp_path)
        try:
            run_inference(p)
        except Exception as exc:
            pytest.fail(f"run_inference raised an exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests (require real model weights ~330 MB)
# ─────────────────────────────────────────────────────────────────────────────

class TestInferenceIntegration:

    @pytest.mark.integration
    def test_full_pipeline_on_jpeg(self, tmp_path):
        """
        End-to-end test: loads a real JPEG → runs actual model → checks result.
        Requires model weights (downloaded automatically on first run).
        """
        p = make_jpeg(tmp_path)
        result = run_inference(p)

        assert result["status"] == "success"
        assert result["label"] in ("REAL", "AI_GENERATED")
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["inference_ms"] > 0
        assert result["image_info"]["width"] == 64

    @pytest.mark.integration
    def test_full_pipeline_on_png(self, tmp_path):
        p = make_png(tmp_path)
        result = run_inference(p)
        assert result["status"] == "success"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Model Selection & Smaug verification
# ─────────────────────────────────────────────────────────────────────────────

class TestModelSelection:
    """Verifies that model selection works and never silently falls back."""

    def test_cli_argument_parsing(self):
        from src.inference import parse_args
        args_current = parse_args(["dummy.jpg", "--model", "current"])
        assert args_current.model == "current"

        args_smaug = parse_args(["dummy.jpg", "--model", "smaug"])
        assert args_smaug.model == "smaug"

        args_default = parse_args(["dummy.jpg"])
        assert args_default.model == "current"

    def test_smaug_selects_abacusai_model_id(self):
        from src.detector import resolve_model_info, SMAUG_MODEL_ID
        info = resolve_model_info("smaug")
        assert info["model_id"] == SMAUG_MODEL_ID
        assert info["model_id"] == "abacusai/Smaug-AI-Image-Detector"

    def test_current_selects_dima806_model_id(self):
        from src.detector import resolve_model_info, MODEL_ID
        info = resolve_model_info("current")
        assert info["model_id"] == MODEL_ID
        assert info["model_id"] == "dima806/ai_vs_real_image_detection"

    def test_invalid_model_selection_returns_error(self, tmp_path):
        p = make_jpeg(tmp_path)
        result = run_inference(p, model="non_existent_model_xyz")
        assert result["status"] == "error"
        assert result["error_type"] == "invalid_model_selection"

    def test_smaug_failure_never_silently_falls_back_to_current(self, tmp_path):
        """If Smaug fails to load, run_inference must report Smaug error, not fall back."""
        p = make_jpeg(tmp_path)
        with patch("src.inference._get_detector",
                   side_effect=ModelNotAvailableError("Smaug weights unavailable")):
            result = run_inference(p, model="smaug")

        assert result["status"] == "error"
        assert result["error_type"] == "model_not_available"
        assert result["model_id"] == "abacusai/Smaug-AI-Image-Detector"
        assert "Smaug weights unavailable" in result["error"]

    def test_model_mismatch_is_strictly_caught(self, tmp_path):
        """If _get_detector accidentally returns the current model for Smaug, reject it."""
        p = make_jpeg(tmp_path)
        mock_accidental_current_detector = MagicMock()
        mock_accidental_current_detector.model_id = "dima806/ai_vs_real_image_detection"

        with patch("src.inference._get_detector", return_value=mock_accidental_current_detector):
            result = run_inference(p, model="smaug")

        assert result["status"] == "error"
        assert result["error_type"] == "model_mismatch_error"
        assert "Silent fallback is prohibited" in result["error"]

    def test_smaug_successful_inference(self, tmp_path):
        """When Smaug detector is loaded and runs, result reflects Smaug model ID."""
        p = make_jpeg(tmp_path)
        mock_smaug_detector = MagicMock()
        mock_smaug_detector.model_id = "abacusai/Smaug-AI-Image-Detector"
        mock_smaug_detector.predict.return_value = {
            "label": "AI_GENERATED",
            "confidence": 0.88,
            "raw_scores": [
                {"label": "REAL", "score": 0.12},
                {"label": "AI_GENERATED", "score": 0.88},
            ],
            "model_id": "abacusai/Smaug-AI-Image-Detector",
            "inference_ms": 45.0,
        }

        with patch("src.inference._get_detector", return_value=mock_smaug_detector):
            result = run_inference(p, model="smaug")

        assert result["status"] == "success"
        assert result["model_id"] == "abacusai/Smaug-AI-Image-Detector"
        assert result["label"] == "AI_GENERATED"
        assert result["confidence"] == 0.88

