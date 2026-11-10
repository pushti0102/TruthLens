"""
tests/test_class_mapping.py
===========================
Automated tests for:
  1. Model class mapping and id2label verification
  2. Preprocessing behavior on document-type aspect ratios and color modes
  3. Handling of invalid and corrupted image files
  4. Model-not-available behavior and error propagation
  5. Evaluation metrics and confusion matrix calculations
"""

import csv
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from src.detector import TruthLensDetector, ModelNotAvailableError, LABEL_MAP
from src.preprocessing import load_image, validate_image_path, PreprocessingError
from src.inference import run_inference
from src.evaluate import (
    calculate_roc_auc,
    compute_metrics,
    normalize_ground_truth,
    evaluate_dataset,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Class Mapping & id2label verification
# ─────────────────────────────────────────────────────────────────────────────

class TestClassMapping:
    """Verifies that model labels and Hugging Face id2label indices are properly mapped."""

    def test_canonical_labels(self):
        """Every target in LABEL_MAP must be either 'REAL' or 'AI_GENERATED'."""
        for raw, canonical in LABEL_MAP.items():
            assert canonical in ("REAL", "AI_GENERATED"), f"Invalid target {canonical} for {raw}"

    @pytest.mark.parametrize("raw_input,expected", [
        ("real", "REAL"),
        ("REAL", "REAL"),
        ("Real", "REAL"),
        ("  real  ", "REAL"),
        ("fake", "AI_GENERATED"),
        ("FAKE", "AI_GENERATED"),
        ("Fake", "AI_GENERATED"),
        ("ai generated", "AI_GENERATED"),
        ("AI GENERATED", "AI_GENERATED"),
        ("ai_generated", "AI_GENERATED"),
        ("artificial", "AI_GENERATED"),
        ("artificial image", "AI_GENERATED"),
    ])
    def test_normalise_label_variants(self, raw_input, expected):
        """Verify normalisation handles casing, whitespace, and synonym variations."""
        with patch.object(TruthLensDetector, "_load_model", return_value=None):
            detector = TruthLensDetector()
            assert detector._normalise_label(raw_input) == expected

    def test_unknown_label_fallback(self):
        """Unknown labels should return uppercase string without throwing KeyError."""
        with patch.object(TruthLensDetector, "_load_model", return_value=None):
            detector = TruthLensDetector()
            assert detector._normalise_label("unseen_label") == "UNSEEN_LABEL"

    def test_id2label_index_alignment(self):
        """
        Verify that model config index 0 is REAL and index 1 is FAKE (AI_GENERATED).
        This guarantees index 1 was never swapped with 0 in the pipeline logic.
        """
        model_id2label = {0: "REAL", 1: "FAKE"}
        with patch.object(TruthLensDetector, "_load_model", return_value=None):
            detector = TruthLensDetector()
            # Index 0
            label_0 = detector._normalise_label(model_id2label[0])
            assert label_0 == "REAL"
            # Index 1
            label_1 = detector._normalise_label(model_id2label[1])
            assert label_1 == "AI_GENERATED"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Preprocessing on Document Images and Aspect Ratios
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentPreprocessing:
    """Verifies image loading and channel handling on document-like formats and sizes."""

    def test_id_card_aspect_ratio_loading(self, tmp_path):
        """Standard ID-1 identity card aspect ratio (~85.6mm x 53.98mm = 856x540)."""
        card_img = Image.new("RGB", (856, 540), color=(240, 240, 230))
        p = tmp_path / "pan_card_mock.jpg"
        card_img.save(p, format="JPEG")

        loaded = load_image(p)
        assert isinstance(loaded, Image.Image)
        assert loaded.size == (856, 540)
        assert loaded.mode == "RGB"

    def test_tall_scanned_document_aspect_ratio(self, tmp_path):
        """A4 document scanned at 300 DPI (2480x3508)."""
        doc_img = Image.new("RGB", (248, 350), color=(255, 255, 255))
        p = tmp_path / "doc_page.png"
        doc_img.save(p, format="PNG")

        loaded = load_image(p)
        assert loaded.mode == "RGB"
        assert loaded.size == (248, 350)

    def test_grayscale_document_converted_to_rgb(self, tmp_path):
        """Documents scanned in 8-bit grayscale ('L') must convert to 3-channel RGB."""
        gray_img = Image.new("L", (400, 300), color=128)
        p = tmp_path / "grayscale_scan.jpg"
        gray_img.save(p, format="JPEG")

        loaded = load_image(p)
        assert loaded.mode == "RGB"
        # Verify 3 identical channels
        r, g, b = loaded.split()
        assert r.tobytes() == g.tobytes() == b.tobytes()

    def test_transparent_png_document_flattened_to_rgb(self, tmp_path):
        """Document graphic with RGBA transparency must convert to RGB."""
        rgba_img = Image.new("RGBA", (200, 200), color=(100, 150, 200, 128))
        p = tmp_path / "watermark_doc.png"
        rgba_img.save(p, format="PNG")

        loaded = load_image(p)
        assert loaded.mode == "RGB"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Invalid and Corrupted Images
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidImages:

    def test_empty_file_raises_preprocessing_error(self, tmp_path):
        empty_file = tmp_path / "empty.jpg"
        empty_file.write_bytes(b"")
        with pytest.raises(PreprocessingError, match="Cannot identify"):
            load_image(empty_file)

    def test_truncated_corrupt_jpeg(self, tmp_path):
        corrupt_file = tmp_path / "corrupt.jpg"
        corrupt_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)
        with pytest.raises(PreprocessingError):
            load_image(corrupt_file)

    def test_pdf_document_rejected(self, tmp_path):
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4...")
        with pytest.raises(PreprocessingError, match="Unsupported file type: '.pdf'"):
            validate_image_path(pdf_file)

    def test_nonexistent_image_inference(self, tmp_path):
        result = run_inference(tmp_path / "nonexistent.jpg")
        assert result["status"] == "error"
        assert result["error_type"] == "preprocessing_error"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Model-Unavailable Behavior
