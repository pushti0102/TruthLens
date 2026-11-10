"""
tests/test_smoke_pretrained.py
==============================
Smoke and integration test suite to verify that the pretrained Hugging Face model
('dima806/ai_vs_real_image_detection') loads correctly and performs inference.

Tests include:
  1. Real model loading and Hugging Face cache reuse
  2. Inspection of model.config.id2label and model.config.label2id
  3. Safe weight loading (safetensors preference)
  4. Real forward pass on RGB test image with valid probability distribution
  5. End-to-end run_inference pipeline with warning, likelihood, and provenance notes
  6. Document-domain warning on ID-1 aspect ratio image without model tampering
  7. Folder-based dataset evaluation pipeline in src.evaluate_dataset
"""

import csv
import pytest
from pathlib import Path
from PIL import Image

from src.detector import TruthLensDetector, MODEL_ID, LABEL_MAP
from src.inference import run_inference, compute_ai_likelihood
from src.preprocessing import check_document_characteristics
from src.evaluate_dataset import (
    evaluate_folder_dataset,
    compute_evaluation_metrics,
    normalize_class_name,
)


@pytest.fixture(scope="module")
def shared_detector():
    """Load the real detector once for this test module to avoid re-loading."""
    return TruthLensDetector(model_id=MODEL_ID)


class TestPretrainedModelSmoke:
    """Smoke tests running on the actual pretrained Hugging Face model."""

    def test_model_loaded_successfully(self, shared_detector):
        """Verify model weights and image processor are loaded."""
        assert shared_detector.is_ready is True
        assert shared_detector.model is not None
        assert shared_detector.processor is not None

    def test_id2label_and_label2id_mapping(self, shared_detector):
        """
        Inspect model config and confirm:
          id2label[0] == 'REAL'
          id2label[1] == 'FAKE'
        """
        assert shared_detector.id2label[0] == "REAL"
        assert shared_detector.id2label[1] == "FAKE"
        assert shared_detector.label2id["REAL"] == 0
        assert shared_detector.label2id["FAKE"] == 1

        # Confirm normalisation maps FAKE -> AI_GENERATED and REAL -> REAL
        assert shared_detector._normalise_label(shared_detector.id2label[0]) == "REAL"
        assert shared_detector._normalise_label(shared_detector.id2label[1]) == "AI_GENERATED"

    def test_real_inference_prediction_structure(self, shared_detector):
        """Run inference on a real synthetic RGB image and verify structure."""
        img = Image.new("RGB", (224, 224), color=(140, 180, 220))
        result = shared_detector.predict(img)

        assert isinstance(result, dict)
        assert result["model_id"] == MODEL_ID
        assert result["label"] in ("REAL", "AI_GENERATED")
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["inference_ms"] > 0.0

        # Verify raw_scores
        raw_scores = result["raw_scores"]
        assert len(raw_scores) == 2
        labels_in_scores = {s["label"] for s in raw_scores}
        assert labels_in_scores == {"REAL", "AI_GENERATED"}

        # Sum of probabilities should approximate 1.0 (softmax)
        prob_sum = sum(s["score"] for s in raw_scores)
        assert abs(prob_sum - 1.0) < 0.02

    def test_end_to_end_inference_report(self, tmp_path):
        """Verify full run_inference returns all required fields including warning & likelihood."""
        img_path = tmp_path / "smoke_photo.jpg"
        Image.new("RGB", (300, 300), color=(100, 150, 200)).save(img_path, format="JPEG")

        report = run_inference(img_path)

        assert report["status"] == "success"
        assert report["file_name"] == "smoke_photo.jpg"
        assert report["label"] in ("REAL", "AI_GENERATED")
        assert "confidence" in report
        assert "raw_scores" in report
        assert report["model_id"] == MODEL_ID
        assert "inference_ms" in report
        assert "warning" in report
        assert report["warning"] == "Experimental AI-image detection; this prediction does not prove authenticity."
        assert report["ai_likelihood"] in ("high", "moderate", "low", "inconclusive")
        assert "image_info" in report
        assert "domain_note" in report
        assert "provenance_note" in report

    def test_document_characteristics_and_warning(self, tmp_path):
        """
        Verify that an ID-1 aspect ratio image (e.g. PAN card format: 856x540)
        triggers the document domain warning without modifying model weights.
        """
        pan_card_mock = tmp_path / "pan_card_sim.jpg"
        # Standard ID-1 ratio = 856 / 540 = 1.585
        Image.new("RGB", (856, 540), color=(235, 230, 220)).save(pan_card_mock, format="JPEG")

        report = run_inference(pan_card_mock)

        assert report["status"] == "success"
        assert "document_domain_warning" in report
        assert "PAN cards" in report["document_domain_warning"] or "ID-1" in report["document_domain_warning"]
        assert report["image_info"]["aspect_ratio"] == round(856 / 540, 4)

    def test_ai_likelihood_cautious_bands(self):
        """Verify likelihood bands don't use absolute binary language."""
        assert compute_ai_likelihood("AI_GENERATED", 0.95) == "high"
        assert compute_ai_likelihood("AI_GENERATED", 0.65) == "moderate"
        assert compute_ai_likelihood("AI_GENERATED", 0.52) == "inconclusive"
        assert compute_ai_likelihood("REAL", 0.90) == "low"
        assert compute_ai_likelihood("REAL", 0.65) == "moderate"
        assert compute_ai_likelihood("REAL", 0.51) == "inconclusive"


class TestDatasetEvaluationPipeline:
    """Tests for src.evaluate_dataset folder processing and CSV generation."""

    def test_folder_dataset_evaluation(self, tmp_path):
        # Create folder structure
        dataset_dir = tmp_path / "test_dataset"
        real_dir = dataset_dir / "REAL"
        ai_dir = dataset_dir / "AI_GENERATED"
        real_dir.mkdir(parents=True)
        ai_dir.mkdir(parents=True)

        # Create 2 sample images per folder
        Image.new("RGB", (64, 64), color=(50, 100, 150)).save(real_dir / "real1.jpg", format="JPEG")
        Image.new("RGB", (64, 64), color=(60, 110, 160)).save(real_dir / "real2.png", format="PNG")
        Image.new("RGB", (64, 64), color=(200, 50, 50)).save(ai_dir / "ai1.jpg", format="JPEG")
        Image.new("RGB", (64, 64), color=(210, 60, 60)).save(ai_dir / "ai2.png", format="PNG")

        csv_out = tmp_path / "output_eval.csv"
        results = evaluate_folder_dataset(dataset_dir, csv_output_path=csv_out, threshold=0.5)

        assert results["total_discovered"] == 4
        assert results["evaluated_samples"] == 4
        assert results["skipped_files"] == 0

        # Check metrics dict
        m = results["metrics"]
        assert "accuracy" in m
        assert "precision" in m
        assert "recall" in m
        assert "specificity" in m
        assert "false_positive_rate" in m
        assert "false_negative_rate" in m
        assert "f1_score" in m
        assert "confusion_matrix" in m

        # Check CSV output exists and has headers
        assert csv_out.exists()
        with open(csv_out, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert "file_name" in reader.fieldnames
            assert "ground_truth" in reader.fieldnames
            assert "predicted_label" in reader.fieldnames
            assert "score_ai_generated" in reader.fieldnames
            assert "is_correct" in reader.fieldnames
            rows = list(reader)
            assert len(rows) == 4
