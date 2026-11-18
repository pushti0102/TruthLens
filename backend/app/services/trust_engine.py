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
        if ai_status == "SUCCESS":
            confidence_pct = round((ai.get("confidence") or 0.0) * 100, 1)
            doc_warning = ai.get("document_domain_warning")

            if ai_label == "REAL":
                return {
                    "status": "INCONCLUSIVE",
                    "score": 70,
                    "badge": "Visual Cues Photographic (Unregistered)",
                    "badge_color": "blue",
                    "explanation": (
                        f"No cryptographic provenance record registered. The Vision Transformer detector found "
                        f"authentic photographic characteristics ({confidence_pct}% confidence). "
                        "Because the file has not been cryptographically signed by a registered publisher, "
                        "origin non-repudiation and chain of custody cannot be mathematically guaranteed."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "LOW"},
                }

            # If AI model flagged AI_GENERATED, check if document/camera aspect ratio warning was triggered
            if doc_warning:
                return {
                    "status": "INCONCLUSIVE",
                    "score": 50,
                    "badge": "Inconclusive (Domain / Geometry Advisory)",
                    "badge_color": "slate",
                    "explanation": (
                        f"No registered cryptographic baseline found. Although the Vision Transformer indicated AI likelihood ({confidence_pct}%), "
                        "the image dimensions trigger a document/camera format advisory where CIFAKE-trained models frequently produce "
                        "false-positive detections. Rely on cryptographic provenance registration for definitive verification."
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
                        f"likelihood of synthetic or AI-generated imagery ({confidence_pct}% confidence). Evaluate with caution."
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
                        f"synthetic patterns ({confidence_pct}% confidence)."
                    ),
                    "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "MODERATE"},
                }

        # AI is UNAVAILABLE or offline:
        return {
            "status": "INCONCLUSIVE",
            "score": 50,
            "badge": "Unregistered (AI Offline)",
            "badge_color": "slate",
            "explanation": (
                "No registered cryptographic reference baseline was found in the database. "
                "AI visual forensics is currently offline or unconfigured. Cryptographic integrity "
                "cannot be proven without an established baseline."
            ),
            "signals_summary": {"integrity": "NO_BASELINE", "signature": "MISSING", "ai_risk": "UNKNOWN"},
        }

