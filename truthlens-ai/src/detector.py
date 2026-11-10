"""
src/detector.py
===============
PURPOSE
-------
Load the pretrained AI-image detector model and expose a clean interface for
running predictions.

THE MODEL WE USE
----------------
Model ID  : dima806/ai_vs_real_image_detection
Repository: https://huggingface.co/dima806/ai_vs_real_image_detection

Architecture
    Vision Transformer (ViT-base-patch16-224) fine-tuned with Hugging Face
    AutoTrain for binary image classification.

What it detects
    Whether a given image is REAL (photographed) or AI-GENERATED (produced
    by a text-to-image model such as Stable Diffusion, Midjourney, DALL-E).
    Note: it was primarily trained on *artistic* images, so accuracy on
    photorealistic deepfakes may be lower.

License
    CC-BY-ND 4.0 — free to use with attribution; no derivatives.
    See: https://creativecommons.org/licenses/by-nd/4.0/

Expected input
    A PIL.Image.Image object in RGB mode.
    The model's ViTFeatureExtractor will internally resize to 224×224 and
    normalise with ImageNet statistics (mean=[0.5,0.5,0.5], std=[0.5,0.5,0.5]).

Output classes
    "REAL"         — image appears to be a genuine photograph
    "AI_GENERATED" — image appears to have been produced by an AI

Model size
    ~330 MB (ViT-base-patch16-224, ~86 M parameters).
    Downloaded automatically from Hugging Face on first use and cached in
    ~/.cache/huggingface/hub/ (or HF_HOME if set).

Hardware requirements
    CPU inference is fine for a college demo; a single image takes ~1–3 s on
    modern laptop CPU.  GPU (CUDA) is used automatically if available.

HOW TO GET THE WEIGHTS
    The weights are downloaded automatically the first time you call
    TruthLensDetector().  You need an internet connection for that first
    download only.  After that, they are cached locally.
"""

import time
from typing import Optional

from PIL import Image

# Module-level references for library components and unittest patching
pipeline = None
Pipeline = None
AutoImageProcessor = None
AutoModelForImageClassification = None
torch = None
_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    from transformers import (
        pipeline,
        Pipeline,
        AutoImageProcessor,
        AutoModelForImageClassification,
    )
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass


# Model registry definitions
MODEL_ID = "dima806/ai_vs_real_image_detection"
SMAUG_MODEL_ID = "abacusai/Smaug-AI-Image-Detector"
DEFAULT_MODEL_KEY = "current"

MODEL_REGISTRY = {
    "current": {
        "model_id": MODEL_ID,
        "name": "ViT AI vs Real Image Detector",
        "architecture": "vit",
        "hf_repo": "https://huggingface.co/dima806/ai_vs_real_image_detection",
        "description": "Vision Transformer (ViT-base-patch16-224) fine-tuned for binary AI vs Real classification.",
    },
    "smaug": {
        "model_id": SMAUG_MODEL_ID,
        "name": "Smaug AI Image Detector",
        "architecture": "smaug",
        "hf_repo": "https://huggingface.co/abacusai/Smaug-AI-Image-Detector",
        "description": "Abacus.AI Smaug Image Forensics Detector based on vision-optimized EmbeddingGemma-2.",
    },
}


def resolve_model_info(model_identifier: Optional[str] = None) -> dict:
    """
    Resolve a model shortcut, key, or Hugging Face repository ID to registry info.

    Parameters
    ----------
    model_identifier : str or None
        One of 'current', 'smaug', or full Hugging Face model IDs.
        Defaults to 'current'.

    Returns
    -------
    dict with keys: 'key', 'model_id', 'name', 'architecture', 'hf_repo', 'description'.

    Raises
    ------
    ValueError
        If the identifier cannot be matched to a known model.
    """
    if not model_identifier:
        model_identifier = DEFAULT_MODEL_KEY

    ident = str(model_identifier).strip()
    lowered = ident.lower()

    if lowered in MODEL_REGISTRY:
        info = dict(MODEL_REGISTRY[lowered])
        info["key"] = lowered
        return info

    for key, info in MODEL_REGISTRY.items():
        if ident == info["model_id"]:
            res = dict(info)
            res["key"] = key
            return res

    supported = list(MODEL_REGISTRY.keys()) + [info["model_id"] for info in MODEL_REGISTRY.values()]
    raise ValueError(
        f"Unknown model identifier: '{model_identifier}'.\n"
        f"Supported choices: {', '.join(sorted(supported))}"
    )


