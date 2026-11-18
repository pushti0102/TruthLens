# TruthLens: Digital Media Forensics & Provenance Verification Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

TruthLens is a digital media verification and provenance platform that couples multi-model deep learning forensics with cryptographic integrity and digital signature tracking. Rather than treating deep-learning scores as an opaque binary verdict, TruthLens cleanly separates statistical visual artifact cues from bitwise cryptographic proofs, providing an explainable, deterministic Trust Assessment.

---

## 🏗️ Project Architecture & Team Contributions

The platform integrates work across three specialized sub-systems:

```
                               ┌───────────────────────────────────────────────┐
                               │           TruthLens Web Application           │
                               │        (React 19 + Tailwind CSS Dashboard)    │
                               └──────────────────────┬────────────────────────┘
                                                      │ REST API / JWT Bearer
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       Backend Orchestrator (FastAPI)                                        │
│  - RBAC & JWT Authentication (Argon2id)                       - SQLite ORM Storage & Audit Logging          │
│  - Dynamic Model Registry & Routing                           - Transparent 6-State Trust Assessment Engine │
└───────────────────────┬─────────────────────────────────────────────┬───────────────────────────────────────┘
                        │ Internal Python API                         │ Internal Python API
                        ▼                                             ▼
┌───────────────────────────────────────────────┐   ┌─────────────────────────────────────────────────────────┐
│       AI Visual Forensics (Member 1)          │   │         Cryptographic Engine (Member 2)                 │
│ - Standard ViT-Base Patch16-224               │   │ - FIPS 180-4 SHA-256 Bitwise Integrity Hashing          │
│ - Advanced Smaug Multi-Crop Forensics         │   │ - ECDSA SECP256R1 Digital Signatures (Publisher Provenance)
│ - Domain boundary checks & Calibrated Scoring │   │ - AES-256-GCM Storage Encryption & Key Management       │
└───────────────────────────────────────────────┘   └─────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Directory Structure

```text
TruthLens/
├── backend/                  # FastAPI orchestration server (Member 3)
│   ├── app/
│   │   ├── models/           # SQLAlchemy ORM models (User, Verification, Provenance, AuditLog)
│   │   ├── routers/          # API endpoint controllers (media, auth, publishers, admin, dashboard, system)
│   │   ├── schemas/          # Pydantic v2 request/response data contracts
│   │   ├── security/         # JWT generation, Argon2id password hashing, key loading
│   │   ├── services/         # Orchestration (ai_service, crypto_service, trust_engine, audit_service)
│   │   ├── config.py         # Application settings & environment configuration
│   │   ├── database.py       # SQLite connection manager & session factory
│   │   └── main.py           # FastAPI application entry point & CORS configuration
│   └── tests/                # Backend API & router integration tests
│
├── frontend/                 # Professional dark-theme React dashboard (Member 3)
│   ├── src/
│   │   ├── components/       # UI components (Sidebar.jsx, ProtectedRoute.jsx)
│   │   ├── pages/            # Core views (Dashboard, Verify, Results, History, PublisherRegister, AdminPanel, SystemStatus, Login, Register)
│   │   ├── services/         # Axios API clients (api.js, auth.js)
│   │   ├── store/            # Global state context (AuthContext.jsx)
│   │   ├── App.jsx           # Client-side router & layout wrapper
│   │   └── index.css         # Tailwind utility classes & dark-theme tokens
│   ├── tailwind.config.js    # Cybersecurity dark palette configuration (#0D1117, #111827, #18212F, #8B5CF6)
│   └── package.json          # Node dependencies (React 19, Lucide, Recharts, Vite)
│
├── truthlens-ai/             # AI forensic vision detection subsystem (Member 1)
│   ├── src/
│   │   ├── detector.py       # Multi-model detector (ViT-Base & Smaug EmbeddingGemma-2)
│   │   ├── inference.py      # Preprocessing, forward pass execution, model routing, softmax normalization
│   │   └── preprocessing.py  # Image validation, normalization, and aspect ratio checks
│   ├── data/                 # Sample images for detector unit tests
│   ├── tests/                # AI pipeline unit and integration tests
│   └── pytest.ini            # Pytest configuration for AI module
│
├── member2_security/         # Cryptographic security & key management subsystem (Member 2)
│   ├── crypto/               # SHA-256 bitwise hashing, ECDSA SECP256R1 signing, AES-256-GCM encryption
│   ├── key_management/       # Public/private key utility helpers, serializing, and registry
│   ├── security/             # Rate limiting, file validation, and magic byte checking
│   └── tests/                # Cryptography & security primitive unit tests
│
├── shared/                   # Shared cross-module specifications
│   ├── api_contract.md       # REST endpoint contract between frontend and backend
│   └── verification_schema.json # JSON schema defining verification report output
│
├── data/                     # Datasets & benchmark manifests
│   ├── benchmark_210_results.json # Full benchmark metrics across 210 test samples
│   ├── benchmark_210_summary.md   # Detailed evaluation report & confusion matrix analysis
│   ├── evaluation_210_manifest.json # Evaluation dataset image manifest & metadata
│   ├── test_document_id.jpg       # Sample document for domain boundary testing
│   ├── cifake_dataset/       # (Ignored in Git) Raw CIFAKE evaluation dataset
│   └── README.md             # Dataset documentation
│
├── demo_samples/             # Demonstration images for live verification
│   ├── original_demo.png     # Authoritative test image for publisher registration
│   ├── tampered_demo.png     # 1-pixel modified copy for tamper detection demonstration
│   ├── real_dog_photo.jpg    # Authentic smartphone camera photograph
│   └── ai_generated_anime.png# Diffusion AI-generated synthetic sample
│
├── scripts/                  # Automation, benchmarking, and verification utilities
│   ├── build_210_dataset.py  # Assembles independent 210-image evaluation dataset
│   ├── run_210_benchmark.py  # Executes 210-image benchmark comparing ViT vs Smaug
│   ├── benchmark_models.py   # Model evaluation runner
│   ├── test_model_routing_e2e.py # End-to-end API test verifying model routing & disagreement
│   ├── generate_test_images.py   # Generates original & tampered demo images
│   └── test_verify_pipeline.py   # Functional verification API client
│
├── secrets/                  # (Ignored in Git) Local dev ECDSA key pairs
├── storage/                  # (Ignored in Git) Uploaded media storage
├── tests/                    # End-to-end system integration tests
│   └── test_audit_e2e.py     # 11 comprehensive multi-module E2E test cases
│
├── .env.example              # Environment variable configuration template
├── .gitignore                # Comprehensive Git ignore rules (keys, caches, datasets)
├── requirements.txt          # Python root dependencies
└── SECURITY.md               # Security disclosures & cryptographic key handling policies
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (with virtual environment)
- Node.js 18+ and npm

