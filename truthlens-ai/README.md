# TruthLens-AI — AI/ML Component

> **Member 1 deliverable** for the TruthLens: Digital Media Authenticity & Provenance Verification System.
> This component analyzes images to estimate statistical resemblance to AI-generated versus authentic photographic imagery using a pretrained Hugging Face Vision Transformer (ViT).
> It is designed to run independently from the command line and be seamlessly imported by the FastAPI backend (Member 3).

---

## Table of Contents

1. [Component Architecture & Pipeline](#1-component-architecture--pipeline)
2. [Model Attribution, Architecture & Specifications](#2-model-attribution-architecture--specifications)
3. [AI Detection vs. Authenticity Verification](#3-ai-detection-vs-authenticity-verification)
4. [Project Structure](#4-project-structure)
5. [Quick Start — Windows PowerShell](#5-quick-start--windows-powershell)
6. [Single Image Inference](#6-single-image-inference)
7. [Structured Output Format](#7-structured-output-format)
8. [Folder-Based Dataset Evaluation (`src/evaluate_dataset.py`)](#8-folder-based-dataset-evaluation-srcevaluate_datasetpy)
9. [Running Tests](#9-running-tests)
10. [Document & ID Card Handling (e.g., PAN Cards)](#10-document--id-card-handling-eg-pan-cards)
11. [Known Limitations & Model Evolution Over Time](#11-known-limitations--model-evolution-over-time)
12. [FastAPI Integration](#12-fastapi-integration)

---

## 1. Component Architecture & Pipeline

```
Image file (PNG / JPEG / WebP)
        │
        ▼
┌─────────────────────────┐
│   src/preprocessing.py  │  ← Path validation, Pillow safe RGB decoding, aspect ratio & document geometry checks
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   src/detector.py       │  ← Loads pretrained ViT using AutoImageProcessor & AutoModelForImageClassification
└───────────┬─────────────┘    (SafeTensors, CUDA auto-detect with CPU default, id2label verification)
            │
            ▼
┌─────────────────────────┐
│   src/inference.py      │  ← Ties preprocessing & detector; computes cautious likelihood, domain warnings, timing
└─────────────────────────┘
```

---

## 2. Model Attribution, Architecture & Specifications

| Property | Detail |
|---|---|
| **Model ID** | `dima806/ai_vs_real_image_detection` |
| **Hugging Face Hub** | [https://huggingface.co/dima806/ai_vs_real_image_detection](https://huggingface.co/dima806/ai_vs_real_image_detection) |
| **Architecture** | Vision Transformer (`google/vit-base-patch16-224`) fine-tuned via Hugging Face AutoTrain |
| **Task** | Binary Image Classification (`REAL` vs `FAKE` / `AI_GENERATED`) |
| **Weights Format** | SafeTensors (`model.safetensors`, ~343 MB), downloaded automatically on first run and cached in `~/.cache/huggingface/hub/` |
| **Parameters** | ~85.8 Million |
| **Training Dataset** | CIFAKE dataset (60,000 synthetic images generated via Stable Diffusion 1.4 + 60,000 real images from CIFAR-10) |
| **License** | Creative Commons Attribution-NoDerivatives 4.0 International ([CC-BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/)) |
| **Reported Validation Accuracy** | 94.2% (on its own CIFAKE validation split; measured separately on your custom test data) |
| **Input Preprocessing** | Resized to 224×224 pixels, normalised with mean `[0.5, 0.5, 0.5]` and std `[0.5, 0.5, 0.5]` via `AutoImageProcessor` |
| **Hardware** | CPU by default (~100–300 ms on modern CPUs); automatic CUDA GPU acceleration when available |

### Class Label Mapping
Inspecting `model.config.id2label` and `model.config.label2id` reveals:
- Index `0` → `"REAL"` (mapped canonically to `"REAL"`)
- Index `1` → `"FAKE"` (mapped canonically to `"AI_GENERATED"`)

---

## 3. AI Detection vs. Authenticity Verification

> [!IMPORTANT]
> **AI pattern detection is NOT proof of digital authenticity or fraud.**
> TruthLens employs a multi-layered defense architecture:
> - **Member 1 (AI/ML)**: Evaluates statistical image-surface artifact similarities to learned diffusion models.
> - **Member 2 (Security & Provenance)**: Verifies cryptographic hashes (SHA-256), digital signatures, and C2PA metadata.
> - **Member 3 (Backend & Orchestration)**: Aggregates verification vectors into an integrated audit report.

Key principles adhered to in this implementation:
1. **No Definitive "Fake" Labels**: Images are never declared fake solely on visual model scores. Cautious confidence bands (`high`, `moderate`, `low`, `inconclusive`) are reported alongside raw probabilities.
2. **Provenance Independence**: Missing EXIF data or provenance manifests does not imply synthetic generation.
3. **Out-of-Domain Boundaries**: The model estimates resemblance to its training set (CIFAKE), not document authenticity or identity veracity.

---

## 4. Project Structure

```
truthlens-ai/
├── data/
│   ├── REAL/                      ← Put real photographic test images here
│   └── AI_GENERATED/              ← Put AI-generated test images here
├── models/                        ← Optional local cache directory
├── src/
│   ├── __init__.py
│   ├── preprocessing.py           ← Pillow loading, RGB conversion, document aspect-ratio check
│   ├── detector.py                ← AutoImageProcessor + AutoModelForImageClassification wrapper
│   ├── inference.py               ← Single-image inference pipeline & CLI
│   ├── evaluate_dataset.py        ← Folder-based dataset evaluator with CSV export & metrics
│   └── evaluate.py                ← CSV-based batch evaluator
├── tests/
│   ├── __init__.py
│   ├── test_preprocessing.py      ← File loading, error handling, mode conversion
│   ├── test_detector.py           ← Detector mocks, error recovery, label mapping
│   ├── test_inference.py          ← Structured output, error isolation, guarantees
│   ├── test_class_mapping.py      ← id2label verification, ID-1 card preprocessing
│   └── test_smoke_pretrained.py   ← Smoke test on actual pretrained Hugging Face model & folder evaluation
├── requirements.txt               ← Python dependencies (torch, transformers, safetensors, Pillow, pytest)
├── pytest.ini                     ← Pytest configuration
└── README.md                      ← Documentation
```

---

## 5. Quick Start — Windows PowerShell

Navigate to the project root in Windows PowerShell:

```powershell
cd "D:\projects\ISC Project\truthlens-ai"
```

### Step 1 — Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

*(Ensure your execution policy allows local scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` if needed).*

### Step 2 — Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## 6. Single Image Inference

### Command Line Interface

```powershell
# Default / Current model (dima806/ai_vs_real_image_detection)
python -m src.inference "C:\path\to\image.jpg" --model current

# Smaug model (abacusai/Smaug-AI-Image-Detector)
python -m src.inference "C:\path\to\image.jpg" --model smaug
```

#### Available Models:
- `current` (default): `dima806/ai_vs_real_image_detection` — Vision Transformer fine-tuned on CIFAKE.
- `smaug`: `abacusai/Smaug-AI-Image-Detector` — EmbeddingGemma-2 based multi-crop AI image detector (requires `pip install sentence-transformers`).

Example output:
```json
{
  "status": "success",
  "file_name": "sample.jpg",
  "label": "REAL",
  "confidence": 0.8845,
  "raw_scores": [
    {
      "label": "REAL",
      "score": 0.8845
    },
    {
      "label": "AI_GENERATED",
      "score": 0.1155
    }
  ],
  "model_id": "dima806/ai_vs_real_image_detection",
  "inference_ms": 142.3,
  "ai_likelihood": "low",
  "warning": "Experimental AI-image detection; this prediction does not prove authenticity.",
  "image_info": {
    "width": 1024,
    "height": 768,
    "mode": "RGB",
    "aspect_ratio": 1.3333
  },
  "domain_note": "Model was trained on natural and artistic imagery (CIFAKE dataset). It has not been validated on ID cards, credentials, or document scans.",
  "provenance_note": "AI pattern detection does not establish provenance, legal validity, or document authenticity. Cryptographic integrity (SHA-256) and provenance checks must be evaluated independently."
}
```

### Python API

```python
from src.inference import run_inference

result = run_inference("path/to/image.png")
if result["status"] == "success":
    print(f"Prediction: {result['label']} (Confidence: {result['confidence'] * 100:.1f}%)")
    print(f"Likelihood: {result['ai_likelihood']}")
    print(f"Warning:    {result['warning']}")
else:
    print(f"Error ({result['error_type']}): {result['error']}")
```

---

## 7. Structured Output Format

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `"success"` or `"error"` |
| `file_name` | `str` | Name of the evaluated image file |
| `label` | `str` | Canonical top prediction: `"REAL"` or `"AI_GENERATED"` |
| `confidence` | `float` | Probability score for the top predicted class in `[0.0, 1.0]` |
| `raw_scores` | `list` | Full array of `{"label": str, "score": float}` for both classes |
| `model_id` | `str` | Hugging Face repository identifier |
| `inference_ms` | `float` | Wall-clock inference time in milliseconds |
| `ai_likelihood` | `str` | Cautious category: `"high"`, `"moderate"`, `"low"`, or `"inconclusive"` |
| `warning` | `str` | Mandatory experimental advisory stating prediction does not prove authenticity |
| `document_domain_warning` | `str` *(optional)* | Advisory triggered when input exhibits ID card / document geometry |
| `image_info` | `dict` | Input `width`, `height`, `mode`, and `aspect_ratio` |
| `domain_note` | `str` | Context explaining CIFAKE training scope |
| `provenance_note` | `str` | Clear boundary separating visual classification from cryptographic provenance |

---

## 8. Folder-Based Dataset Evaluation (`src/evaluate_dataset.py`)

To evaluate the detector against a labeled dataset organized into class folders:

### Dataset Directory Structure
```
my_dataset/
├── REAL/
│   ├── photo_001.jpg
│   └── photo_002.png
└── AI_GENERATED/
    ├── gen_001.jpg
    └── gen_002.webp
```

*(Folder names are case-insensitive and support synonyms: `REAL`, `real`, `authentic`, `genuine`; `AI_GENERATED`, `ai_generated`, `fake`, `synthetic`).*

### Running the Evaluation

```powershell
python -m src.evaluate_dataset --dataset-dir my_dataset --csv-output evaluation_predictions.csv
```

Optional arguments:
- `--threshold 0.5` : Probability threshold for classifying an image as `AI_GENERATED` (default: 0.50).
- `--json-output metrics.json` : Export complete evaluation results and confusion matrix as JSON.

### Metrics Computed & Reported
- **Accuracy**: Overall fraction of correct predictions: `(TP + TN) / Total`
- **Precision**: Fraction of AI predictions that are genuinely AI: `TP / (TP + FP)`
- **Recall (Sensitivity / TPR)**: Fraction of actual AI images detected: `TP / (TP + FN)`
- **Specificity (TNR)**: Fraction of real images correctly identified: `TN / (TN + FP)`
- **False Positive Rate (FPR)**: Real images incorrectly flagged as AI: `FP / (FP + TN)`
- **False Negative Rate (FNR)**: AI images missed: `FN / (FN + TP)`
- **F1-Score**: Harmonic mean of Precision and Recall
- **Confusion Matrix**: Full breakdown of `TP`, `FP`, `TN`, `FN`
- **ROC-AUC**: Mann-Whitney U rank-sum calculation across continuous confidence scores

### Individual Predictions CSV
Exported to `evaluation_predictions.csv` with per-image records:
`file_name, ground_truth, predicted_label, is_correct, confidence, score_real, score_ai_generated, ai_likelihood, inference_ms, image_path`.

---

## 9. Running Tests

### 1. Run Complete Test Suite (Fast Unit Tests + Smoke Tests)

```powershell
pytest
```

*Runs 97 unit, smoke, and validation tests.*

### 2. Run Smoke Test on Real Pretrained Model

```powershell
pytest tests/test_smoke_pretrained.py -v
```

Verifies model loading from Hugging Face cache, SafeTensors integrity, label mapping, and end-to-end inference without mocking.

### 3. Run with Full Integration Markers

```powershell
pytest --integration -v
```

---

## 10. Document & ID Card Handling (e.g., PAN Cards)

### Why Scanned Documents & PAN Cards Trigger High AI Scores
During testing, an authentic Indian PAN card photograph was classified as `AI_GENERATED` with **93.6% confidence**.
- **Root Cause**: The model is fine-tuned on the CIFAKE dataset (CIFAR-10 objects like cars, birds, ships, plus Stable Diffusion 1.4 synthetic images). It was **never trained on identity cards, scanned text, plastic lamination, or microprinting**.
- **Softmax Overconfidence**: Vision Transformers exposed to out-of-distribution inputs project features into extreme ends of the decision boundary, yielding high-confidence misclassifications.
- **Handling Principle**:
  - We **do not** modify model weights or artificially depress the decision threshold just to make a specific document pass.
  - The pipeline dynamically detects document/ID-1 aspect ratios (~1.586 for PAN/ID cards, ~1.414 for A4 pages) via `check_document_characteristics()`.
  - When detected, a dedicated `document_domain_warning` is appended:
    > *"Input format exhibits characteristics of an Identity card / credential format (e.g. PAN card, ID-1 card, driving license). Pretrained vision transformers frequently produce high-confidence false positive AI detections on text documents and ID cards. This prediction should be treated with caution and verified using non-visual provenance tools."*
  - OCR text correctness is **not** used as proof of image authenticity.

---

## 11. Known Limitations & Model Evolution Over Time

1. **Evolution of Generative AI**:
   - The model was trained on **Stable Diffusion 1.4** (2022/2023 era diffusion patterns).
   - Generative image synthesis has evolved drastically with modern architectures (e.g., **Midjourney v6, FLUX.1, SDXL, Ideogram, DALL-E 3**).
   - Artifacts learned from older diffusion engines (latent upscaler checkerboards, specific frequency noise) are absent in newer flow-matching models. Performance on latest-generation AI images may be degraded.
2. **Artistic & Object Bias**:
   - High fidelity on artistic and natural scenes; lower sensitivity to localized facial swaps (deepfakes).
3. **No Cryptographic Proof**:
   - Predictions are heuristic pattern recognitions and must not be used as standalone legal evidence of authenticity.

---

## 12. FastAPI Integration

When Member 3 builds the API layer, `run_inference` can be called directly:

```python
from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil
from src.inference import run_inference

app = FastAPI(title="TruthLens AI Service")

@app.post("/api/v1/detect-image")
async def detect_image(file: UploadFile = File(...)):
    temp_path = Path("temp_uploads") / file.filename
    temp_path.parent.mkdir(exist_ok=True)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = run_inference(temp_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return result
```

*The detector instance is loaded as a singleton in memory on the first request and reused across subsequent calls, eliminating weight reloading overhead.*

---

*TruthLens AI — Digital Media Authenticity & Provenance Verification System*
*Member 1: AI/ML & Multimedia Analysis Component*
