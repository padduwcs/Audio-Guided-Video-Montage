"""Đọc/validate input và ghi output đúng Data Contract."""

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
            return json.load(f)
    except json.JSONDecodeError as e:
        raise InputError(f"JSON khong parse duoc: {path} ({e})")


def load_audio_segments(path: str) -> dict[str, Any]:
    data = _load_json(path)
    for key in ("schema_version", "project_id", "items"):
        if key not in data:
            raise InputError(f"audio_segments thieu field '{key}'")
    if not data["items"]:
        raise InputError("audio_segments.items rong")
    for seg in data["items"]:
        if not seg.get("segment_id"):
            raise InputError("Segment thieu segment_id")
        if not seg.get("query"):
            raise InputError(f"Segment {seg['segment_id']} thieu query")
    return data


def load_clip_metadata(path: str) -> dict[str, Any]:
    data = _load_json(path)
    for key in ("schema_version", "project_id", "items"):
        if key not in data:
            raise InputError(f"clip_metadata thieu field '{key}'")
    if not data["items"]:
        raise InputError("clip_metadata.items rong")
    for clip in data["items"]:
        if not clip.get("clip_id"):
            raise InputError("Clip thieu clip_id")
    return data


def check_project_id(audio: dict, clip: dict) -> str:
    """Hai file phai cung project_id — khong khop thi dung."""
    pid_a, pid_c = audio.get("project_id"), clip.get("project_id")
    if pid_a != pid_c:
        raise InputError(f"project_id khong khop: audio='{pid_a}' clip='{pid_c}'")
    return pid_a


# ---------- SELECT source_text (§7.2) ----------

EMBED_STATUSES = {"usable", "low_quality"}   # chi embed clip nay
SKIP_STATUSES = {"too_short", "error"}


def select_source_text(segment: dict, prefer_translated: bool, fallback_to_query: bool) -> str:
    """Chon text that su dua vao model. KHONG bia text."""
    tq = segment.get("translated_query")
    q = segment.get("query")
    if prefer_translated and tq:
        return tq
    if q:
        return q
    if fallback_to_query and q:
        return q
    raise InputError(f"Segment {segment.get('segment_id')} khong co text hop le")


def iter_embeddable_keyframes(clip_data: dict, log: dict):
    """Yield (clip_id, keyframe) cho clip usable/low_quality, keyframe co path ton tai."""
    for clip in clip_data["items"]:
        status = clip.get("status")
        if status in SKIP_STATUSES:
            log["skipped_clips"].append({"clip_id": clip["clip_id"], "reason": status})
            continue
        if status is None:
            log["warnings"].append(f"Clip {clip['clip_id']} thieu status -> xu ly nhu usable")
        elif status not in EMBED_STATUSES:
            log["warnings"].append(f"Clip {clip['clip_id']} status la '{status}' -> xu ly nhu usable")

        keyframes = clip.get("keyframes") or []
        if not keyframes:
            log["warnings"].append(f"Clip {clip['clip_id']} khong co keyframe -> bo qua")
            continue
        for kf in keyframes:
            if not kf.get("keyframe_id") or not kf.get("path"):
                log["warnings"].append(f"Keyframe thieu id/path o clip {clip['clip_id']}")
                continue
            if not os.path.exists(kf["path"]):
                log["warnings"].append(f"Keyframe path khong ton tai: {kf['path']} -> bo qua")
                continue
            yield clip["clip_id"], kf


# ---------- WRITE OUTPUT ----------

def write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
