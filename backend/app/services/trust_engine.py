from typing import Dict, Any


class TrustAssessmentEngine:
    """
    Transparent, multi-signal trust synthesis engine.
    Derives explainable verdicts without hiding conflicts or pretending certainty.
    """

    @classmethod
    def evaluate(
        cls,
        integrity: Dict[str, Any],
        signature: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> Dict[str, Any]:
        integ_status = integrity.get("status")  # MATCH, MISMATCH, NO_REFERENCE, INVALID_INPUT
        sig_status = signature.get("status")    # VALID, INVALID, MISSING, MALFORMED
        key_trust = signature.get("key_trust_status")  # TRUSTED, REVOKED, EXPIRED, UNKNOWN
        ai_status = ai.get("status")            # SUCCESS, UNAVAILABLE, ERROR
        ai_label = ai.get("label")              # REAL, AI_GENERATED
        ai_likelihood = ai.get("ai_likelihood", "inconclusive")

        # ── Case 1: Cryptographically Verified & Trusted Baseline ──────────
        if integ_status == "MATCH" and sig_status == "VALID" and key_trust == "TRUSTED":
            # If AI is available and flags high AI, note the conflict!
            if ai_status == "SUCCESS" and ai_label == "AI_GENERATED" and ai_likelihood == "high":
                return {
                    "status": "VERIFIED_TRUSTED_WITH_AI_CONFLICT",
                    "score": 85,
                    "badge": "Cryptographic Match (AI Warning)",
                    "badge_color": "cyan",
                    "explanation": (
                        "File byte-integrity matches a trusted signed provenance record. "
                        "However, the AI forensic detector flags synthetic surface artifacts. "
                        "The cryptographic provenance confirms the registered bytes have not changed, "
                        "but the original media itself may have been synthetically generated before registration."
                    ),
                    "signals_summary": {"integrity": "MATCH", "signature": "TRUSTED", "ai_risk": "HIGH"},
                }
            return {
                "status": "VERIFIED_TRUSTED",
                "score": 98,
                "badge": "Cryptographically Verified",
                "badge_color": "emerald",
                "explanation": (
                    "File matches registered reference digest byte-for-byte and bears a mathematically "
                    "valid ECDSA digital signature from an active, trusted authority."
                ),
                "signals_summary": {"integrity": "MATCH", "signature": "TRUSTED", "ai_risk": "LOW"},
            }

        # ── Case 2: Byte-Level Integrity Mismatch (Tampered / Re-saved) ────
        if integ_status == "MISMATCH":
            return {
                "status": "INTEGRITY_MISMATCH",
                "score": 25,
                "badge": "Integrity Mismatch (Tampered)",
                "badge_color": "rose",
                "explanation": (
                    "File bytes differ from the registered cryptographic reference digest. "
                    "The media has diverged due to editing, pixel manipulation, compression transcoding, "
                    "or file corruption since initial provenance registration."
                ),
                "signals_summary": {"integrity": "MISMATCH", "signature": sig_status, "ai_risk": ai_likelihood},
            }

        # ── Case 3: Invalid Signature or Untrusted / Revoked Key ────────────
        if sig_status in ("INVALID", "MALFORMED") or key_trust in ("REVOKED", "EXPIRED"):
            return {
                "status": "INVALID_SIGNATURE",
                "score": 15,
                "badge": "Cryptographic Verification Failed",
                "badge_color": "rose",
                "explanation": (
                    "Provenance record exists, but digital signature verification failed mathematically "
                    "or the authority signing key is REVOKED or EXPIRED."
                ),
                "signals_summary": {"integrity": integ_status, "signature": "UNTRUSTED", "ai_risk": ai_likelihood},
            }

        # ── Case 4: Unregistered / No Reference Baseline ────────────────────
        # (integ_status == "NO_REFERENCE")
        model_name = ai.get("model_name") or ai.get("architecture") or "AI Forensic Detector"

        if ai_status == "SUCCESS":
            confidence_pct = round((ai.get("confidence") or 0.0) * 100, 1)
            doc_warning = ai.get("document_domain_warning")

            # Check for inter-model disagreement across prior runs on the same file
            if ai.get("model_disagreement"):
                return {
                    "status": "INCONCLUSIVE",
                    "score": 50,
                    "badge": "Inconclusive (Model Disagreement)",
                    "badge_color": "slate",
                    "explanation": (
                        f"Forensic AI models disagree on this media. {ai.get('disagreement_details', '')} "
                        "When different detection architectures reach contradictory conclusions on an unregistered file, "
                        "probabilistic scores cannot be considered definitive. Cryptographic provenance is unavailable, "
                        "and the overall assessment is INCONCLUSIVE."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "MODEL_DISAGREEMENT"},
                }

            if ai_likelihood == "inconclusive":
                return {
                    "status": "INCONCLUSIVE",
                    "score": 50,
                    "badge": "Inconclusive (Uncertain AI Signal)",
                    "badge_color": "slate",
                    "explanation": (
                        f"No registered cryptographic provenance baseline found. The {model_name} prediction ({confidence_pct}%) "
                        "falls within an ambiguous decision boundary or reflects insufficient evidence. Raw softmax scores "
                        "are uncalibrated heuristics and must not be treated as posterior probabilities. "
                        "Missing provenance is reported as unavailable, not evidence of manipulation."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "INCONCLUSIVE"},
                }

            if ai_label == "REAL":
                return {
                    "status": "INCONCLUSIVE",
                    "score": 70,
                    "badge": "Visual Cues Photographic (Unregistered)",
                    "badge_color": "blue",
                    "explanation": (
                        f"No cryptographic provenance record registered. The {model_name} found "
                        f"photographic characteristics ({confidence_pct}% confidence). "
                        "Because the file has not been cryptographically signed by a registered publisher, "
                        "provenance is unavailable and origin chain of custody cannot be mathematically guaranteed. "
                        "Unregistered status is not proof of fraud."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "LOW"},
                }

            # If AI model flagged AI_GENERATED, check if document/camera aspect ratio warning was triggered
            if doc_warning:
                return {
                    "status": "INCONCLUSIVE",
                    "score": 50,
                    "badge": "Inconclusive (Document Advisory)",
                    "badge_color": "slate",
                    "explanation": (
                        f"No registered cryptographic baseline found. Although the {model_name} indicated AI likelihood ({confidence_pct}%), "
                        "the image exhibits document or credential characteristics where models have higher false-positive risk. "
                        "Missing provenance is unavailable; independent cryptographic registration is required for definitive verification."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "INCONCLUSIVE_DOMAIN"},
                }

            if ai_label == "AI_GENERATED" and ai_likelihood == "high":
                return {
                    "status": "SUSPICIOUS_AI",
                    "score": 30,
                    "badge": "AI-Generated Media Detected",
                    "badge_color": "amber",
                    "explanation": (
                        f"No registered cryptographic baseline found. AI visual forensics indicates a high "
                        f"likelihood of synthetic or AI-generated imagery ({confidence_pct}% confidence). "
                        "Note: Raw AI detection scores are pattern heuristics and do not provide legal proof of origin."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "HIGH"},
                }
            elif ai_label == "AI_GENERATED":
                return {
                    "status": "SUSPICIOUS_AI",
                    "score": 40,
                    "badge": "Possible Synthetic Media",
                    "badge_color": "amber",
                    "explanation": (
                        f"No registered cryptographic baseline found. AI visual forensics detected moderate "
                        f"synthetic patterns ({confidence_pct}% confidence). Missing provenance is reported as unavailable."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "MODERATE"},
                }

        # AI is UNAVAILABLE or offline:
        return {
            "status": "INCONCLUSIVE",
            "score": 50,
            "badge": "Unregistered (Provenance Unavailable)",
            "badge_color": "slate",
            "explanation": (
                "No registered cryptographic reference baseline was found in the database. "
                "AI visual forensics is currently offline or unconfigured. "
                "Missing provenance is reported as unavailable, not automatically fraudulent."
            ),
            "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "UNKNOWN"},
        }

