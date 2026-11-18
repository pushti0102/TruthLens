# Security Policy & Cryptographic Specifications — TruthLens

## 1. Key Management & Provenance Trust

TruthLens uses standard public-key cryptography to ensure non-repudiation and authenticity of digital assets:

- **Algorithm:** ECDSA over SECP256R1 (`prime256v1` / P-256) with SHA-256.
- **Key Storage:** Local development keys are securely generated and isolated in `secrets/` with strict directory permissions.
- **Registry:** `trusted_keys_registry.json` maintains the list of recognized publisher public keys, their operational status, and valid timestamps.
- **Integrity Validation:** When an asset is registered, its canonical SHA-256 digest is signed by the publisher's private key. Subsequent verification recomputes the SHA-256 digest and verifies the digital signature using the corresponding registered public key.

## 2. Authentication & Authorization

- **Password Storage:** Uses state-of-the-art **Argon2id** password hashing (`argon2-cffi`), which is resistant to GPU-based brute force and side-channel timing attacks.
- **Token Security:** Short-lived JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
- **Role-Based Access Control (RBAC):** Every endpoint enforces strict role validation (`ADMIN`, `PUBLISHER`, `USER`) via FastAPI dependencies.

## 3. Defense Against Media Forgery & Tampering

- **Bitwise Tampering Detection:** Any single-pixel modification to an image alters its cryptographic SHA-256 hash, causing immediate `INTEGRITY_MISMATCH` verdicts.
- **Transparent Trust Model:** The trust engine does not use hidden heuristic weights. Its deterministic rule engine guarantees explainable, reproducible verdicts for academic audits and legal forensics.

