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
    def analyze_image(
        cls,
        image_path: Path,
        model: Optional[str] = "current",
        prior_predictions: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Run AI inference safely with multi-model support and disagreement detection.
        Returns a dictionary conforming to the structured output contract.

        Parameters
        ----------
        image_path : Path
            Path to the image to analyze.
        model : str, optional
            Model selector shortcut ('current' or 'smaug'). Defaults to 'current'.
        prior_predictions : list, optional
            Prior evaluations on the exact same file digest to detect inter-model conflicts.
        """
        model_name = (model or "current").strip().lower()
        from src.detector import resolve_model_info
        model_info = resolve_model_info(model_name)
        target_model_id = model_info["model_id"]

        try:
            from src.inference import run_inference
            result = run_inference(image_path, model=model_name)

            if result.get("status") == "success":
                label = result.get("label")
                outcome = result.get("outcome", label)
                model_disagreement = False
                disagreement_details = None

                # Check if a prior model produced a conflicting prediction on the same image
                if prior_predictions:
                    for prev in prior_predictions:
                        prev_label = prev.get("label")
                        prev_model = prev.get("model_id") or "prior model"
                        if prev_label and prev_label != label:
                            model_disagreement = True
                            outcome = "INCONCLUSIVE (MODEL DISAGREEMENT)"
                            disagreement_details = (
                                f"Model Disagreement: Current model ({model_info['name']}) predicted '{label}', "
                                f"whereas a prior evaluation using {prev_model} predicted '{prev_label}' on the exact same media."
                            )
                            break

                arch_str = result.get("architecture") or model_info.get("architecture_name") or model_info.get("architecture", "AI Forensic Detector")

                return {
                    "status": "SUCCESS",
                    "label": label,
                    "outcome": outcome,
                    "confidence": float(result.get("confidence", 0.0)),
                    "raw_scores": result.get("raw_scores"),
                    "model_id": result.get("model_id", target_model_id),
                    "model_name": result.get("model_name", model_info.get("name")),
                    "architecture": arch_str,
                    "inference_ms": float(result.get("inference_ms", 0.0)),
                    "ai_likelihood": result.get("ai_likelihood", "inconclusive"),
                    "warning": result.get("warning"),
                    "calibration_note": result.get("calibration_note"),
                    "document_domain_warning": result.get("document_domain_warning"),
                    "domain_note": result.get("domain_note"),
                    "model_disagreement": model_disagreement,
                    "disagreement_details": disagreement_details,
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
                    "model_id": result.get("model_id") or target_model_id,
                    "model_name": model_info.get("name"),
                    "architecture": model_info.get("architecture_name", model_info.get("architecture", "AI Forensic Detector")),
                    "inference_ms": 0.0,
                    "ai_likelihood": "inconclusive",
                    "warning": "AI analysis was not performed.",
                    "document_domain_warning": None,
                    "domain_note": None,
                    "model_disagreement": False,
                    "disagreement_details": None,
                    "message": f"AI model unavailable ({error_type}): {error_msg}. Independent cryptographic checks remain active.",
                }

        except Exception as exc:
            # Fallback if transformers, safetensors, or model dependencies are missing
            return {
                "status": "UNAVAILABLE",
                "label": None,
                "confidence": None,
                "raw_scores": None,
                "model_id": target_model_id,
                "model_name": model_info.get("name"),
                "architecture": model_info.get("architecture_name", model_info.get("architecture", "AI Forensic Detector")),
                "inference_ms": 0.0,
                "ai_likelihood": "inconclusive",
                "warning": "AI analysis unavailable; system operates on cryptographic signals.",
                "document_domain_warning": None,
                "domain_note": None,
                "model_disagreement": False,
                "disagreement_details": None,
                "message": f"AI analysis offline ({exc.__class__.__name__}). Cryptographic provenance and SHA-256 integrity checks continue.",
            }
