from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.contract import (
    CLIP_STATUS_VALUES,
    DEFAULT_RENDER_SETTINGS,
    DEFAULT_TIMING,
    EPS,
    MAX_SPEED,
    MIN_SPEED,
    SCHEMA_VERSION,
)
from shared.timeline_contract import timeline_contract_errors


class TimelinePlanningError(Exception):
    pass


@dataclass
class PlanningLog:
    summary: dict[str, int] = field(default_factory=lambda: {"segments": 0, "warnings": 0})
    items: list[dict[str, Any]] = field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _approx_equal(left: float, right: float, tolerance: float = EPS) -> bool:
    return abs(left - right) <= tolerance


def _require_project_ids(*payloads: dict[str, Any]) -> str:
    project_ids = {payload["project_id"] for payload in payloads if "project_id" in payload}
    if len(project_ids) != 1:
        raise TimelinePlanningError(f"project_id mismatch across inputs: {sorted(project_ids)}")
    return next(iter(project_ids))


def _index_by(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise TimelinePlanningError(f"{label}: missing {key}")
        if value in result:
            raise TimelinePlanningError(f"{label}: duplicate {key} {value!r}")
        result[value] = item
    return result


def _clip_is_valid(clip: dict[str, Any]) -> bool:
    status = clip.get("status", "usable")
    if status not in CLIP_STATUS_VALUES:
        return False
    if status in {"too_short", "error"}:
        return False
    duration = float(clip.get("duration", 0))
    return duration > 0


def _resolve_source_path(clip: dict[str, Any], videos_by_id: dict[str, dict[str, Any]]) -> str | None:
    source_path = clip.get("source_path")
    if isinstance(source_path, str) and source_path:
        return source_path
    video_id = clip.get("video_id")
    if isinstance(video_id, str) and video_id in videos_by_id:
        return videos_by_id[video_id].get("normalized_path")
    return None


def _ordered_clip_ids(candidate_set: dict[str, Any]) -> list[str]:
    selected = candidate_set.get("selected_clip_id")
    candidates = candidate_set.get("candidates", [])
    ranked = sorted(candidates, key=lambda item: int(item["rank"]))
    ordered: list[str] = []
    if isinstance(selected, str) and selected:
        ordered.append(selected)
    for candidate in ranked:
        clip_id = candidate["clip_id"]
        if clip_id not in ordered:
            ordered.append(clip_id)
    return ordered


def _score_for_clip(candidate_set: dict[str, Any], clip_id: str) -> float | None:
    for candidate in candidate_set.get("candidates", []):
        if candidate.get("clip_id") == clip_id:
            return candidate.get("final_score")
    return None


def _rank_for_clip(candidate_set: dict[str, Any], clip_id: str) -> int | None:
    for candidate in candidate_set.get("candidates", []):
        if candidate.get("clip_id") == clip_id:
            return int(candidate["rank"])
    return None


def _compute_needs_review(
    *,
    confidence: str,
    fallback_used: bool,
    visual_items: list[dict[str, Any]],
    used_non_selected: bool,
    reused_clips: bool,
    clip_status: str | None,
) -> bool:
    if not visual_items:
        return True
    if confidence == "low" or fallback_used:
        return True
    if used_non_selected:
        return True
    if reused_clips:
        return True
    if clip_status == "low_quality":
        return True
    return False


def _build_visual_items_for_segment(
    *,
    segment: dict[str, Any],
    candidate_set: dict[str, Any],
    clips_by_id: dict[str, dict[str, Any]],
    videos_by_id: dict[str, dict[str, Any]],
    render_settings: dict[str, Any],
    segment_index: int,
    log: PlanningLog,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    segment_id = segment["segment_id"]
    segment_start = float(segment["start"])
    segment_end = float(segment["end"])
    segment_duration = float(segment["duration"])
    warnings: list[str] = []
    visual_items: list[dict[str, Any]] = []
    used_non_selected = False
    selected_clip_id = candidate_set.get("selected_clip_id")

    remaining_start = segment_start
    remaining_duration = segment_duration
    visual_index = 1

    clip_ids = _ordered_clip_ids(candidate_set)
    usable_clip_ids: list[str] = []
    for clip_id in clip_ids:
        clip = clips_by_id.get(clip_id)
        if clip is None or not _clip_is_valid(clip):
            warnings.append(f"skipped invalid clip {clip_id!r}")
            continue
        if not _resolve_source_path(clip, videos_by_id):
            warnings.append(f"missing source_path for clip {clip_id}")
            continue
        usable_clip_ids.append(clip_id)

    if not usable_clip_ids:
        warnings.append("candidate set has no clips")
        log.summary["warnings"] += 1
        return [], {
            "segment_id": segment_id,
            "decision": "no_candidates",
            "warnings": warnings,
        }

    clip_pointer = 0
    reused_clips = False
    while remaining_duration > EPS:
        if clip_pointer >= len(usable_clip_ids) and not reused_clips:
            reused_clips = True
            warnings.append("reused ranked clips to cover the full audio segment")
        clip_id = usable_clip_ids[clip_pointer % len(usable_clip_ids)]
        clip_pointer += 1
        clip = clips_by_id.get(clip_id)
        assert clip is not None

        if selected_clip_id and clip_id != selected_clip_id and not visual_items:
            used_non_selected = True

        source_path = _resolve_source_path(clip, videos_by_id)
        assert source_path is not None

        clip_start_bound = float(clip["start"])
        clip_end_bound = float(clip["end"])
        clip_duration = clip_end_bound - clip_start_bound

        if clip_duration >= remaining_duration - EPS:
            clip_start = clip_start_bound
            clip_end = clip_start_bound + remaining_duration
            timeline_start = remaining_start
            timeline_end = segment_end
            speed = 1.0
            remaining_duration = 0.0
        else:
            speed_if_single = clip_duration / remaining_duration
            if speed_if_single >= MIN_SPEED:
                clip_start = clip_start_bound
                clip_end = clip_end_bound
                timeline_start = remaining_start
                timeline_end = segment_end
                speed = speed_if_single
                remaining_duration = 0.0
            else:
                clip_start = clip_start_bound
                clip_end = clip_end_bound
                timeline_start = remaining_start
                timeline_end = remaining_start + clip_duration
                speed = 1.0
                remaining_start += clip_duration
                remaining_duration -= clip_duration

        if speed < MIN_SPEED or speed > MAX_SPEED:
            warnings.append(f"speed {speed:.3f} outside MVP range for clip {clip_id}")
            if visual_items:
                continue

        rank = _rank_for_clip(candidate_set, clip_id)
        visual_items.append(
            {
                "timeline_item_id": f"t{segment_index:03d}_i{visual_index:02d}",
                "clip_id": clip_id,
                "video_id": clip["video_id"],
                "source_path": source_path,
                "clip_start": round(clip_start, 3),
                "clip_end": round(clip_end, 3),
                "timeline_start": round(timeline_start, 3),
                "timeline_end": round(timeline_end, 3),
                "speed": round(speed, 3),
                "transition": render_settings.get("default_transition", "cut"),
                "effect": None,
                "crop_mode": render_settings.get("crop_mode", "fit"),
                "volume": 0.0 if not render_settings.get("keep_original_audio", False) else render_settings.get("original_audio_volume", 0.0),
                "source_candidate_rank": rank,
                "locked": False,
            }
        )
        visual_index += 1

    if remaining_duration > EPS:
        warnings.append(f"unfilled segment duration remaining: {remaining_duration:.3f}s")
        log.summary["warnings"] += 1

    decision = "selected_clip" if visual_items and not used_non_selected else "rank_or_partial_fill"
    if not visual_items:
        decision = "no_visual"
        log.summary["warnings"] += 1

    log.items.append(
        {
            "segment_id": segment_id,
            "decision": decision,
            "warnings": warnings,
        }
    )
    if warnings:
        log.summary["warnings"] += len(warnings)

    primary_clip = clips_by_id.get(visual_items[0]["clip_id"]) if visual_items else None
    return visual_items, {
        "used_non_selected": used_non_selected,
        "reused_clips": reused_clips,
        "clip_status": primary_clip.get("status") if primary_clip else None,
    }


def build_timeline(
    media_metadata: dict[str, Any],
    audio_segments: dict[str, Any],
    clip_metadata: dict[str, Any],
    matching_candidates: dict[str, Any],
    *,
    render_settings: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_id = _require_project_ids(media_metadata, audio_segments, clip_metadata, matching_candidates)

    audio = media_metadata.get("audio", {})
    if not isinstance(audio, dict) or not audio.get("audio_id"):
        raise TimelinePlanningError("media_metadata.audio.audio_id is required")

    segments = audio_segments.get("items", [])
    if not isinstance(segments, list) or not segments:
        raise TimelinePlanningError("audio_segments.items must be non-empty")

    clip_items = clip_metadata.get("items", [])
    if not isinstance(clip_items, list) or not clip_items:
        raise TimelinePlanningError("clip_metadata.items must be non-empty")

    matching_items = matching_candidates.get("items", [])
    if not isinstance(matching_items, list) or not matching_items:
        raise TimelinePlanningError("matching_candidates.items must be non-empty")

    segments = sorted(segments, key=lambda item: float(item["start"]))
    clips_by_id = _index_by(clip_items, "clip_id", "clip_metadata.items")
    videos = media_metadata.get("videos", [])
    if not isinstance(videos, list) or not videos:
        raise TimelinePlanningError("media_metadata.videos must be non-empty")
    videos_by_id = _index_by(videos, "video_id", "media_metadata.videos")

    candidate_by_segment: dict[str, dict[str, Any]] = {}
    for candidate_set in matching_items:
        segment_id = candidate_set.get("audio_segment_id")
        if not isinstance(segment_id, str):
            raise TimelinePlanningError("matching candidate set missing audio_segment_id")
        if segment_id in candidate_by_segment:
            raise TimelinePlanningError(
                f"duplicate candidate set for segment {segment_id}"
            )
        candidate_by_segment[segment_id] = candidate_set

    settings = dict(DEFAULT_RENDER_SETTINGS)
    if render_settings:
        settings.update(render_settings)

    log = PlanningLog()
    timeline_items: list[dict[str, Any]] = []

    for index, segment in enumerate(segments, start=1):
        segment_id = segment["segment_id"]
        candidate_set = candidate_by_segment.get(segment_id)
        if candidate_set is None:
            raise TimelinePlanningError(f"missing candidate set for segment {segment_id}")

        visual_items, meta = _build_visual_items_for_segment(
            segment=segment,
            candidate_set=candidate_set,
            clips_by_id=clips_by_id,
            videos_by_id=videos_by_id,
            render_settings=settings,
            segment_index=index,
            log=log,
        )

        confidence = candidate_set.get("confidence", "medium")
        fallback_used = bool(candidate_set.get("fallback_used", False))
        selected_clip_id = candidate_set.get("selected_clip_id")
        score = _score_for_clip(candidate_set, selected_clip_id) if selected_clip_id else None
        if score is None and visual_items:
            score = _score_for_clip(candidate_set, visual_items[0]["clip_id"])

        needs_review = _compute_needs_review(
            confidence=str(confidence),
            fallback_used=fallback_used,
            visual_items=visual_items,
            used_non_selected=bool(meta.get("used_non_selected")),
            reused_clips=bool(meta.get("reused_clips")),
            clip_status=meta.get("clip_status"),
        )

        timeline_items.append(
            {
                "segment_id": segment_id,
                "audio_start": float(segment["start"]),
                "audio_end": float(segment["end"]),
                "duration": float(segment["duration"]),
                "text": segment["text"],
                "confidence": confidence,
                "score": score,
                "needs_review": needs_review,
                "fallback_used": fallback_used,
                "user_edited": False,
                "candidates_ref": candidate_set.get("candidate_set_id"),
                "visual_items": visual_items,
            }
        )

    log.summary["segments"] = len(timeline_items)
    now = _utc_now()
    timeline = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "audio_id": audio["audio_id"],
        "created_at": now,
        "updated_at": now,
        "render_settings": settings,
        "items": timeline_items,
    }

    contract_errors = timeline_contract_errors(
        timeline,
        audio_duration=float(audio.get("duration", 0)),
        require_visuals=True,
    )
    if contract_errors:
        raise TimelinePlanningError(
            "timeline postcondition failed: " + "; ".join(contract_errors)
        )

    planning_log = {
        "project_id": project_id,
        "created_at": now,
        "timing": dict(DEFAULT_TIMING),
        "summary": log.summary,
        "items": log.items,
    }
    return timeline, planning_log
