import os
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.security.keys import crypto_manager
from backend.app.services.ai_service import AIService

router = APIRouter(prefix="/api", tags=["System & Health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TruthLens Application Backend",
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENV,
        "storage_writable": os.access(settings.STORAGE_DIR, os.W_OK),
    }


@router.get("/health/ai")
def ai_health():
    ready, info = AIService.is_available()
    return {
        "model_id": "dima806/ai_vs_real_image_detection",
        "architecture": "Vision Transformer (ViT-Base)",
        "ready": ready,
        "detail": info,
        "dataset_scope": "CIFAKE (CIFAR-10 real + Stable Diffusion 1.4 synthetic)",
        "limitation_note": "Visual statistical resemblance model only; does not provide legal proof of authenticity.",
    }


@router.get("/health/crypto")
def crypto_health():
    reg = crypto_manager.get_registry()
    active_key = reg.get_key_record(crypto_manager.active_key_id)
    return {
        "crypto_module": "member2_security",
        "hashing_algorithm": "SHA-256",
        "signature_algorithm": "ECDSA-P256-SHA256",
        "encryption_algorithm": "AES-256-GCM",
        "active_key_id": crypto_manager.active_key_id,
        "active_key_registered": active_key is not None,
        "key_lifecycle_status": active_key.status.value if active_key else "MISSING",
        "total_registry_keys": len(reg._keys),
    }