### 2. Backend Setup & Startup
```powershell
# Set Python path to project root
$env:PYTHONPATH = "."

# Start FastAPI backend server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Subsystem Health Endpoint**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 3. Frontend Setup & Startup
```powershell
# Navigate to frontend and start dev server
cd frontend
npm install
npm run dev
```
- **Web Dashboard**: [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 👥 Default Seeded User Accounts

The database automatically seeds 3 pre-configured role-based test accounts on first launch:

| Account Type | Email | Password | Role | Permissions |
|--------------|-------|----------|------|-------------|
| **Administrator** | `admin@truthlens.local` | `AdminPass123!` | `ADMIN` | System status, user RBAC role assignment, full audit logs |
| **Publisher** | `publisher@truthlens.local` | `PublisherPass123!` | `PUBLISHER` | Media asset registration, ECDSA signing, provenance registry |
| **Analyst / User** | `user@truthlens.local` | `UserPass123!` | `USER` | Media upload, dual-layer forensic verification, report history |

---

## 🛡️ Trust Assessment Engine (Deterministic 6-State Policy)

The Trust Engine treats probabilistic AI detection and mathematical cryptographic proofs as decoupled signals:

| Verdict Badge | Cryptographic Integrity | Digital Provenance | AI Detection | Explanation |
|---------------|-------------------------|--------------------|--------------|-------------|
| **`VERIFIED_TRUSTED`** | Match | Valid ECDSA Signature | Real / Consistent | Asset provenance verified against publisher registry with unchanged bitstream. |
| **`INTEGRITY_MISMATCH`** | Mismatch | Known Asset ID | Any | Critical tamper alert: SHA-256 hash changed from registered baseline. |
| **`INVALID_SIGNATURE`** | Any | Failed ECDSA Math | Any | Digital signature fails cryptographic validation with publisher's public key. |
| **`SUSPICIOUS_AI`** | No Registry | Unregistered | Synthetic Artifacts | Media exhibits statistical generation artifacts; no authoritative publisher record. |
| **`VERIFIED_TRUSTED_WITH_AI_CONFLICT`** | Match | Valid ECDSA Signature | Synthetic Artifacts | Authoritative publisher confirmed, but AI flags synthetic markers (e.g. CGI/AI-assisted graphic). |
| **`INCONCLUSIVE`** | No Registry | Unregistered | Borderline / Disagreement | Unregistered media with ambiguous cues or conflicting multi-model predictions. |

---

## 🧪 Automated Testing

TruthLens includes tests across every subsystem:

```powershell
# Run the complete test suite (E2E + backend + security)
python -m pytest tests/test_audit_e2e.py backend/tests/ member2_security/tests/ -v

# Run AI inference detector tests
python -m pytest truthlens-ai/tests/ -v

# Run multi-model routing verification
python scripts/test_model_routing_e2e.py
```

### Test Coverage Highlights
- ✅ **Cryptographic Decoupling**: Valid ECDSA signatures cannot be overridden by AI predictions.
- ✅ **Tamper Detection**: Single-byte changes trigger immediate `INTEGRITY_MISMATCH`.
- ✅ **Multi-Model Routing**: `current` (ViT) and `smaug` (EmbeddingGemma-2) invoke distinct models; disagreement returns `INCONCLUSIVE (MODEL DISAGREEMENT)`.
- ✅ **RBAC Enforcement**: Administrative endpoints reject unauthorized user tokens with `403 Forbidden`.
- ✅ **Audit Trail**: All authentication and verification events are recorded with IP, timestamp, and actor details.
