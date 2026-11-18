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
    try:
        from src.detector import resolve_model_info, DEFAULT_MODEL_KEY, MODEL_REGISTRY
        default_info = resolve_model_info(DEFAULT_MODEL_KEY)
        model_id = default_info["model_id"]
        architecture = default_info.get("architecture_name", default_info.get("architecture"))
        available = [
            {
                "key": k,
                "name": v.get("name"),
                "model_id": v["model_id"],
                "architecture": v.get("architecture_name", v.get("architecture")),
            }
            for k, v in MODEL_REGISTRY.items()
        ]
    except Exception:
        model_id = "default_ai_detector"
        architecture = "AI Transformer"
        available = []

    return {
        "model_id": model_id,
        "architecture": architecture,
        "ready": ready,
        "detail": info,
        "available_models": available,
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
