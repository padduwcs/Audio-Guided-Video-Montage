"""Serialize, validate, and atomically write Audio Analyzer JSON artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from audio_analyzer.enrichment import ALLOWED_SEGMENT_TYPES
from audio_analyzer.models import EnrichedAudioSegment


TOP_LEVEL_FIELDS = {
    "schema_version",
    "project_id",
    "audio_id",
    "language",
    "created_at",
    "items",
}
ITEM_FIELDS = {
    "segment_id",
    "start",
    "end",
    "duration",
    "text",
    "query",
    "translated_query",
    "keywords",
    "segment_type",
    "asr_confidence",
    "needs_review",
}


class OutputValidationError(ValueError):
    """Raised when an audio segments document violates its contract."""


def build_audio_segments_document(
    *,
    project_id: str,
    audio_id: str,
    created_at: str,
    segments: list[EnrichedAudioSegment],
    language: str = "vi",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "project_id": project_id,
        "audio_id": audio_id,
        "language": language,
        "created_at": created_at,
        "items": [
            {
                "segment_id": enriched.segment.segment_id,
                "start": enriched.segment.start,
                "end": enriched.segment.end,
                "duration": enriched.segment.duration,
                "text": enriched.segment.text,
                "query": enriched.query,
                "translated_query": None,
                "keywords": list(enriched.keywords),
                "segment_type": enriched.segment_type,
                "asr_confidence": enriched.segment.confidence,
                "needs_review": enriched.needs_review,
            }
            for enriched in segments
        ],
    }


def validate_audio_segments_document(
    document: dict[str, Any], *, audio_duration: float
) -> None:
    if set(document) != TOP_LEVEL_FIELDS:
        raise OutputValidationError(
            f"audio_segments top-level fields must be exactly {sorted(TOP_LEVEL_FIELDS)}"
        )
    for field in ("schema_version", "project_id", "audio_id", "language", "created_at"):
        if not isinstance(document[field], str) or not document[field]:
            raise OutputValidationError(f"{field} must be a non-empty string")
    if document["schema_version"] != "1.0":
        raise OutputValidationError("schema_version must be '1.0'")
    try:
        datetime.fromisoformat(document["created_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise OutputValidationError("created_at must be an ISO-8601 timestamp") from exc

    items = document["items"]
    if not isinstance(items, list) or not items:
        raise OutputValidationError("items must be a non-empty array")

    previous_end = 0.0
    for index, item in enumerate(items, start=1):
        label = f"items[{index - 1}]"
        if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
            raise OutputValidationError(
                f"{label} fields must be exactly {sorted(ITEM_FIELDS)}"
            )
        if item["segment_id"] != f"a{index:03d}":
            raise OutputValidationError(f"{label}.segment_id is not sequential")
        for field in ("start", "end", "duration"):
            value = item[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise OutputValidationError(f"{label}.{field} must be a number")
        if item["start"] < 0 or item["end"] <= item["start"]:
            raise OutputValidationError(f"{label} has an invalid timestamp range")
        if abs(item["duration"] - (item["end"] - item["start"])) > 1e-9:
            raise OutputValidationError(f"{label}.duration must equal end - start")
        if abs(item["start"] - previous_end) > 1e-9:
            raise OutputValidationError(
                f"{label}.start must equal the previous segment end"
            )
        if item["end"] > audio_duration + 1e-9:
            raise OutputValidationError(f"{label}.end exceeds audio duration")
        previous_end = item["end"]

        for field in ("text", "query"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise OutputValidationError(f"{label}.{field} must be non-empty")
        confidence = item["asr_confidence"]
        if confidence is not None and (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= confidence <= 1.0
        ):
            raise OutputValidationError(
                f"{label}.asr_confidence must be null or in [0.0, 1.0]"
            )
        if item["translated_query"] is not None:
            raise OutputValidationError(
                f"{label}.translated_query must remain null before translation is implemented"
            )
        if not isinstance(item["keywords"], list) or not all(
            isinstance(keyword, str) and keyword for keyword in item["keywords"]
        ):
            raise OutputValidationError(f"{label}.keywords must be an array of strings")
        if item["segment_type"] not in ALLOWED_SEGMENT_TYPES:
            raise OutputValidationError(f"{label}.segment_type is unsupported")
        if not isinstance(item["needs_review"], bool):
            raise OutputValidationError(f"{label}.needs_review must be boolean")

    if abs(previous_end - audio_duration) > 1e-9:
        raise OutputValidationError("audio segments must cover the full audio duration")


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    """Write complete UTF-8 JSON beside its destination, then replace it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(document, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

