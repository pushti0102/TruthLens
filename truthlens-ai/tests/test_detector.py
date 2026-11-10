"""
tests/test_detector.py
======================
Tests for the TruthLensDetector class (src/detector.py).

IMPORTANT
---------
Some tests in this file require the model weights to be downloaded from
Hugging Face (~330 MB on first run).  Those tests are marked with:

    @pytest.mark.integration

By default, the integration tests are SKIPPED unless you pass --integration:

    pytest tests/test_detector.py -v                        # skips integration
    pytest tests/test_detector.py -v --integration          # runs everything

The non-integration tests mock the transformers pipeline so they run
instantly without any network access.

Run just the fast tests:
    pytest tests/test_detector.py -v -m "not integration"
"""

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from src.detector import (
    TruthLensDetector,
    ModelNotAvailableError,
    MODEL_ID,
    SMAUG_MODEL_ID,
    MODEL_REGISTRY,
    resolve_model_info,
    LABEL_MAP,
)



# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_dummy_image(width: int = 64, height: int = 64) -> Image.Image:
    """Return a small solid-colour RGB PIL image."""
    return Image.new("RGB", (width, height), color=(120, 80, 200))


def make_mock_pipeline(label: str = "REAL", score: float = 0.95):
    """
    Return a mock that behaves like a HuggingFace image-classification pipeline.
    """
    mock_pipe = MagicMock()
    mock_pipe.return_value = [
        {"label": label, "score": score},
        {"label": "FAKE" if label == "REAL" else "REAL", "score": 1.0 - score},
    ]
    return mock_pipe


# ─────────────────────────────────────────────────────────────────────────────
# Tests: LABEL_MAP and normalisation
# ─────────────────────────────────────────────────────────────────────────────

class TestLabelMap:

    def test_label_map_contains_real(self):
        assert "real" in LABEL_MAP
        assert LABEL_MAP["real"] == "REAL"

    def test_label_map_contains_fake(self):
        assert "fake" in LABEL_MAP
        assert LABEL_MAP["fake"] == "AI_GENERATED"

    def test_label_map_has_variants(self):
        assert "ai generated" in LABEL_MAP or "ai_generated" in LABEL_MAP


# ─────────────────────────────────────────────────────────────────────────────
# Tests: ModelNotAvailableError when transformers is absent
# ─────────────────────────────────────────────────────────────────────────────

