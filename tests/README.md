# TruthLens System Integration Tests

This directory houses the comprehensive end-to-end integration and system-audit test suite for TruthLens.

---

## Test Suites

| Path | Focus Area | Command |
|------|------------|---------|
| `test_audit_e2e.py` | Full multi-member integration: AI inference routing, SHA-256 integrity checks, ECDSA signing & verification, AES-GCM encryption, RBAC authorization, and Trust Engine policy. | `pytest tests/test_audit_e2e.py` |
| `backend/tests/` | FastAPI routers, JWT authentication, user management, and media verification endpoints. | `pytest backend/tests/` |
| `member2_security/tests/` | Cryptographic primitives (hashing, ECDSA signatures, AES-GCM encryption, rate limiting, upload validation). | `pytest member2_security/tests/` |
| `truthlens-ai/tests/` | AI vision detector, preprocessing, label mapping, and model caching. | `pytest truthlens-ai/tests/` |

---

## Running the Complete Suite

To run all project tests in one command:
```bash
pytest tests/test_audit_e2e.py backend/tests/ member2_security/tests/
```
