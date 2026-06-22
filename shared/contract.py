from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
EPS = 0.01

CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})
MEDIA_STATUS_VALUES = frozenset({"ready", "warning", "error"})
CLIP_STATUS_VALUES = frozenset({"usable", "low_quality", "too_short", "error"})
TRANSITION_VALUES = frozenset({"cut", "fade", "crossfade"})
CROP_MODE_VALUES = frozenset({"fit", "fill", "center_crop", "blur_background"})

MIN_SPEED = 0.75
MAX_SPEED = 1.25

DEFAULT_RENDER_SETTINGS: dict[str, Any] = {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "format": "mp4",
    "default_transition": "cut",
    "crop_mode": "center_crop",
    "keep_original_audio": False,
    "original_audio_volume": 0.0,
}

DEFAULT_TIMING = {
    "min_speed": MIN_SPEED,
    "max_speed": MAX_SPEED,
    "time_tolerance": EPS,
}
