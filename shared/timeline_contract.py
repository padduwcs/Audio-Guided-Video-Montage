from __future__ import annotations

from typing import Any

from shared.contract import EPS, MAX_SPEED, MIN_SPEED


def timeline_contract_errors(
    timeline: dict[str, Any],
    *,
    audio_duration: float | None = None,
    require_visuals: bool = True,
) -> list[str]:
    """Return internal timing/renderability errors for a timeline document."""

    errors: list[str] = []
    required_top = {
        "schema_version",
        "project_id",
        "audio_id",
        "created_at",
        "updated_at",
        "render_settings",
        "items",
    }
    missing_top = sorted(required_top - set(timeline))
    if missing_top:
        return [f"timeline missing fields: {', '.join(missing_top)}"]

    items = timeline.get("items")
    if not isinstance(items, list) or not items:
        return ["timeline.items must be a non-empty list"]

    seen_segments: set[str] = set()
    seen_visuals: set[str] = set()
    expected_audio_start = 0.0
    for item_index, item in enumerate(items):
        label = f"timeline.items[{item_index}]"
        segment_id = item.get("segment_id")
        if not isinstance(segment_id, str) or not segment_id:
            errors.append(f"{label}.segment_id must be a non-empty string")
        elif segment_id in seen_segments:
            errors.append(f"duplicate segment_id {segment_id}")
        else:
            seen_segments.add(segment_id)

        try:
            audio_start = float(item["audio_start"])
            audio_end = float(item["audio_end"])
            duration = float(item["duration"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label} has invalid audio timing")
            continue

        if audio_end <= audio_start:
            errors.append(f"{label} must have positive duration")
        if abs(duration - (audio_end - audio_start)) > EPS:
            errors.append(f"{label}.duration does not match audio range")
        if abs(audio_start - expected_audio_start) > EPS:
            errors.append(f"{label} is not contiguous with the previous segment")
        expected_audio_start = audio_end

        visuals = item.get("visual_items")
        if not isinstance(visuals, list):
            errors.append(f"{label}.visual_items must be a list")
            continue
        if require_visuals and not visuals:
            errors.append(f"{label}.visual_items must not be empty")
            continue

        expected_visual_start = audio_start
        for visual_index, visual in enumerate(visuals):
            visual_label = f"{label}.visual_items[{visual_index}]"
            visual_id = visual.get("timeline_item_id")
            if not isinstance(visual_id, str) or not visual_id:
                errors.append(f"{visual_label}.timeline_item_id is required")
            elif visual_id in seen_visuals:
                errors.append(f"duplicate timeline_item_id {visual_id}")
            else:
                seen_visuals.add(visual_id)

            if not visual.get("source_path"):
                errors.append(f"{visual_label}.source_path is required")
            try:
                clip_start = float(visual["clip_start"])
                clip_end = float(visual["clip_end"])
                timeline_start = float(visual["timeline_start"])
                timeline_end = float(visual["timeline_end"])
                speed = float(visual.get("speed", 1.0))
            except (KeyError, TypeError, ValueError):
                errors.append(f"{visual_label} has invalid timing")
                continue

            if clip_end <= clip_start or timeline_end <= timeline_start:
                errors.append(f"{visual_label} must have positive duration")
            if not MIN_SPEED <= speed <= MAX_SPEED:
                errors.append(f"{visual_label}.speed is outside the supported range")
            if abs(timeline_start - expected_visual_start) > EPS:
                errors.append(f"{visual_label} is not contiguous within its segment")
            expected_visual_start = timeline_end

            source_duration = (clip_end - clip_start) / speed
            timeline_duration = timeline_end - timeline_start
            if abs(source_duration - timeline_duration) > 0.02:
                errors.append(f"{visual_label} source and timeline durations differ")

        if visuals and abs(expected_visual_start - audio_end) > EPS:
            errors.append(f"{label}.visual_items do not cover the full segment")

    if audio_duration is not None and abs(expected_audio_start - audio_duration) > EPS:
        errors.append("timeline does not cover the full audio duration")
    return errors


def validate_timeline_contract(
    timeline: dict[str, Any],
    *,
    audio_duration: float | None = None,
    require_visuals: bool = True,
) -> None:
    errors = timeline_contract_errors(
        timeline,
        audio_duration=audio_duration,
        require_visuals=require_visuals,
    )
    if errors:
        raise ValueError("; ".join(errors))
