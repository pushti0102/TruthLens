"""
scripts/benchmark_models.py
===========================
Systematic evaluation of TruthLens AI models:
- 'current': dima806/ai_vs_real_image_detection (ViT-Base-224 fine-tuned on CIFAKE)
- 'smaug': abacusai/Smaug-AI-Image-Detector (EmbeddingGemma-2 multi-crop forensics)

Evaluates both models on the EXACT same labeled dataset without fabricating
predictions or adjusting thresholds.
Separates photographic imagery from document scans as required.
"""

import os
import sys
import json
import time
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_DIR = PROJECT_ROOT / "truthlens-ai"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from src.inference import run_inference
from src.detector import resolve_model_info
from PIL import Image, ImageDraw


def generate_test_document(output_path: Path) -> Path:
    """Generate a realistic test ID card format document if one doesn't exist."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (856, 540), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)
    # Header bar
    draw.rectangle([20, 20, 836, 90], fill=(24, 76, 120))
    # Photo box
    draw.rectangle([40, 120, 240, 360], fill=(210, 210, 210), outline=(120, 120, 120), width=2)
    # Signature line
    draw.rectangle([40, 390, 240, 470], fill=(255, 255, 255), outline=(150, 150, 150), width=1)
    # Text lines
    for y in [130, 170, 210, 250, 290, 330]:
        draw.rectangle([270, y, 780, y + 16], fill=(70, 70, 70))
    img.save(output_path, "JPEG", quality=95)
    return output_path


def get_dataset():
    """Build the evaluation dataset containing photographic images and separate documents."""
    cifake_dir = PROJECT_ROOT / "data" / "cifake_dataset" / "FAKE"
    if not cifake_dir.exists():
        cifake_dir = PROJECT_ROOT / "test" / "FAKE"

    demo_dir = PROJECT_ROOT / "demo_samples"
    sample_real = AI_DIR / "data" / "real" / "sample_photo.jpg"
    sample_synth = AI_DIR / "data" / "ai_generated" / "sample_synth.jpg"

    # 1. Real photographic images (known natural camera & smartphone photos)
    real_photos = [
        demo_dir / "real_dog_photo.jpg",
        demo_dir / "original_demo.png",
        sample_real,
    ]
    # Filter to only existing files
    existing_real = [p for p in real_photos if p.exists()]

    # 2. Synthetic AI images (known AI generated)
    synth_images = [
        demo_dir / "ai_generated_anime.png",
        sample_synth,
    ]
    if cifake_dir.exists():
        synth_images.extend(list(cifake_dir.glob("*.jpg"))[:5])

    existing_synth = [p for p in synth_images if p.exists()]

    photo_dataset = []
    for p in existing_real:
        photo_dataset.append({"path": p, "ground_truth": "REAL", "type": "smartphone_photo"})
    for p in existing_synth:
        photo_dataset.append({"path": p, "ground_truth": "AI_GENERATED", "type": "synthetic_ai"})

    # 3. Document images (separate evaluation category)
    doc_path = PROJECT_ROOT / "data" / "test_document_id.jpg"
    if not doc_path.exists():
        generate_test_document(doc_path)

    doc_dataset = [
        {"path": doc_path, "ground_truth": "REAL", "type": "id_card_document"},
    ]

    return photo_dataset, doc_dataset


def evaluate_model(model_key: str, dataset: list):
    """Run model on dataset and collect predictions without altering outputs."""
    model_info = resolve_model_info(model_key)
    print(f"\n=======================================================")
    print(f"Evaluating Model: {model_info['name']} ({model_info['model_id']})")
    print(f"=======================================================")

    results = []
    tp = fp = tn = fn = 0

    for item in dataset:
        path = item["path"]
        gt = item["ground_truth"]
        t0 = time.perf_counter()
        res = run_inference(path, model=model_key)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        pred_label = res.get("label")
        conf = res.get("confidence", 0.0)
        doc_warn = bool(res.get("document_domain_warning"))

        # Scoring: Positive = AI_GENERATED, Negative = REAL
        is_tp = (gt == "AI_GENERATED" and pred_label == "AI_GENERATED")
        is_fp = (gt == "REAL" and pred_label == "AI_GENERATED")
        is_tn = (gt == "REAL" and pred_label == "REAL")
        is_fn = (gt == "AI_GENERATED" and pred_label == "REAL")

        if is_tp: tp += 1
        if is_fp: fp += 1
        if is_tn: tn += 1
        if is_fn: fn += 1

        status_marker = "CORRECT" if (is_tp or is_tn) else "MISCLASSIFIED"
        print(f"  [{status_marker}] File: {path.name:<25} | GT: {gt:<12} | Pred: {pred_label:<12} | Conf: {conf*100:5.1f}% | Time: {elapsed_ms:6.1f}ms")

        results.append({
            "filename": path.name,
            "path": str(path),
            "ground_truth": gt,
            "prediction": pred_label,
            "confidence": conf,
            "document_domain_warning": doc_warn,
            "inference_ms": round(elapsed_ms, 1),
            "correct": is_tp or is_tn,
        })

    total = len(dataset)
    acc = (tp + tn) / total if total > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    metrics = {
        "model_key": model_key,
        "model_id": model_info["model_id"],
        "architecture": model_info["architecture"],
        "total_samples": total,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "results": results,
    }
    return metrics


def main():
    print("TruthLens AI - Systematic Pretrained Model Benchmark")
    print("Comparing 'current' (dima806 ViT) vs 'smaug' (Abacus.AI Smaug)")

    photo_dataset, doc_dataset = get_dataset()
    print(f"\nPhotographic Dataset: {len(photo_dataset)} samples")
    print(f"Document Dataset    : {len(doc_dataset)} samples (Evaluated separately)")

    # 1. Benchmark on photographic images
    print("\n" + "#" * 60)
    print("PHASE 1: PHOTOGRAPHIC DATASET BENCHMARK")
    print("#" * 60)
    metrics_current = evaluate_model("current", photo_dataset)
    metrics_smaug = evaluate_model("smaug", photo_dataset)

    # 2. Benchmark on document category
    print("\n" + "#" * 60)
    print("PHASE 2: DOCUMENT CATEGORY EVALUATION (SEPARATE CATEGORY)")
    print("#" * 60)
    doc_current = evaluate_model("current", doc_dataset)
    doc_smaug = evaluate_model("smaug", doc_dataset)

    # Summary table
    print("\n" + "=" * 80)
    print("FINAL BENCHMARK COMPARISON SUMMARY (PHOTOGRAPHIC DATASET)")
    print("=" * 80)
    header = f"{'Metric':<24} | {'Current (dima806 ViT)':<24} | {'Smaug (EmbeddingGemma)':<24}"
    print(header)
    print("-" * 80)
    print(f"{'Model ID':<24} | {metrics_current['model_id'][:24]:<24} | {metrics_smaug['model_id'][:24]:<24}")
    print(f"{'Samples Evaluated':<24} | {metrics_current['total_samples']:<24} | {metrics_smaug['total_samples']:<24}")
    print(f"{'Accuracy':<24} | {metrics_current['accuracy']*100:6.2f}%{'':<17} | {metrics_smaug['accuracy']*100:6.2f}%{'':<17}")
    print(f"{'Precision':<24} | {metrics_current['precision']*100:6.2f}%{'':<17} | {metrics_smaug['precision']*100:6.2f}%{'':<17}")
    print(f"{'Recall':<24} | {metrics_current['recall']*100:6.2f}%{'':<17} | {metrics_smaug['recall']*100:6.2f}%{'':<17}")
    print(f"{'F1-Score':<24} | {metrics_current['f1_score']*100:6.2f}%{'':<17} | {metrics_smaug['f1_score']*100:6.2f}%{'':<17}")
    print(f"{'False Positive Rate':<24} | {metrics_current['false_positive_rate']*100:6.2f}%{'':<17} | {metrics_smaug['false_positive_rate']*100:6.2f}%{'':<17}")
    print(f"{'Confusion (TP/FP/TN/FN)':<24} | {str(metrics_current['confusion_matrix']):<24} | {str(metrics_smaug['confusion_matrix']):<24}")
    print("=" * 80)

    # Document summary
    print("\nDOCUMENT CATEGORY BEHAVIOR:")
    print(f"  Current Model Document Warning Triggered: {doc_current['results'][0]['document_domain_warning']}")
    print(f"  Current Model Prediction               : {doc_current['results'][0]['prediction']} ({doc_current['results'][0]['confidence']*100:.1f}%)")
    print(f"  Smaug Model Document Warning Triggered  : {doc_smaug['results'][0]['document_domain_warning']}")
    print(f"  Smaug Model Prediction                 : {doc_smaug['results'][0]['prediction']} ({doc_smaug['results'][0]['confidence']*100:.1f}%)")

    # Save to JSON
    output_path = PROJECT_ROOT / "benchmark_results.json"
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "photographic_benchmark": {
            "current": metrics_current,
            "smaug": metrics_smaug,
        },
        "document_benchmark": {
            "current": doc_current,
            "smaug": doc_smaug,
        }
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\nDetailed benchmark metrics saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
