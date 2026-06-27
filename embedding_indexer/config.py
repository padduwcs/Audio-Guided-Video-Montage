"""Config nội bộ module — KHÔNG phải Data Contract giữa các stage."""

from dataclasses import dataclass, field
from typing import Any
import json


# Default theo stage spec §4.4
DEFAULT_CONFIG: dict[str, Any] = {
    "model": {
        "name": "clip-vit-base-patch32",   # HuggingFace: openai/clip-vit-base-patch32
        "type": "multimodal",
        "dimension": 512,
    },
    "text": {
        "prefer_translated_query": True,   # CLIP gốc mạnh tiếng Anh -> ưu tiên translated_query
        "fallback_to_query": True,
    },
    "visual": {
        "embedding_level": "keyframe",     # MVP: embed theo keyframe
        "aggregate_clip_embedding": False,
    },
    "index": {
        "enabled": True,
        "type": "faiss",
    },
    "normalize_vectors": True,             # L2 normalize -> cosine = dot product (thống nhất với Stage 5)
}


@dataclass
class Config:
    audio_segments_path: str
    clip_metadata_path: str
    output_dir: str
    embedding_dir: str
    index_dir: str
    raw: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_CONFIG))

    @property
    def model_name(self) -> str:
        return self.raw["model"]["name"]

    @property
    def dimension(self) -> int:
        return self.raw["model"]["dimension"]

    @property
    def prefer_translated(self) -> bool:
        return self.raw["text"]["prefer_translated_query"]

    @property
    def fallback_to_query(self) -> bool:
        return self.raw["text"]["fallback_to_query"]

    @property
    def index_enabled(self) -> bool:
        return self.raw["index"]["enabled"]

    @property
    def normalize(self) -> bool:
        return self.raw["normalize_vectors"]


def deep_merge(base: dict, override: dict) -> dict:
    """Merge override lên base (giữ default nếu key thiếu)."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(config_path: str | None, **paths: str) -> Config:
    raw = dict(DEFAULT_CONFIG)
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            user_cfg = json.load(f)
        raw = deep_merge(raw, user_cfg)
    return Config(raw=raw, **paths)
