"""
src/evaluate.py
===============
PURPOSE
-------
Batch evaluation script for TruthLens-AI image authenticity detection.

Accepts a CSV file containing image paths and ground-truth labels, runs
inference on each image, and calculates comprehensive classification metrics:
  - Accuracy
  - Precision (Positive class = AI_GENERATED)
  - Recall    (Positive class = AI_GENERATED)
  - F1-Score  (Positive class = AI_GENERATED)
  - Confusion Matrix (TP, FP, TN, FN)
  - ROC-AUC (when valid probabilities and both classes exist)
  - Category breakdown (e.g. photographs vs documents vs other) when provided.

CLASS MAPPING & CONVENTIONS
---------------------------
- Positive Class : AI_GENERATED (1)
- Negative Class : REAL (0)

Ground-truth labels in the CSV are normalized:
  - "real", "authentic", "genuine", "0" -> REAL
  - "ai_generated", "fake", "synthetic", "ai", "1" -> AI_GENERATED

USAGE
-----
    python -m src.evaluate --csv path/to/dataset.csv
    python -m src.evaluate --csv path/to/dataset.csv --output results.json
    python -m src.evaluate --help
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from src.inference import run_inference


# Canonical label normalization for evaluation
GROUND_TRUTH_MAP = {
    "real": "REAL",
    "genuine": "REAL",
    "authentic": "REAL",
    "photo": "REAL",
    "0": "REAL",
    "fake": "AI_GENERATED",
    "ai": "AI_GENERATED",
    "ai_generated": "AI_GENERATED",
    "ai-generated": "AI_GENERATED",
    "synthetic": "AI_GENERATED",
    "generated": "AI_GENERATED",
    "1": "AI_GENERATED",
}


def normalize_ground_truth(raw_label: str) -> Optional[str]:
    """Normalize user-supplied ground truth string to 'REAL' or 'AI_GENERATED'."""
    cleaned = str(raw_label).strip().lower()
    return GROUND_TRUTH_MAP.get(cleaned)


def calculate_roc_auc(y_true: List[int], y_scores: List[float]) -> Optional[float]:
    """
    Calculate ROC-AUC using the Mann-Whitney U rank-sum method.
    Pure Python implementation: zero external dependencies, handles ties.
    Returns None if fewer than 2 classes are present.
    """
    if len(set(y_true)) < 2:
        return None  # ROC-AUC is undefined if only one class exists

    # Pair scores with true labels
    paired = sorted(zip(y_scores, y_true), key=lambda x: x[0])
    n_pos = sum(1 for y in y_true if y == 1)
    n_neg = len(y_true) - n_pos

    if n_pos == 0 or n_neg == 0:
        return None

    # Calculate ranks with tie handling
    ranks = [0.0] * len(paired)
    i = 0
    while i < len(paired):
        j = i
        while j < len(paired) and paired[j][0] == paired[i][0]:
            j += 1
        # Assign average rank (1-indexed)
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    # Sum of ranks for positive class
    sum_ranks_pos = sum(rank for rank, (_, y) in zip(ranks, paired) if y == 1)
    auc = (sum_ranks_pos - (n_pos * (n_pos + 1)) / 2.0) / (n_pos * n_neg)
    return round(float(auc), 4)


def compute_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute classification metrics from evaluation records.
    Each record must have 'ground_truth' ('REAL' or 'AI_GENERATED')
    and 'predicted_label' ('REAL' or 'AI_GENERATED'), plus 'predicted_score_ai'.
    """
    if not records:
        return {
            "total_samples": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "roc_auc": None,
            "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        }

    tp = 0  # Actual AI, Pred AI
    fp = 0  # Actual REAL, Pred AI (False Alarm)
    tn = 0  # Actual REAL, Pred REAL
    fn = 0  # Actual AI, Pred REAL (Missed AI)

    y_true_binary = []
    y_scores_ai = []

    for r in records:
        gt = r["ground_truth"]
        pred = r["predicted_label"]
        score_ai = r["predicted_score_ai"]

        y_true_binary.append(1 if gt == "AI_GENERATED" else 0)
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
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    auc = calculate_roc_auc(y_true_binary, y_scores_ai)

    return {
        "total_samples": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": auc,
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
    }


def evaluate_dataset(
    csv_path: Union[str, Path],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Read dataset CSV, run inference on all images, and compile evaluation results.
    """
    csv_file = Path(csv_path).resolve()
    if not csv_file.exists():
        raise FileNotFoundError(f"Evaluation dataset CSV not found: '{csv_file}'")

    records = []
    errors = []
    categories: Dict[str, List[Dict[str, Any]]] = {}

    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {"error": "CSV file is empty or missing headers"}

        # Normalize field names
        fields = {k.strip().lower(): k for k in reader.fieldnames}
        path_col = fields.get("image_path") or fields.get("path") or fields.get("file_path") or fields.get("filename")
        gt_col = fields.get("ground_truth_label") or fields.get("ground_truth") or fields.get("label")
        cat_col = fields.get("category") or fields.get("type") or fields.get("image_type")

        if not path_col or not gt_col:
            raise ValueError(
                f"CSV must contain 'image_path' and 'ground_truth_label' columns.\n"
                f"Found headers: {list(reader.fieldnames)}"
            )

        csv_dir = csv_file.parent

        for row_idx, row in enumerate(reader, start=2):
            raw_path = row[path_col].strip()
            raw_gt = row[gt_col].strip()
            cat = row[cat_col].strip().lower() if cat_col and row.get(cat_col) else "unspecified"

            gt_label = normalize_ground_truth(raw_gt)
            if gt_label is None:
                errors.append({
                    "row": row_idx,
                    "path": raw_path,
                    "error": f"Invalid ground-truth label: '{raw_gt}' (must be REAL or AI_GENERATED)",
                })
                continue

            # Resolve relative image paths against CSV location
            target_path = Path(raw_path)
            if not target_path.is_absolute():
                target_path = csv_dir / target_path

            if not target_path.exists():
                errors.append({
                    "row": row_idx,
                    "path": str(target_path),
                    "error": "File does not exist on disk",
                })
                continue

            # Run inference
            result = run_inference(target_path)
            if result.get("status") != "success":
                errors.append({
                    "row": row_idx,
                    "path": str(target_path),
                    "error": result.get("error", "Unknown inference failure"),
                })
                continue

            # Extract AI_GENERATED score
            score_ai = 0.0
            for item in result.get("raw_scores", []):
                if item["label"] == "AI_GENERATED":
                    score_ai = float(item["score"])
                    break

            # Predicted label based on score threshold
            predicted_label = "AI_GENERATED" if score_ai >= threshold else "REAL"

            record = {
                "image_path": str(target_path),
                "file_name": target_path.name,
                "ground_truth": gt_label,
                "predicted_label": predicted_label,
                "predicted_score_ai": score_ai,
                "confidence": result["confidence"],
                "category": cat,
                "inference_ms": result["inference_ms"],
            }
            records.append(record)

            if cat not in categories:
                categories[cat] = []
            categories[cat].append(record)

    # Compute overall metrics
    overall_metrics = compute_metrics(records)

    # Compute per-category metrics if categories are available
    category_metrics = {}
    if len(categories) > 1 or (len(categories) == 1 and "unspecified" not in categories):
        for cat_name, cat_records in categories.items():
            category_metrics[cat_name] = compute_metrics(cat_records)

    return {
        "positive_class": "AI_GENERATED",
        "negative_class": "REAL",
        "decision_threshold": threshold,
        "overall": overall_metrics,
        "per_category": category_metrics,
        "evaluated_records": len(records),
        "skipped_errors": errors,
    }


def print_evaluation_report(results: Dict[str, Any]) -> None:
    """Print a clean CLI evaluation report."""
    print("\n" + "=" * 65)
    print("           TRUTHLENS-AI BATCH EVALUATION REPORT")
    print("=" * 65)
    print(f"Positive Class (1) : {results['positive_class']}")
    print(f"Negative Class (0) : {results['negative_class']}")
    print(f"Decision Threshold : {results['decision_threshold']:.2f}")
    print(f"Evaluated Samples  : {results['evaluated_records']}")
    print(f"Errors / Skipped   : {len(results['skipped_errors'])}")

    ov = results["overall"]
    cm = ov["confusion_matrix"]
    print("\n" + "─" * 45)
    print("OVERALL CLASSIFICATION METRICS")
    print("─" * 45)
    print(f"  Accuracy  : {ov['accuracy'] * 100:.2f}%")
    print(f"  Precision : {ov['precision'] * 100:.2f}%  (TP / [TP + FP])")
    print(f"  Recall    : {ov['recall'] * 100:.2f}%  (TP / [TP + FN])")
    print(f"  F1-Score  : {ov['f1_score']:.4f}")
    auc_str = f"{ov['roc_auc']:.4f}" if ov['roc_auc'] is not None else "N/A (single class)"
    print(f"  ROC-AUC   : {auc_str}")

    print("\nCONFUSION MATRIX:")
    print("                          Pred REAL    Pred AI_GENERATED")
    print(f"  Actual REAL             TN: {cm['tn']:<8} FP: {cm['fp']:<8}")
    print(f"  Actual AI_GENERATED     FN: {cm['fn']:<8} TP: {cm['tp']:<8}")

    if results.get("per_category"):
        print("\n" + "─" * 45)
        print("PER-CATEGORY BREAKDOWN")
        print("─" * 45)
        for cat, m in results["per_category"].items():
            ccm = m["confusion_matrix"]
            print(f"\n  [Category: {cat.upper()}] ({m['total_samples']} samples)")
            print(f"    Accuracy  : {m['accuracy'] * 100:.2f}%")
            print(f"    Precision : {m['precision'] * 100:.2f}%")
            print(f"    Recall    : {m['recall'] * 100:.2f}%")
            print(f"    F1-Score  : {m['f1_score']:.4f}")
            print(f"    CM (TP/FP/TN/FN): {ccm['tp']} / {ccm['fp']} / {ccm['tn']} / {ccm['fn']}")

    if results["skipped_errors"]:
        print("\n" + "─" * 45)
        print(f"ERRORS ENCOUNTERED ({len(results['skipped_errors'])} items):")
        for err in results["skipped_errors"][:5]:
            print(f"  - Row {err.get('row')}: {err.get('path')} -> {err.get('error')}")
        if len(results["skipped_errors"]) > 5:
            print(f"  ... and {len(results['skipped_errors']) - 5} more")

    print("\n" + "=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Batch evaluate TruthLens AI image detector on a labeled dataset."
    )
    parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Path to labeled CSV (must have 'image_path' and 'ground_truth_label' columns).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold for AI_GENERATED class (default: 0.5).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save full results as JSON.",
    )

    args = parser.parse_args()

    try:
        results = evaluate_dataset(args.csv, threshold=args.threshold)
    except Exception as exc:
        print(f"\n[ERROR] Evaluation failed: {exc}\n", file=sys.stderr)
        sys.exit(1)

    print_evaluation_report(results)

    if args.output:
        out_path = Path(args.output).resolve()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Full results saved to: {out_path}\n")


if __name__ == "__main__":
    main()