class TestModelNotAvailableError:

    def test_raises_when_transformers_not_available(self):
        """If transformers is not importable, the constructor must raise."""
        with patch("src.detector._TRANSFORMERS_AVAILABLE", False):
            with pytest.raises(ModelNotAvailableError, match="transformers"):
                TruthLensDetector()

    def test_raises_on_os_error_during_load(self):
        """If the pipeline() call raises OSError, wrap it in ModelNotAvailableError."""
        with patch("src.detector.pipeline", side_effect=OSError("Connection refused")):
            with pytest.raises(ModelNotAvailableError, match="Could not load model"):
                TruthLensDetector()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: TruthLensDetector.predict (mocked pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictMocked:

    @pytest.fixture
    def detector_real(self):
        """A TruthLensDetector whose pipeline is replaced with a mock returning REAL."""
        with patch("src.detector.pipeline", return_value=make_mock_pipeline("REAL", 0.92)):
            d = TruthLensDetector()
        return d

    @pytest.fixture
    def detector_fake(self):
        """A TruthLensDetector whose pipeline is replaced with a mock returning FAKE."""
        with patch("src.detector.pipeline", return_value=make_mock_pipeline("FAKE", 0.88)):
            d = TruthLensDetector()
        return d

    def test_predict_returns_dict(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert isinstance(result, dict)

    def test_predict_has_required_keys(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        for key in ("label", "confidence", "raw_scores", "model_id", "inference_ms"):
            assert key in result, f"Missing key: {key}"

    def test_label_is_canonical(self, detector_real):
        """The label must be one of our two canonical strings."""
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert result["label"] in ("REAL", "AI_GENERATED")

    def test_confidence_in_range(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_model_id_matches(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert result["model_id"] == MODEL_ID

    def test_inference_ms_positive(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert result["inference_ms"] >= 0.0

    def test_fake_image_returns_ai_generated(self, detector_fake):
        img = make_dummy_image()
        result = detector_fake.predict(img)
        assert result["label"] == "AI_GENERATED"

    def test_real_image_returns_real(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert result["label"] == "REAL"

    def test_raw_scores_is_list(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        assert isinstance(result["raw_scores"], list)
        assert len(result["raw_scores"]) > 0

    def test_raw_scores_sum_approximately_one(self, detector_real):
        img = make_dummy_image()
        result = detector_real.predict(img)
        total = sum(s["score"] for s in result["raw_scores"])
        assert abs(total - 1.0) < 0.05, f"Scores sum to {total}, expected ~1.0"

    def test_is_ready_true_after_init(self, detector_real):
        assert detector_real.is_ready is True

    def test_inference_error_propagates_as_runtime_error(self):
        """If the pipeline itself raises, predict() should raise RuntimeError."""
        with patch("src.detector.pipeline") as mock_pipe_factory:
            mock_pipe = MagicMock()
            mock_pipe.side_effect = Exception("GPU exploded")
            mock_pipe_factory.return_value = mock_pipe
            d = TruthLensDetector()

        with pytest.raises(RuntimeError, match="Inference failed"):
            d.predict(make_dummy_image())


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests (require real model weights)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegration:

    @pytest.mark.integration
    def test_detector_loads_real_model(self):
        """
        The TruthLensDetector should load from Hugging Face without error.
        REQUIRES: internet access on first run to download ~330 MB of weights.
        """
        detector = TruthLensDetector()
        assert detector.is_ready

    @pytest.mark.integration
    def test_real_inference_on_synthetic_image(self):
        """
        Running inference on a plain solid-colour image should return a valid
        result dict.  The label is whatever the model decides — we only check
        the structure here, not the correctness.
        """
        detector = TruthLensDetector()
        img = make_dummy_image(width=224, height=224)
        result = detector.predict(img)

        assert result["label"] in ("REAL", "AI_GENERATED")
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["model_id"] == MODEL_ID
        assert result["inference_ms"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Model Registry and Smaug Loading
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryAndSmaug:
    """Tests for model resolution and Smaug detector handling."""

    def test_registry_contains_current_and_smaug(self):
        assert "current" in MODEL_REGISTRY
        assert "smaug" in MODEL_REGISTRY
        assert MODEL_REGISTRY["current"]["model_id"] == MODEL_ID
        assert MODEL_REGISTRY["smaug"]["model_id"] == SMAUG_MODEL_ID

    def test_resolve_model_info_keys(self):
        cur_info = resolve_model_info("current")
        assert cur_info["model_id"] == "dima806/ai_vs_real_image_detection"
        assert cur_info["architecture"] == "vit"

        smaug_info = resolve_model_info("smaug")
        assert smaug_info["model_id"] == "abacusai/Smaug-AI-Image-Detector"
        assert smaug_info["architecture"] == "smaug"

    def test_resolve_model_info_by_full_id(self):
        smaug_info = resolve_model_info("abacusai/Smaug-AI-Image-Detector")
        assert smaug_info["key"] == "smaug"
        assert smaug_info["architecture"] == "smaug"

    def test_resolve_model_info_invalid(self):
        with pytest.raises(ValueError, match="Unknown model identifier"):
            resolve_model_info("invalid_model_abc")

    def test_smaug_detector_init_mocked(self):
        """When pipeline is mocked, TruthLensDetector with Smaug sets correct ID."""
        with patch("src.detector.pipeline", return_value=make_mock_pipeline("AI_GENERATED", 0.91)):
            detector = TruthLensDetector(model_id="smaug")
            assert detector.model_id == "abacusai/Smaug-AI-Image-Detector"
            assert detector.architecture == "smaug"
            res = detector.predict(make_dummy_image())
            assert res["model_id"] == "abacusai/Smaug-AI-Image-Detector"
            assert res["label"] == "AI_GENERATED"

    def test_smaug_never_falls_back_to_vit_on_failure(self):
        """When Smaug fails to load, it must raise ModelNotAvailableError and not use ViT."""
        with patch("src.detector.pipeline", None):
            with pytest.raises(ModelNotAvailableError) as exc_info:
                # Force unmocked load of Smaug
                TruthLensDetector(model_id="smaug")
            # The error must specifically describe Smaug failure
            assert "Smaug model 'abacusai/Smaug-AI-Image-Detector'" in str(exc_info.value)

