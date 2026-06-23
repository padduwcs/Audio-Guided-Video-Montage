"""Loader for Review UI (Stage 7).

Trách nhiệm:
- Load và parse 5 file JSON: timeline, matching_candidates, clip_metadata, audio_segments, media_metadata.
- Validate fail-fast: file tồn tại, parse được, project_id khớp.
- Build index cross-file: segments_by_id, clips_by_id, videos_by_id, candidate_sets_by_id, candidate_sets_by_segment_id.
"""

import json
import os

class ProjectData:
    """Container for all loaded project data and cross-file indexes."""
    def __init__(self, timeline, matching_candidates, clip_metadata, audio_segments, media_metadata):
        self.timeline = timeline
        self.matching_candidates = matching_candidates
        self.clip_metadata = clip_metadata
        self.audio_segments = audio_segments
        self.media_metadata = media_metadata

        # Build indexes for fast lookup
        self.segments_by_id = {item["segment_id"]: item for item in audio_segments.get("items", [])}
        self.clips_by_id = {item["clip_id"]: item for item in clip_metadata.get("items", [])}
        self.videos_by_id = {item["video_id"]: item for item in media_metadata.get("videos", [])}
        self.candidate_sets_by_id = {item["candidate_set_id"]: item for item in matching_candidates.get("items", [])}
        self.candidate_sets_by_segment_id = {item["audio_segment_id"]: item for item in matching_candidates.get("items", [])}

def _load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON {path}: {e}")
    if not isinstance(data, dict):
        raise ValueError(f"Top-level JSON must be object, got {type(data)} in {path}")
    return data

def load_project_data(
    timeline_path,
    matching_candidates_path,
    clip_metadata_path,
    audio_segments_path,
    media_metadata_path,
    project_id=None
):
    """Load and validate all project data for Review UI."""
    timeline = _load_json(timeline_path)
    matching_candidates = _load_json(matching_candidates_path)
    clip_metadata = _load_json(clip_metadata_path)
    audio_segments = _load_json(audio_segments_path)
    media_metadata = _load_json(media_metadata_path)

    # Fail-fast: check schema_version, project_id
    for name, obj in [
        ("timeline.json", timeline),
        ("matching_candidates.json", matching_candidates),
        ("clip_metadata.json", clip_metadata),
        ("audio_segments.json", audio_segments),
        ("media_metadata.json", media_metadata),
    ]:
        if "schema_version" not in obj:
            raise ValueError(f"{name} missing schema_version")
        if "project_id" not in obj:
            raise ValueError(f"{name} missing project_id")
        if project_id is not None and obj["project_id"] != project_id:
            raise ValueError(f"{name} project_id mismatch: expected {project_id}, got {obj['project_id']}")

    return ProjectData(
        timeline=timeline,
        matching_candidates=matching_candidates,
        clip_metadata=clip_metadata,
        audio_segments=audio_segments,
        media_metadata=media_metadata,
    )
