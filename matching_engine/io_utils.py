"""Đọc/validate input và ghi output đúng Data Contract.

Fail-fast rules theo spec §4.2.
"""

from __future__ import annotations

import json
import os
from typing import Any


class InputError(Exception):
    """Lỗi input chặn pipeline — exit != 0, KHÔNG ghi metadata giả."""


# ---------- LOAD + VALIDATE (fail-fast §4.2) ----------


def _load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        raise InputError(f"File khong ton tai: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise InputError(f"JSON khong parse duoc: {path} ({e})")
    if not isinstance(data, dict):
        raise InputError(f"{path}: top-level value phai la object")
    return data


def load_audio_segments(path: str) -> dict[str, Any]:
    """Load và validate audio_segments.json."""
    data = _load_json(path)
    for key in ("schema_version", "project_id", "items"):
        if key not in data:
            raise InputError(f"audio_segments thieu field '{key}'")
    if not data["items"]:
        raise InputError("audio_segments.items rong")
    for seg in data["items"]:
        if not seg.get("segment_id"):
            raise InputError("Segment thieu segment_id")
        for req in ("start", "end", "duration"):
            if req not in seg:
                raise InputError(
                    f"Segment {seg['segment_id']} thieu field '{req}'"
                )
        if not seg.get("query"):
            raise InputError(f"Segment {seg['segment_id']} thieu query")
    return data


def load_clip_metadata(path: str) -> dict[str, Any]:
    """Load và validate clip_metadata.json."""
    data = _load_json(path)
    for key in ("schema_version", "project_id", "items"):
        if key not in data:
            raise InputError(f"clip_metadata thieu field '{key}'")
    if not data["items"]:
        raise InputError("clip_metadata.items rong")
    for clip in data["items"]:
        if not clip.get("clip_id"):
            raise InputError("Clip thieu clip_id")
        if "duration" not in clip:
            raise InputError(f"Clip {clip['clip_id']} thieu duration")
        qs = clip.get("quality_score")
        if qs is not None and not (0.0 <= qs <= 1.0):
            raise InputError(
                f"Clip {clip['clip_id']} quality_score={qs} ngoai [0,1]"
            )
    return data


def load_embedding_metadata(path: str) -> dict[str, Any]:
    """Load và validate embedding_metadata.json."""
    data = _load_json(path)
    for key in ("schema_version", "project_id"):
        if key not in data:
            raise InputError(f"embedding_metadata thieu field '{key}'")
    model = data.get("model")
    if not model:
        raise InputError("embedding_metadata thieu 'model'")
    for mk in ("name", "type", "dimension"):
        if mk not in model:
            raise InputError(f"embedding_metadata.model thieu '{mk}'")
    if not data.get("text_embeddings"):
        raise InputError("embedding_metadata.text_embeddings rong")
    if not data.get("visual_embeddings"):
        raise InputError("embedding_metadata.visual_embeddings rong")
    # validate embedding_id unique
    seen_ids: set[str] = set()
    for emb in data["text_embeddings"] + data["visual_embeddings"]:
        eid = emb.get("embedding_id")
        if not eid:
            raise InputError("Embedding thieu embedding_id")
        if eid in seen_ids:
            raise InputError(f"embedding_id trung lap: {eid}")
        seen_ids.add(eid)
    return data


def check_project_id(
    audio: dict, clip: dict, embedding: dict
) -> str:
    """Ba file phải cùng project_id — không khớp thì dừng."""
    pid_a = audio.get("project_id")
    pid_c = clip.get("project_id")
    pid_e = embedding.get("project_id")
    if pid_a != pid_c or pid_a != pid_e:
        raise InputError(
            f"project_id khong khop: audio='{pid_a}' "
            f"clip='{pid_c}' embedding='{pid_e}'"
        )
    return pid_a  # type: ignore[return-value]


# ---------- WRITE OUTPUT ----------


def write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