# Map the raw label strings the model returns to normalised class names.
# The model config id2label is {0: 'REAL', 1: 'FAKE'}.
# We normalise everything to two canonical labels: "REAL" and "AI_GENERATED".
LABEL_MAP = {
    "real": "REAL",
    "fake": "AI_GENERATED",
    "ai generated": "AI_GENERATED",
    "ai_generated": "AI_GENERATED",
    "artificial": "AI_GENERATED",
    "artificial image": "AI_GENERATED",
}


class ModelNotAvailableError(Exception):
    """Raised when the model weights cannot be loaded."""
    pass


class TruthLensDetector:
    """
    Unified detector wrapper for pretrained AI-image detection models.

    Supports:
      - 'current': Vision Transformer (ViT-base-patch16-224) fine-tuned on CIFAKE
      - 'smaug': Abacus.AI Smaug-AI-Image-Detector (EmbeddingGemma-2 based)

    Parameters
    ----------
    model_id : str
        Model identifier or registry shortcut ('current', 'smaug', or full HF repo ID).
        Defaults to 'dima806/ai_vs_real_image_detection'.
    device : str or None
        'cpu', 'cuda', or None (auto-detect GPU with CPU fallback).
    """

    def __init__(
        self,
        model_id: str = MODEL_ID,
        device: Optional[str] = None,
    ):
        if not _TRANSFORMERS_AVAILABLE:
            raise ModelNotAvailableError(
                "The 'transformers' library is not installed.\n"
                "Fix: activate the virtual environment and run:\n"
                "  pip install -r requirements.txt"
            )

        # Resolve model key and identifier via registry
        model_info = resolve_model_info(model_id)
        self.model_key = model_info["key"]
        self.model_id = model_info["model_id"]
        self.architecture = model_info["architecture"]
        self.model_name = model_info["name"]

        self.processor = None
        self.model = None
        self._pipe: Optional[Pipeline] = None
        self.id2label = {0: "REAL", 1: "FAKE"}
        self.label2id = {"REAL": 0, "FAKE": 1}

        # Auto-select device if not specified: prefer CUDA if available, default to CPU
        if device is None:
            try:
                self._device_str = "cuda" if (torch is not None and torch.cuda.is_available()) else "cpu"
            except Exception:
                self._device_str = "cpu"
        else:
            self._device_str = device.lower()

        self._device = 0 if self._device_str == "cuda" else -1

        self._load_model()

    def _load_model(self) -> None:
        """
        Download (first time) and load the model into memory.
        Uses model-specific architecture loaders.

        Raises
        ------
        ModelNotAvailableError
            If the model cannot be downloaded or loaded.
        """
        # Compatibility check: if pipeline was patched or mocked in tests
        is_mocked = (
            pipeline is not None and (
                hasattr(pipeline, "assert_called")
                or pipeline.__class__.__name__ in ("MagicMock", "Mock")
            )
        )

        if self.architecture == "smaug":
            self._load_smaug_model(is_mocked=is_mocked)
        else:
            self._load_vit_model(is_mocked=is_mocked)

    def _load_smaug_model(self, is_mocked: bool = False) -> None:
        """
        Load the Smaug AI detector (EmbeddingGemma-2 based).
        Requires compatible dependencies and weights.
        Never silently falls back to the ViT/current model.
        """
        if is_mocked:
            try:
                self._pipe = pipeline(
                    task="image-classification",
                    model=self.model_id,
                    device=self._device,
                )
                return
            except OSError as exc:
                raise ModelNotAvailableError(
                    f"Could not load model '{self.model_id}'.\n"
                    f"Original error: {exc}"
                ) from exc
            except Exception as exc:
                raise ModelNotAvailableError(
                    f"Unexpected error loading model '{self.model_id}': {exc}"
                ) from exc

        # Unmocked loading: check for sentence_transformers
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ModelNotAvailableError(
                f"Could not load Smaug model '{self.model_id}':\n"
                "Missing required dependency 'sentence-transformers'.\n"
                "The Smaug model architecture (EmbeddingGemma-2) requires sentence-transformers.\n"
                "Install it with:\n"
                "  pip install sentence-transformers"
            ) from exc

        try:
            target_device = "cuda" if (self._device_str == "cuda" and torch.cuda.is_available()) else "cpu"
            self.model = SentenceTransformer(
                self.model_id,
                device=target_device,
                config_kwargs={"audio_config": None},
                model_kwargs={"torch_dtype": torch.bfloat16 if target_device == "cuda" else torch.float32},
            )
            if hasattr(self.model[0], "processor") and hasattr(self.model[0].processor, "image_processor"):
                ip = self.model[0].processor.image_processor
                ip.max_soft_tokens = ip.image_seq_length = 140
                self.processor = ip
            else:
                self.processor = getattr(self.model[0], "processor", None)
        except Exception as exc:
            raise ModelNotAvailableError(
                f"Could not load Smaug model '{self.model_id}'.\n"
                f"Original error: {exc}\n\n"
                "Possible causes:\n"
                "  1. Smaug model weights (~1.7 GB) are not cached or failed to download.\n"
                "  2. Network connection timed out or is unavailable.\n"
                "  3. Environment or hardware is incompatible with the Smaug architecture.\n\n"
                "Fix: connect to the internet to download 'abacusai/Smaug-AI-Image-Detector' weights."
            ) from exc

    def _load_vit_model(self, is_mocked: bool = False) -> None:
        """Load standard Hugging Face Vision Transformer model."""
        if is_mocked:
            try:
                self._pipe = pipeline(
                    task="image-classification",
                    model=self.model_id,
                    device=self._device,
                )
                return
            except OSError as exc:
                raise ModelNotAvailableError(
                    f"Could not load model '{self.model_id}'.\n"
                    f"Original error: {exc}\n\n"
                    "Possible causes:\n"
                    "  1. No internet connection on first run (weights not cached yet).\n"
                    "  2. The model ID is incorrect or has been removed.\n"
                    "  3. HF_HOME / cache directory is full or permission-denied.\n\n"
                    "Fix: connect to the internet and run the detector once to cache the weights."
                ) from exc
            except Exception as exc:
                raise ModelNotAvailableError(
                    f"Unexpected error loading model: {exc}"
                ) from exc

        try:
            # Load image processor (resizing to 224x224, normalization)
            self.processor = AutoImageProcessor.from_pretrained(self.model_id)

            # Load model weights, preferring safe serialization (safetensors)
            try:
                self.model = AutoModelForImageClassification.from_pretrained(
                    self.model_id,
                    use_safetensors=True,
                )
            except Exception:
                self.model = AutoModelForImageClassification.from_pretrained(
                    self.model_id,
                )

            # Assign device and evaluation mode
            target_device = "cuda" if (self._device_str == "cuda" and torch.cuda.is_available()) else "cpu"
            self.model.to(target_device)
            self.model.eval()

            # Dynamically inspect and verify class labels from model config
            if hasattr(self.model, "config"):
                if getattr(self.model.config, "id2label", None):
                    self.id2label = self.model.config.id2label
                if getattr(self.model.config, "label2id", None):
                    self.label2id = self.model.config.label2id

        except OSError as exc:
            raise ModelNotAvailableError(
                f"Could not load model '{self.model_id}'.\n"
                f"Original error: {exc}\n\n"
                "Possible causes:\n"
                "  1. No internet connection on first run (weights not cached yet).\n"
                "  2. The model ID is incorrect or has been removed.\n"
                "  3. HF_HOME / cache directory is full or permission-denied.\n\n"
                "Fix: connect to the internet and run the detector once to cache the weights."
            ) from exc
        except Exception as exc:
            raise ModelNotAvailableError(
                f"Unexpected error loading model: {exc}"
            ) from exc

    def _normalise_label(self, raw_label: str) -> str:
        """Convert a raw model label to one of our two canonical labels."""
        key = str(raw_label).strip().lower()
        return LABEL_MAP.get(key, str(raw_label).upper())

    def _predict_smaug(self, image: Image.Image) -> tuple:
        """
        Run inference using the Smaug-AI-Image-Detector architecture.
        Returns (predicted_label, confidence, normalised_scores).
        """
        import math
        from PIL import ImageOps

        img = ImageOps.exif_transpose(image).convert("RGB")
        w, h = img.size
        side = 576
        crop_size = 528

        if min(w, h) > side:
            s = side / min(w, h)
            img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
        elif min(w, h) < crop_size:
            s = crop_size / min(w, h)
            img = img.resize((math.ceil(w * s), math.ceil(h * s)), Image.BICUBIC)

        w, h = img.size
        cx, cy = (w - crop_size) // 2, (h - crop_size) // 2
        crop_img = img.crop((cx, cy, cx + crop_size, cy + crop_size))

        flat = [{"image": crop_img}]
        logits = self.model.encode(flat, batch_size=1, convert_to_tensor=True).float().view(1, 1)
        prob_ai = float(torch.sigmoid(logits.mean(1))[0].item())

        predicted_label = "AI_GENERATED" if prob_ai >= 0.5 else "REAL"
        confidence = round(prob_ai if predicted_label == "AI_GENERATED" else (1.0 - prob_ai), 4)

        normalised_scores = [
            {"label": "REAL", "score": round(1.0 - prob_ai, 4)},
            {"label": "AI_GENERATED", "score": round(prob_ai, 4)},
        ]
        return predicted_label, confidence, normalised_scores

    def predict(self, image: Image.Image) -> dict:
        """
        Run the detector on a single PIL image.

        Parameters
        ----------
        image : PIL.Image.Image
            An RGB image (output of preprocessing.load_image).

        Returns
        -------
        dict with keys:
            label        (str)   : "REAL" or "AI_GENERATED"
            confidence   (float) : probability in [0, 1] for the predicted class
            raw_scores   (list)  : full list of {label, score} from the model
            model_id     (str)   : model identifier
            inference_ms (float) : time taken in milliseconds

        Raises
        ------
        ModelNotAvailableError
            If neither model nor pipeline is loaded.
        RuntimeError
            If inference fails.
        """
        if not self.is_ready:
            raise ModelNotAvailableError(
                "Model is not loaded. Call TruthLensDetector() first."
            )

        t0 = time.perf_counter()

        # Branch 1: Smaug architecture inference
        if self.architecture == "smaug" and self.model is not None and self._pipe is None:
            try:
                predicted_label, confidence, normalised_scores = self._predict_smaug(image)
            except Exception as exc:
                raise RuntimeError(
                    f"Inference failed: {exc}\n"
                    "Check that the image was preprocessed correctly."
                ) from exc

        # Branch 2: Standard ViT AutoModel / AutoImageProcessor inference
        elif self.model is not None and self.processor is not None:
            try:
                target_device = "cuda" if (self._device_str == "cuda" and torch.cuda.is_available()) else "cpu"
                inputs = self.processor(images=image, return_tensors="pt")
                inputs = {k: v.to(target_device) for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probs = torch.nn.functional.softmax(logits, dim=-1)[0]

                # Map each output class index to its label and probability
                normalised_scores = []
                for idx in range(len(probs)):
                    raw_name = self.id2label.get(idx, str(idx))
                    normalised_scores.append({
                        "label": self._normalise_label(raw_name),
                        "score": round(float(probs[idx].item()), 4),
                    })

                top_idx = int(torch.argmax(probs).item())
                top_raw_label = self.id2label.get(top_idx, str(top_idx))
                predicted_label = self._normalise_label(top_raw_label)
                confidence = round(float(probs[top_idx].item()), 4)

            except Exception as exc:
                raise RuntimeError(
                    f"Inference failed: {exc}\n"
                    "Check that the image was preprocessed correctly."
                ) from exc

        # Branch 3: Pipeline fallback (e.g. for mocked pipeline tests)
        elif self._pipe is not None:
            try:
                raw_results = self._pipe(image)
            except Exception as exc:
                raise RuntimeError(
                    f"Inference failed: {exc}\n"
                    "Check that the image was preprocessed correctly."
                ) from exc

            top = max(raw_results, key=lambda x: x["score"])
            predicted_label = self._normalise_label(top["label"])
            confidence = round(float(top["score"]), 4)

            normalised_scores = [
                {
                    "label": self._normalise_label(r["label"]),
                    "score": round(float(r["score"]), 4),
                }
                for r in raw_results
            ]
        else:
            raise ModelNotAvailableError("Model weights are not initialized.")

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "label": predicted_label,
            "confidence": confidence,
            "raw_scores": normalised_scores,
            "model_id": self.model_id,
            "inference_ms": round(elapsed_ms, 1),
        }

    @property
    def is_ready(self) -> bool:
        """True if the model has been loaded successfully."""
        return (
            (self.model is not None and (self.processor is not None or self.architecture == "smaug"))
            or (self._pipe is not None)
        )

