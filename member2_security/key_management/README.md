# TruthLens Key Management & Cryptographic Storage Architecture
**Member 2:** Cryptography & Information Security  
**Module:** `member2_security.key_management`

---

## 1. Overview & Security Principles

The TruthLens key management subsystem is responsible for generating, serializing, storing, and rotating the cryptographic keys used across the system:
1. **ECDSA NIST P-256 (SECP256R1) Key Pairs:** Used for signing and verifying digital provenance records.
2. **AES-256 Symmetric Keys:** 256-bit keys used for authenticated envelope encryption (`AES-256-GCM`).

### Core Security Mandates:
- **Zero In-Source Secrets:** Secret keys, passwords, and private keys must **NEVER** be committed to Git or hardcoded in source code.
- **Fail Closed:** If a required key is missing, TruthLens must fail loudly and safely at startup. **NEVER silently generate a new signing key on restart**, as this would invalidate verification of previously registered records.
- **Irrecoverability of Lost Encryption Keys:** AES-256-GCM provides no backdoors or key-recovery mechanisms. **Loss of an encryption key renders all associated ciphertexts permanently unreadable.**
- **Private Key Isolation:** Private keys are kept strictly in memory or in permission-restricted files (`chmod 0600` on POSIX systems), stored outside public web roots.

---

## 2. Key Lifecycle & Rotation Architecture

TruthLens employs a structured key lifecycle managed by `KeyRegistry`:

```
 [Generate Key Pair]
         │
         ▼
     [ACTIVE] ───► Currently authorized to sign new provenance records
         │
         │ (Key Rotation Event)
         ▼
    [RETIRED] ───► Historical records remain VERIFIABLE & TRUSTED;
         │         forbidden for signing new records
         │
         │ (Compromise / Revocation Event)
         ▼
    [REVOKED] ───► Immediately UNTRUSTED; all records referencing
                   this key report REVOKED trust status
```

### Key Rotation without Invalidation
When an active key `tl-key-v1` is rotated to `tl-key-v2`:
1. `tl-key-v1` transitions to `RETIRED`.
2. New media registrations are signed with `tl-key-v2` (`ACTIVE`).
3. Historical records previously signed with `tl-key-v1` continue to verify as **mathematically valid and TRUSTED**.

---

## 3. Local Development Setup

### Generating Local Keys
To generate a local development ECDSA signing key pair with passphrase protection:

```python
from member2_security.key_management import (
    generate_ecdsa_key_pair,
    save_key_pair_to_files,
    generate_aes_key,
)

# 1. Generate ECDSA P-256 key pair with passphrase protection
priv_pem, pub_pem = generate_ecdsa_key_pair(password="your-secure-local-passphrase")
save_key_pair_to_files(
    private_pem=priv_pem,
    public_pem=pub_pem,
    private_path="secrets/truthlens_signing_private.pem",
    public_path="secrets/truthlens_signing_public.pem",
    restrict_permissions=True  # Applies chmod 0600 on UNIX
)

# 2. Generate a 256-bit AES Master Key (Base64-encoded)
import base64
aes_key = generate_aes_key(32)
aes_b64 = base64.b64encode(aes_key).decode("ascii")
print("Base64 AES Key for .env:", aes_b64)
```

### Local Permissions
On POSIX environments (Linux / macOS), ensure private key files have owner-only permissions:
```bash
chmod 600 secrets/truthlens_signing_private.pem
chmod 644 secrets/truthlens_signing_public.pem
```

---

## 4. Production Deployment Guidance (Cloud KMS & HSM)

Environment variables and local files are acceptable for local development and testing, but **production deployments should use dedicated Key Management Services (KMS) or Hardware Security Modules (HSM):**

| Platform | Recommended Service | Architecture |
| :--- | :--- | :--- |
| **AWS** | AWS KMS / CloudHSM | Store ECDSA P-256 asymmetric signing keys in KMS. Call `kms.sign()` directly via IAM role; the private key never leaves the HSM hardware boundary. |
| **Google Cloud** | Cloud KMS / Cloud HSM | Asymmetric signing keys (`EC_SIGN_P256_SHA256`). App uses Workload Identity to sign canonical digests via Cloud KMS API. |
| **Azure** | Azure Key Vault / Managed HSM | Store keys in Key Vault HSM backing. Authenticate using Managed Identity. |
| **Self-Hosted** | HashiCorp Vault | Transit Secrets Engine configured with `ecdsa-p256` key type. |

### Envelope Encryption in Production:
For AES-256-GCM data encryption:
1. Generate a Master Key (KEK) inside KMS.
2. For each dataset or tenant, request a fresh Data Encryption Key (DEK) via `kms.generate_data_key()`.
3. Encrypt data locally using `member2_security.crypto.encrypt_bytes` with the plaintext DEK.
4. Securely erase the plaintext DEK from RAM and store the encrypted DEK inside the envelope's metadata.
