"""Wrap model multimodal: text -> vector, image -> vector (CUNG embedding space).

Diem song con (BAY 1): text va image PHAI dung cung 1 model multimodal,
neu khong vector khong so sanh duoc o Stage 5.

Cung cap 2 backend:
  - CLIPModelBackend: that, dung transformers + torch (production).
    Tu dong dich text tieng Viet sang tieng Anh truoc khi encode vi
    CLIP goc chi hieu tieng Anh.
  - FakeModelBackend: deterministic hash -> vector, KHONG can torch,
    de chay thu pipeline / unit test nhanh. Vector van L2-normalized,
    van dung dimension, nhung KHONG co y nghia ngu nghia.
"""

from __future__ import annotations
import hashlib
import re
import numpy as np


# --------------- Translation helper ---------------

_translator_instance = None


def _get_translator():
    """Lazy-load Google Translator (free, no API key)."""
    global _translator_instance
    if _translator_instance is None:
        try:
            from deep_translator import GoogleTranslator
            _translator_instance = GoogleTranslator(source="vi", target="en")
            print("[info] Loaded GoogleTranslator (vi → en) for CLIP text encoding")
        except ImportError:
            print("[warn] deep-translator not installed, skipping translation")
            _translator_instance = False  # sentinel: don't retry
    return _translator_instance if _translator_instance else None


def _is_mostly_ascii(text: str) -> bool:
    """Return True if text is already mostly English/ASCII."""
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return len(text) > 0 and (ascii_chars / len(text)) > 0.85


def translate_to_english(text: str) -> str:
    """Translate Vietnamese text to English for CLIP.

    Returns original text if already English or translation fails.
    """
    if not text or _is_mostly_ascii(text):
        return text
    translator = _get_translator()
    if translator is None:
        return text
    try:
        translated = translator.translate(text)
        if translated and isinstance(translated, str) and len(translated) > 2:
            return translated
    except Exception as e:
        print(f"[warn] Translation failed for '{text[:50]}...': {e}")
    return text


def translate_batch(texts: list[str]) -> list[str]:
    """Translate a batch of texts, preserving order."""
    results = []
    for t in texts:
        results.append(translate_to_english(t))
    return results


# --------------- Core model backends ---------------

class BaseBackend:
    dimension: int
    name: str

    def encode_text(self, text: str) -> np.ndarray:
        raise NotImplementedError

    def encode_image(self, image_path: str) -> np.ndarray:
        raise NotImplementedError

    def encode_texts(self, texts: list[str]) -> list[np.ndarray]:
        return [self.encode_text(t) for t in texts]

    def encode_images(self, image_paths: list[str]) -> list[np.ndarray]:
        return [self.encode_image(p) for p in image_paths]


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    if vec.ndim == 1:
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vec / norms


class FakeModelBackend(BaseBackend):
    """Deterministic dummy embedding — cho test pipeline khong can GPU/torch."""

    def __init__(self, name: str = "clip-vit-base-patch32", dimension: int = 512):
        self.name = name
        self.dimension = dimension

    def _hash_vector(self, key: str) -> np.ndarray:
        # Seed tu hash de cung input -> cung vector (deterministic)
        seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return l2_normalize(rng.standard_normal(self.dimension).astype("float32"))

    def encode_text(self, text: str) -> np.ndarray:
        return self._hash_vector("TEXT::" + text)

    def encode_image(self, image_path: str) -> np.ndarray:
        return self._hash_vector("IMAGE::" + image_path)


class CLIPModelBackend(BaseBackend):
    """Backend that su dung openai/clip-vit-base-patch32.

    Tu dong dich text tieng Viet sang tieng Anh truoc khi encode,
    vi CLIP goc chi hieu tieng Anh.
    """

    def __init__(self, name: str = "clip-vit-base-patch32", dimension: int = 512):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        hf_id = name if "/" in name else f"openai/{name}"
        self.model = CLIPModel.from_pretrained(hf_id)
        self.processor = CLIPProcessor.from_pretrained(hf_id)
        self.model.eval()
        self.name = name
        # Dimension that cua model (projection dim)
        self.dimension = self.model.config.projection_dim
        if self.dimension != dimension:
            # Ghi dimension THAT, khong ep theo config
            print(f"[warn] config dimension={dimension} != model dim={self.dimension}, dung {self.dimension}")

    def encode_text(self, text: str) -> np.ndarray:
        # Translate Vietnamese → English before CLIP encoding
        en_text = translate_to_english(text)
        inputs = self.processor(text=[en_text], return_tensors="pt", padding=True, truncation=True)
        with self._torch.no_grad():
            feats = self.model.get_text_features(**inputs)
        return l2_normalize(feats[0].cpu().numpy().astype("float32"))

    def encode_texts(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        # Batch translate
        en_texts = translate_batch(texts)
        inputs = self.processor(text=en_texts, return_tensors="pt", padding=True, truncation=True)
        with self._torch.no_grad():
            feats = self.model.get_text_features(**inputs)
        mat = l2_normalize(feats.cpu().numpy().astype("float32"))
        return [mat[i] for i in range(mat.shape[0])]

    def encode_image(self, image_path: str) -> np.ndarray:
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        with self._torch.no_grad():
            feats = self.model.get_image_features(**inputs)
        return l2_normalize(feats[0].cpu().numpy().astype("float32"))

    def encode_images(self, image_paths: list[str]) -> list[np.ndarray]:
        if not image_paths:
            return []
        from PIL import Image
        images = [Image.open(p).convert("RGB") for p in image_paths]
        inputs = self.processor(images=images, return_tensors="pt")
        with self._torch.no_grad():
            feats = self.model.get_image_features(**inputs)
        mat = l2_normalize(feats.cpu().numpy().astype("float32"))
        return [mat[i] for i in range(mat.shape[0])]


def load_backend(name: str, dimension: int, use_fake: bool = False) -> BaseBackend:
    """Load model that; neu khong duoc (chua cai torch) va use_fake=True -> FakeBackend."""
    if use_fake:
        print("[info] Dung FakeModelBackend (test mode, vector khong co y nghia ngu nghia)")
        return FakeModelBackend(name, dimension)
    try:
        return CLIPModelBackend(name, dimension)
    except Exception as e:
        raise RuntimeError(
            f"Khong load duoc CLIP model '{name}': {e}\n"
            f"Cai dat: pip install torch transformers pillow\n"
            f"Hoac chay voi --fake de test pipeline."
        )