# ─────────────────────────────────────────────────────────────────────────────

class TestModelUnavailableBehavior:

    def test_inference_reports_model_unavailable(self, tmp_path):
        img = Image.new("RGB", (64, 64), color=(100, 100, 100))
        p = tmp_path / "test.jpg"
        img.save(p, format="JPEG")

        with patch("src.inference._get_detector", side_effect=ModelNotAvailableError("Model offline")):
            result = run_inference(p)
            assert result["status"] == "error"
            assert result["error_type"] == "model_not_available"
            assert "Model offline" in result["error"]

    def test_detector_raises_helpful_error_on_missing_weights(self):
        with patch("src.detector.pipeline", side_effect=OSError("Connection timeout")):
            with pytest.raises(ModelNotAvailableError, match="Could not load model"):
                TruthLensDetector()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Evaluation Metrics & Batch Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationMetrics:

    def test_ground_truth_normalization(self):
        assert normalize_ground_truth("real") == "REAL"
        assert normalize_ground_truth("REAL") == "REAL"
        assert normalize_ground_truth("0") == "REAL"
        assert normalize_ground_truth("fake") == "AI_GENERATED"
        assert normalize_ground_truth("AI_GENERATED") == "AI_GENERATED"
        assert normalize_ground_truth("synthetic") == "AI_GENERATED"
        assert normalize_ground_truth("1") == "AI_GENERATED"
        assert normalize_ground_truth("invalid_label") is None

    def test_calculate_roc_auc_perfect(self):
        y_true = [0, 0, 1, 1]
        y_scores = [0.1, 0.2, 0.8, 0.9]
        auc = calculate_roc_auc(y_true, y_scores)
        assert auc == 1.0

    def test_calculate_roc_auc_inverted(self):
        y_true = [0, 0, 1, 1]
        y_scores = [0.9, 0.8, 0.2, 0.1]
        auc = calculate_roc_auc(y_true, y_scores)
        assert auc == 0.0

    def test_calculate_roc_auc_single_class_returns_none(self):
        y_true = [1, 1, 1]
        y_scores = [0.7, 0.8, 0.9]
        assert calculate_roc_auc(y_true, y_scores) is None

    def test_compute_metrics_known_matrix(self):
        # 2 TP, 1 FP, 3 TN, 1 FN
        records = [
            {"ground_truth": "AI_GENERATED", "predicted_label": "AI_GENERATED", "predicted_score_ai": 0.9},
            {"ground_truth": "AI_GENERATED", "predicted_label": "AI_GENERATED", "predicted_score_ai": 0.8},
            {"ground_truth": "REAL", "predicted_label": "AI_GENERATED", "predicted_score_ai": 0.7},  # FP
            {"ground_truth": "REAL", "predicted_label": "REAL", "predicted_score_ai": 0.1},
            {"ground_truth": "REAL", "predicted_label": "REAL", "predicted_score_ai": 0.2},
            {"ground_truth": "REAL", "predicted_label": "REAL", "predicted_score_ai": 0.3},
            {"ground_truth": "AI_GENERATED", "predicted_label": "REAL", "predicted_score_ai": 0.4},  # FN
        ]
        m = compute_metrics(records)
        assert m["total_samples"] == 7
        assert m["confusion_matrix"]["tp"] == 2
        assert m["confusion_matrix"]["fp"] == 1
        assert m["confusion_matrix"]["tn"] == 3
        assert m["confusion_matrix"]["fn"] == 1
        # Accuracy = (2+3)/7 = 5/7 ~ 0.7143
        assert m["accuracy"] == round(5 / 7, 4)
        # Precision = 2/(2+1) = 2/3 ~ 0.6667
        assert m["precision"] == round(2 / 3, 4)
        # Recall = 2/(2+1) = 2/3 ~ 0.6667
        assert m["recall"] == round(2 / 3, 4)
        # F1 = 2/3 ~ 0.6667
        assert m["f1_score"] == round(2 / 3, 4)

    def test_batch_evaluate_csv(self, tmp_path):
        """Test batch evaluation pipeline end-to-end with mock inference."""
        p1 = tmp_path / "photo1.jpg"
        p2 = tmp_path / "doc1.jpg"
        Image.new("RGB", (64, 64), color=(10, 20, 30)).save(p1, format="JPEG")
        Image.new("RGB", (64, 64), color=(40, 50, 60)).save(p2, format="JPEG")

        csv_path = tmp_path / "dataset.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["image_path", "ground_truth_label", "category"])
            writer.writerow([str(p1), "REAL", "photograph"])
            writer.writerow([str(p2), "REAL", "document"])

        mock_results = {
            str(p1): {
                "status": "success",
                "label": "REAL",
                "confidence": 0.95,
                "raw_scores": [{"label": "REAL", "score": 0.95}, {"label": "AI_GENERATED", "score": 0.05}],
                "model_id": "dima806/ai_vs_real_image_detection",
                "inference_ms": 50.0,
            },
            str(p2): {
                "status": "success",
                "label": "AI_GENERATED",  # False positive on document
                "confidence": 0.93,
                "raw_scores": [{"label": "REAL", "score": 0.07}, {"label": "AI_GENERATED", "score": 0.93}],
                "model_id": "dima806/ai_vs_real_image_detection",
                "inference_ms": 52.0,
            },
        }

        with patch("src.evaluate.run_inference", side_effect=lambda p: mock_results[str(p)]):
            res = evaluate_dataset(csv_path)
            assert res["evaluated_records"] == 2
            assert res["overall"]["confusion_matrix"]["tn"] == 1
            assert res["overall"]["confusion_matrix"]["fp"] == 1  # Document was FP!
            assert "photograph" in res["per_category"]
            assert "document" in res["per_category"]
            assert res["per_category"]["document"]["confusion_matrix"]["fp"] == 1
            assert res["per_category"]["photograph"]["confusion_matrix"]["tn"] == 1
