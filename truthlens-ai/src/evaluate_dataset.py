"""
src/evaluate_dataset.py
=======================
PURPOSE
-------
Evaluate the pretrained TruthLens-AI image detector on a labeled dataset
organized into class subdirectories (or specified via CSV).

DATASET FOLDER STRUCTURE
------------------------
    dataset/
      REAL/
        photo1.jpg
        photo2.png
      AI_GENERATED/
        synth1.jpg
        synth2.webp

Alternative supported directory names (case-insensitive):
    - Real: "REAL", "real", "authentic", "genuine"
    - AI-Generated: "AI_GENERATED", "ai_generated", "fake", "synthetic", "ai"

FEATURES
--------
1. Processes all supported images (.jpg, .jpeg, .png, .webp).
2. Validates ground truth vs model predictions.
3. Computes comprehensive classification metrics:
   - Accuracy
   - Precision (Positive class = AI_GENERATED)
   - Recall / Sensitivity / True Positive Rate (TPR)
   - Specificity / True Negative Rate (TNR)
   - False Positive Rate (FPR = FP / [FP + TN])
   - False Negative Rate (FNR = FN / [FN + TP])
   - F1-Score
   - Full Confusion Matrix (TP, FP, TN, FN)
   - ROC-AUC (Mann-Whitney rank-sum)
4. Exports per-sample predictions, confidence, and class scores to CSV.
5. Captures and reports corrupted or unreadable files.
6. Clearly distinguishes empirical measured metrics from claims made in the model card.

USAGE (PowerShell)
------------------
    python -m src.evaluate_dataset --dataset-dir path/to/dataset
    python -m src.evaluate_dataset --dataset-dir path/to/dataset --csv-output predictions.csv
    python -m src.evaluate_dataset --help
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from src.preprocessing import SUPPORTED_EXTENSIONS
from src.inference import run_inference


# Canonical label normalization
LABEL_SYNONYMS = {
    # Real synonyms
    "real": "REAL",
    "authentic": "REAL",
    "genuine": "REAL",
    "photograph": "REAL",
    "photo": "REAL",
    "0": "REAL",
    # AI-generated synonyms
    "ai_generated": "AI_GENERATED",
    "ai-generated": "AI_GENERATED",
    "ai": "AI_GENERATED",
    "fake": "AI_GENERATED",
    "synthetic": "AI_GENERATED",
    "generated": "AI_GENERATED",
    "1": "AI_GENERATED",
}


def normalize_class_name(folder_or_label: str) -> Optional[str]:
    """Convert folder name or ground truth label to 'REAL' or 'AI_GENERATED'."""
    cleaned = str(folder_or_label).strip().lower().replace(" ", "_")
    return LABEL_SYNONYMS.get(cleaned)


def calculate_roc_auc(y_true: List[int], y_scores: List[float]) -> Optional[float]:
    """
    Calculate ROC-AUC using Mann-Whitney U rank statistics.
    Returns None if dataset contains only a single class.
    """
    if len(set(y_true)) < 2:
        return None

    paired = sorted(zip(y_scores, y_true), key=lambda x: x[0])
    n_pos = sum(1 for y in y_true if y == 1)
    n_neg = len(y_true) - n_pos

    if n_pos == 0 or n_neg == 0:
        return None

    ranks = [0.0] * len(paired)
    i = 0
    while i < len(paired):
        j = i
        while j < len(paired) and paired[j][0] == paired[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    sum_ranks_pos = sum(rank for rank, (_, y) in zip(ranks, paired) if y == 1)
    auc = (sum_ranks_pos - (n_pos * (n_pos + 1)) / 2.0) / (n_pos * n_neg)
    return round(float(auc), 4)


def compute_evaluation_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute rigorous classification metrics from evaluation records.
    Positive Class = AI_GENERATED (1), Negative Class = REAL (0).
    """
    if not records:
        return {
            "total_samples": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "specificity": 0.0,
            "false_positive_rate": 0.0,
            "false_negative_rate": 0.0,
            "f1_score": 0.0,
            "roc_auc": None,
            "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        }

    tp = 0  # Ground truth AI, predicted AI
    fp = 0  # Ground truth REAL, predicted AI (false alarm)
    tn = 0  # Ground truth REAL, predicted REAL
    fn = 0  # Ground truth AI, predicted REAL (missed fake)

    y_true = []
    y_scores_ai = []

    for r in records:
        gt = r["ground_truth"]
        pred = r["predicted_label"]
        score_ai = r["score_ai_generated"]

        y_true.append(1 if gt == "AI_GENERATED" else 0)
        y_scores_ai.append(score_ai)

        if gt == "AI_GENERATED" and pred == "AI_GENERATED":
            tp += 1
        elif gt == "REAL" and pred == "AI_GENERATED":
            fp += 1
        elif gt == "REAL" and pred == "REAL":
            tn += 1
        elif gt == "AI_GENERATED" and pred == "REAL":
            fn += 1

    total = len(records)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    auc = calculate_roc_auc(y_true, y_scores_ai)

    return {
        "total_samples": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "f1_score": round(f1, 4),
        "roc_auc": auc,
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
    }


def collect_dataset_samples(dataset_dir: Union[str, Path]) -> List[Tuple[Path, str]]:
    """
    Scan dataset folder for class subdirectories and supported image files.

    Returns list of (image_path, normalized_ground_truth).
    """
    root = Path(dataset_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: '{root}'")

    samples = []
    seen_paths = set()
    # Look for subdirectories matching REAL or AI_GENERATED
    for sub in root.iterdir():
        if not sub.is_dir():
            continue
        norm_label = normalize_class_name(sub.name)
        if norm_label is None:
            continue

        for file_path in sub.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                resolved = file_path.resolve()
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    samples.append((file_path, norm_label))

    return samples


def evaluate_folder_dataset(
    dataset_dir: Union[str, Path],
    csv_output_path: Optional[Union[str, Path]] = None,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Run evaluation on a folder-structured dataset.
    """
    samples = collect_dataset_samples(dataset_dir)
    if not samples:
        raise ValueError(
            f"No supported images found in '{dataset_dir}'.\n"
            "Ensure the dataset contains subfolders such as 'REAL/' and 'AI_GENERATED/' "
            f"with supported image formats ({', '.join(sorted(SUPPORTED_EXTENSIONS))})."
        )

    records = []
    skipped_errors = []

    print(f"\nFound {len(samples)} images across class folders in: {dataset_dir}")
    print("Running inference using pretrained Hugging Face model...\n")

    for idx, (img_path, ground_truth) in enumerate(samples, start=1):
        res = run_inference(img_path)

        if res.get("status") != "success":
            skipped_errors.append({
                "path": str(img_path),
                "file_name": img_path.name,
                "ground_truth": ground_truth,
                "error": res.get("error", "Unknown error"),
                "error_type": res.get("error_type", "unknown_error"),
            })
            continue

        score_real = 0.0
        score_ai = 0.0
        for item in res.get("raw_scores", []):
            if item["label"] == "REAL":
                score_real = float(item["score"])
            elif item["label"] == "AI_GENERATED":
                score_ai = float(item["score"])

        # Determine prediction using decision threshold
        predicted_label = "AI_GENERATED" if score_ai >= threshold else "REAL"
        is_correct = (predicted_label == ground_truth)

        record = {
            "image_path": str(img_path),
            "file_name": img_path.name,
            "ground_truth": ground_truth,
            "predicted_label": predicted_label,
            "confidence": res["confidence"],
            "score_real": score_real,
            "score_ai_generated": score_ai,
            "is_correct": is_correct,
            "inference_ms": res["inference_ms"],
            "ai_likelihood": res.get("ai_likelihood", "N/A"),
        }
        records.append(record)

    # Compute overall metrics
    metrics = compute_evaluation_metrics(records)

    # Export individual predictions to CSV if requested or default
    if csv_output_path:
        csv_file = Path(csv_output_path).resolve()
        with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "file_name",
                "ground_truth",
                "predicted_label",
                "is_correct",
                "confidence",
                "score_real",
                "score_ai_generated",
                "ai_likelihood",
                "inference_ms",
                "image_path",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)

    return {
        "model_id": "dima806/ai_vs_real_image_detection",
        "dataset_path": str(Path(dataset_dir).resolve()),
        "total_discovered": len(samples),
        "evaluated_samples": len(records),
        "skipped_files": len(skipped_errors),
        "decision_threshold": threshold,
        "metrics": metrics,
        "errors": skipped_errors,
    }


def print_evaluation_summary(results: Dict[str, Any], csv_path: Optional[str] = None) -> None:
    """Print structured, clear evaluation summary report."""
    m = results["metrics"]
    cm = m["confusion_matrix"]

    print("\n" + "=" * 68)
    print("        TRUTHLENS-AI PRETRAINED MODEL EVALUATION REPORT")
    print("=" * 68)
    print(f"  Model ID           : {results['model_id']}")
    print(f"  Dataset Location   : {results['dataset_path']}")
    print(f"  Images Evaluated   : {results['evaluated_samples']}")
    print(f"  Errors / Skipped   : {results['skipped_files']}")
    print(f"  Positive Class     : AI_GENERATED (1)")
    print(f"  Negative Class     : REAL (0)")
    print(f"  Decision Threshold : {results['decision_threshold']:.2f}")

    print("\n" + "-" * 45)
    print("MEASURED EMPIRICAL CLASSIFICATION METRICS")
    print("-" * 45)
    print(f"  Accuracy                : {m['accuracy'] * 100:.2f}%")
    print(f"  Precision               : {m['precision'] * 100:.2f}%  (TP / [TP + FP])")
    print(f"  Recall (Sensitivity)    : {m['recall'] * 100:.2f}%  (TP / [TP + FN])")
    print(f"  Specificity (TNR)       : {m['specificity'] * 100:.2f}%  (TN / [TN + FP])")
    print(f"  False Positive Rate     : {m['false_positive_rate'] * 100:.2f}%  (FP / [FP + TN])")
    print(f"  False Negative Rate     : {m['false_negative_rate'] * 100:.2f}%  (FN / [FN + TP])")
    print(f"  F1-Score                : {m['f1_score']:.4f}")
    auc_str = f"{m['roc_auc']:.4f}" if m['roc_auc'] is not None else "N/A (single class)"
    print(f"  ROC-AUC                 : {auc_str}")

    print("\nCONFUSION MATRIX:")
    print("                          Pred REAL       Pred AI_GENERATED")
    print(f"  Actual REAL             TN: {cm['tn']:<11} FP: {cm['fp']:<11}")
    print(f"  Actual AI_GENERATED     FN: {cm['fn']:<11} TP: {cm['tp']:<11}")

    print("\n" + "-" * 45)
    print("IMPORTANT NOTE ON BENCHMARKS & LIMITATIONS:")
    print("-" * 45)
    print("  1. MODEL CARD CLAIMS vs MEASURED RESULTS:")
    print("     The Hugging Face model card reports ~94.2% accuracy on its own")
    print("     CIFAKE validation split (CIFAR-10 real objects + SD 1.4 synthetic).")
    print("     The metrics above represent purely empirical measurements on YOUR dataset.")
    print("  2. EVOLUTION OF AI GENERATION:")
    print("     Modern generators (e.g. Midjourney v6, Flux, SDXL, Ideogram) differ")
    print("     from older 2022/2023 diffusion models; performance on modern generative")
    print("     outputs may vary significantly.")
    print("  3. ID CARDS & DOCUMENTS:")
    print("     Documents (e.g. PAN cards, A4 forms) are out-of-domain and can")
    print("     trigger false positives. Never rely solely on AI vision scores for ID validity.")
    print("=" * 68)

    if csv_path:
        print(f"\nPredictions exported to CSV: {csv_path}")

    if results["errors"]:
        print(f"\nSkipped / Corrupted files ({len(results['errors'])}):")
        for err in results["errors"][:5]:
            print(f"  - {err['file_name']}: {err['error']}")
        if len(results["errors"]) > 5:
            print(f"  ... and {len(results['errors']) - 5} more")

    print("\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Evaluate TruthLens pretrained AI image detector on a labeled dataset folder."
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="data",
        help="Path to labeled dataset containing REAL/ and AI_GENERATED/ subfolders (default: 'data').",
    )
    parser.add_argument(
        "--csv-output",
        type=str,
        default="evaluation_predictions.csv",
        help="Path to export per-sample prediction CSV (default: 'evaluation_predictions.csv').",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Optional path to export full evaluation summary as JSON.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold for AI_GENERATED class in [0.0, 1.0] (default: 0.5).",
    )

    args = parser.parse_args()

    try:
        results = evaluate_folder_dataset(
            dataset_dir=args.dataset_dir,
            csv_output_path=args.csv_output,
            threshold=args.threshold,
        )
    except Exception as exc:
        print(f"\n[ERROR] Evaluation failed: {exc}\n", file=sys.stderr)
        sys.exit(1)

    print_evaluation_summary(results, csv_path=args.csv_output)

    if args.json_output:
        out_p = Path(args.json_output).resolve()
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"JSON summary saved to: {out_p}\n")


if __name__ == "__main__":
    main()
