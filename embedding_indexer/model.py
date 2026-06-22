"""Wrap model multimodal: text -> vector, image -> vector (CUNG embedding space).

Diem song con (BAY 1): text va image PHAI dung cung 1 model multimodal,
neu khong vector khong so sanh duoc o Stage 5.

Cung cap 2 backend:
  - CLIPModelBackend: that, dung transformers + torch (production).
  - FakeModelBackend: deterministic hash -> vector, KHONG can torch,
    de chay thu pipeline / unit test nhanh. Vector van L2-normalized,
    van dung dimension, nhung KHONG co y nghia ngu nghia.
"""

from __future__ import annotations
import hashlib
import numpy as np


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
    """Backend that su dung openai/clip-vit-base-patch32."""

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
            # Ghi dimension THAT, khong ep theo config (BAY: model.dimension phai khop vector that)
            print(f"[warn] config dimension={dimension} != model dim={self.dimension}, dung {self.dimension}")

    def encode_text(self, text: str) -> np.ndarray:
        inputs = self.processor(text=[text], return_tensors="pt", padding=True, truncation=True)
        with self._torch.no_grad():
            feats = self.model.get_text_features(**inputs)
        return l2_normalize(feats[0].cpu().numpy().astype("float32"))

    def encode_texts(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        inputs = self.processor(text=texts, return_tensors="pt", padding=True, truncation=True)
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
