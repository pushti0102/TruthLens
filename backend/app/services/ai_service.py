import sys
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from backend.app.config import settings

# Ensure truthlens-ai is in sys.path
ai_root = settings.PROJECT_ROOT / "truthlens-ai"
if str(ai_root) not in sys.path:
    sys.path.insert(0, str(ai_root))


class AIService:
    """
    Safe wrapper around Member 1's AI Detection module.
    Crucial: Must NEVER fail the verification workflow if AI inference is unavailable
    or weights are missing.
    """

    @classmethod
    def is_available(cls) -> Tuple[bool, str]:
        try:
            from src.detector import TruthLensDetector, ModelNotAvailableError
            return True, "Model detector interface loaded."
        except Exception as e:
            return False, str(e)

    @classmethod
    def analyze_image(cls, image_path: Path) -> Dict[str, Any]:
        """
        Run AI inference safely.
        Returns a dictionary conforming to the structured output contract.
        """
        try:
            from src.inference import run_inference
            result = run_inference(image_path)

            if result.get("status") == "success":
                return {
                    "status": "SUCCESS",
                    "label": result.get("label"),
                    "confidence": float(result.get("confidence", 0.0)),
                    "raw_scores": result.get("raw_scores"),
                    "model_id": result.get("model_id"),
                    "inference_ms": float(result.get("inference_ms", 0.0)),
                    "ai_likelihood": result.get("ai_likelihood", "inconclusive"),
                    "warning": result.get("warning"),
                    "document_domain_warning": result.get("document_domain_warning"),
                    "domain_note": result.get("domain_note"),
                    "message": "AI visual forensic analysis completed.",
                }
            else:
                error_type = result.get("error_type", "unknown_error")
                error_msg = result.get("error", "AI analysis encountered an error.")
                return {
                    "status": "UNAVAILABLE" if "model_not_available" in error_type else "ERROR",
                    "label": None,
                    "confidence": None,
                    "raw_scores": None,
                    "model_id": "dima806/ai_vs_real_image_detection",
                    "inference_ms": 0.0,
                    "ai_likelihood": "inconclusive",
                    "warning": "AI analysis was not performed.",
                    "document_domain_warning": None,
                    "domain_note": None,
                    "message": f"AI model unavailable ({error_type}): {error_msg}. Independent cryptographic checks remain active.",
                }

        except Exception as exc:
            # Fallback if transformers, safetensors, or model dependencies are missing
            return {
                "status": "UNAVAILABLE",
                "label": None,
                "confidence": None,
                "raw_scores": None,
                "model_id": "dima806/ai_vs_real_image_detection",
                "inference_ms": 0.0,
                "ai_likelihood": "inconclusive",
                "warning": "AI analysis unavailable; system operates on cryptographic signals.",
                "document_domain_warning": None,
                "domain_note": None,
                "message": f"AI analysis offline ({exc.__class__.__name__}). Cryptographic provenance and SHA-256 integrity checks continue.",
            }
