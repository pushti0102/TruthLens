# TruthLens 210-Image Forensic Model Benchmark Report

**Date:** 2026-11-19 02:02:45
**Total Samples:** 210 independently labeled images

## 1. Models Evaluated
- **Current ViT:** `dima806/ai_vs_real_image_detection` (vit)
- **Smaug:** `abacusai/Smaug-AI-Image-Detector` (smaug)

## 2. Standard Photographic & Synthetic Evaluation (150 Images)
Comprises: 50 Known Smartphone Photos (Negative Class) + 50 Diffusion Photos + 50 Diffusion Art (Positive Class).

| Metric | Current ViT (`dima806`) | Smaug (`abacusai`) |
|---|---|---|
| **Accuracy** | 71.33% | 82.67% |
| **Precision** | 69.93% | 98.68% |
| **Recall (AI Detection)** | 100.00% | 75.00% |
| **F1-Score** | 0.8230 | 0.8523 |
| **False Positive Rate (FPR)** | 86.00% | 2.00% |
| **False Negative Rate (FNR)** | 0.00% | 25.00% |
| **True Positives (TP)** | 100 / 100 | 75 / 100 |
| **False Positives (FP)** | 43 / 50 | 1 / 50 |
| **True Negatives (TN)** | 7 / 50 | 49 / 50 |
| **False Negatives (FN)** | 0 / 100 | 25 / 100 |
| **Mean Latency (ms)** | 966.01 ms | 6140.51 ms |
| **p95 Latency (ms)** | 1287.7 ms | 14114.6 ms |

## 3. Per-Category Breakdown

### A. Real Smartphone Photographs (N=50)
- **Current ViT:** Real: 7, AI Flagged (FP): 43
- **Smaug:** Real: 49, AI Flagged (FP): 1

### B. AI-Generated Photographs (N=50)
- **Current ViT:** AI (TP): 50, Real (FN): 0
- **Smaug:** AI (TP): 38, Real (FN): 12

### C. Artistic Synthetic Images (N=50)
- **Current ViT:** AI (TP): 50, Real (FN): 0
- **Smaug:** AI (TP): 37, Real (FN): 13

### D. Manipulated & Tampered Images (N=35, Splicing / Copy-Move / Q15 Recompression)
- **Current ViT:** Flagged as AI: 32 (91.4%), Classified Real: 3
- **Smaug:** Flagged as AI: 0 (0.0%), Classified Real: 35

## 4. Document Evaluation (Evaluated Strictly Separately, N=25)
Documents have structured typographic layout, high-contrast borders, and lack natural camera sensor noise.
- **Current ViT:** Document Domain Warnings Triggered: 25/25 (100.0%) | Raw Real: 0, Raw AI: 25
- **Smaug:** Document Domain Warnings Triggered: 25/25 (100.0%) | Raw Real: 25, Raw AI: 0

## 5. Critical Observations & Trade-Offs
1. **ViT False Positive Vulnerability:** ViT fine-tuned on CIFAR-sized images frequently misclassifies high-resolution smartphone camera noise and fine details as AI generation patterns.
2. **Smaug Multi-Crop Calibration:** Smaug utilizes multi-crop feature aggregation, providing substantially reduced false positive rates on natural smartphone photos while maintaining high recall on diffusion-generated images.
3. **Manipulated Media Bounds:** Neither general AI image detector is designed as a specialized localized tamper detector. Copy-move and splicing without whole-frame diffusion synthesis often yield low confidence or inconclusive outcomes.
4. **Document Scans:** Neither model should be treated as authoritative on identity cards or document forms; the document domain warning correctly guides users to verify cryptographic provenance rather than trusting vision features.