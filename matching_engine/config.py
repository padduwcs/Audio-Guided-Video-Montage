"""Config nội bộ module — KHÔNG phải Data Contract giữa các stage.

Default theo stage spec §4.4.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# Default config theo stage spec §4.4
DEFAULT_CONFIG: dict[str, Any] = {
    "top_k": 5,
    "similarity": {
        "metric": "cosine",
        "normalize_vectors": True,
    },
    "score_weights": {
        "semantic": 0.60,
        "visual_quality": 0.15,
        "duration_fit": 0.15,
        "continuity": 0.05,
        "diversity": 0.05,
    },
    "penalties": {
        "low_quality": 0.10,
        "recent_repetition": 0.15,
    },
    "confidence_thresholds": {
        "high": 0.75,
        "medium": 0.50,
    },
    "fallback": {
        "enabled": True,
        "allow_low_quality": True,
    },
    "faiss": {
        "pre_k": 50,
    },
}


@dataclass
class Config:
    """Cấu hình nội bộ cho Matching Engine."""

    audio_segments_path: str
    clip_metadata_path: str
    embedding_metadata_path: str
    output_dir: str
    raw: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_CONFIG))

    # --- top_k ---
    @property
    def top_k(self) -> int:
        return int(self.raw["top_k"])

    # --- similarity ---
    @property
    def similarity_metric(self) -> str:
        return self.raw["similarity"]["metric"]

    @property
    def normalize_vectors(self) -> bool:
        return self.raw["similarity"]["normalize_vectors"]

    # --- score weights ---
    @property
    def weight_semantic(self) -> float:
        return float(self.raw["score_weights"]["semantic"])

    @property
    def weight_visual_quality(self) -> float:
        return float(self.raw["score_weights"]["visual_quality"])

    @property
    def weight_duration_fit(self) -> float:
        return float(self.raw["score_weights"]["duration_fit"])

    @property
    def weight_continuity(self) -> float:
        return float(self.raw["score_weights"]["continuity"])

    @property
    def weight_diversity(self) -> float:
        return float(self.raw["score_weights"]["diversity"])

    # --- penalties ---
    @property
    def penalty_low_quality(self) -> float:
        return float(self.raw["penalties"]["low_quality"])

    @property
    def penalty_recent_repetition(self) -> float:
        return float(self.raw["penalties"]["recent_repetition"])

    # --- confidence thresholds ---
    @property
    def threshold_high(self) -> float:
        return float(self.raw["confidence_thresholds"]["high"])

    @property
    def threshold_medium(self) -> float:
        return float(self.raw["confidence_thresholds"]["medium"])

    # --- fallback ---
    @property
    def fallback_enabled(self) -> bool:
        return self.raw["fallback"]["enabled"]

    @property
    def fallback_allow_low_quality(self) -> bool:
        return self.raw["fallback"]["allow_low_quality"]

    # --- faiss ---
    @property
    def faiss_pre_k(self) -> int:
        return int(self.raw.get("faiss", {}).get("pre_k", 50))


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
    """Load config từ file JSON (optional) rồi merge lên default."""
    raw = dict(DEFAULT_CONFIG)
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            user_cfg = json.load(f)
        raw = deep_merge(raw, user_cfg)
    return Config(raw=raw, **paths)
