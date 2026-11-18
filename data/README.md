# TruthLens Data & Evaluation Datasets

This directory contains evaluation benchmarks, dataset manifests, and test media assets used to validate the TruthLens forensic detection pipeline.

---

## Directory & File Overview

| Path | Description |
|------|-------------|
| `benchmark_210_results.json` | Complete benchmark execution metrics (Accuracy, Precision, Recall, F1, FPR, Confusion Matrix, and inference times) across both ViT and Smaug models on 210 test images. |
| `benchmark_210_summary.md` | Comprehensive human-readable benchmark evaluation report detailing domain-specific performance, false positive analysis, and calibration notes. |
| `benchmark_10_legacy.json` | Initial 10-sample exploratory audit results from Phase 1. |
| `evaluation_210_manifest.json` | Complete metadata manifest for all 210 test images, including image ID, ground truth, category, format, resolution, and compression characteristics. |
| `test_document_id.jpg` | Sample document image used for testing document-domain warning boundaries. |
| `evaluation_210/` *(git-ignored)* | Generated 210-image multi-domain benchmark dataset (photographs, synthetic AI images, diffusion art, manipulated forensics, document scans). Regenerated via `python scripts/build_210_dataset.py`. |
| `cifake_dataset/` *(git-ignored)* | Raw CIFAKE image dataset partition (`FAKE` / `REAL`). |

---

## Evaluation Dataset Composition (210 Samples)

1. **Natural Smartphone Photographs (50 images):** Real camera photos captured with various smartphone sensors, lighting conditions, and angles.
2. **AI-Generated Photographs (50 images):** Photorealistic synthetic images generated via diffusion architectures (Stable Diffusion / Midjourney).
3. **Artistic Synthetic Images (50 images):** Stylized non-photorealistic synthetic art (anime, surrealism, digital painting).
4. **Forensic Manipulations (35 images):** Tampered real photographs exhibiting copy-move, splicing, resampling, and localized blur.
5. **Document Scans (25 images):** High-contrast text, forms, certificates, and ID cards evaluated strictly separately as an out-of-domain category.
