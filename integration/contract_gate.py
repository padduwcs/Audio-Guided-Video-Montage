from __future__ import annotations

from typing import Any

from review_ui.loader import ProjectData
from review_ui.validator import validate_project_data


class DraftContractError(ValueError):
    pass


def validate_draft_payloads(
    *,
    media_metadata: dict[str, Any],
    audio_segments: dict[str, Any],
    clip_metadata: dict[str, Any],
    embedding_metadata: dict[str, Any],
    matching_candidates: dict[str, Any],
    timeline: dict[str, Any],
) -> None:
    """Validate the complete Stage 1-6 handoff before publishing a draft."""

    payloads = {
        "media_metadata": media_metadata,
        "audio_segments": audio_segments,
        "clip_metadata": clip_metadata,
        "embedding_metadata": embedding_metadata,
        "matching_candidates": matching_candidates,
        "timeline": timeline,
    }
    project_ids = {payload.get("project_id") for payload in payloads.values()}
    if len(project_ids) != 1 or None in project_ids:
        raise DraftContractError(
            f"project_id mismatch across Stage 1-6 artifacts: {sorted(map(str, project_ids))}"
        )

    project_data = ProjectData(
        timeline=timeline,
        matching_candidates=matching_candidates,
        clip_metadata=clip_metadata,
        audio_segments=audio_segments,
        media_metadata=media_metadata,
    )
    review_errors = [
        message
        for message in validate_project_data(project_data, mode="renderer_handoff")
        if message.level == "error"
    ]
    if review_errors:
        raise DraftContractError(
            "draft handoff is invalid: "
            + "; ".join(message.message for message in review_errors)
        )

    segment_ids = set(project_data.segments_by_id)
    embedded_segment_ids = {
        item.get("segment_id")
        for item in embedding_metadata.get("text_embeddings", [])
    }
    if embedded_segment_ids != segment_ids:
        raise DraftContractError(
            "text embedding coverage does not match audio segments"
        )

    expected_clip_ids = {
        clip_id
        for clip_id, clip in project_data.clips_by_id.items()
        if clip.get("status", "usable") not in {"too_short", "error"}
    }
    embedded_clip_ids = {
        item.get("clip_id")
        for item in embedding_metadata.get("visual_embeddings", [])
    }
    if not expected_clip_ids.issubset(embedded_clip_ids):
        raise DraftContractError(
            "visual embedding coverage is missing usable clips"
        )
