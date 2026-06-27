from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SAMPLE_TO_RUNTIME = {
    "media_metadata_sample.json": "media_metadata.json",
    "audio_segments_sample.json": "audio_segments.json",
    "clip_metadata_sample.json": "clip_metadata.json",
    "embedding_metadata_sample.json": "embedding_metadata.json",
    "matching_candidates_sample.json": "matching_candidates.json",
    "render_config_sample.json": "render_config.json",
    "render_log_sample.json": "render_log.json",
}


@dataclass(frozen=True)
class Stage:
    number: int
    name: str
    description: str


STAGES: tuple[Stage, ...] = (
    Stage(1, "input_processor", "Input Processor"),
    Stage(2, "audio_analyzer", "Audio Analyzer"),
    Stage(3, "video_analyzer", "Video Analyzer"),
    Stage(4, "embedding_indexer", "Embedding Indexer"),
    Stage(5, "matching_engine", "Matching Engine"),
    Stage(6, "timeline_planner", "Timeline Planner"),
    Stage(7, "review_ui", "Review UI"),
    Stage(8, "renderer", "Renderer"),
)

STAGE_BY_NUMBER = {stage.number: stage for stage in STAGES}


def stage_numbers(from_stage: int, to_stage: int) -> list[int]:
    if from_stage > to_stage:
        raise ValueError(f"from-stage ({from_stage}) must be <= to-stage ({to_stage})")
    return list(range(from_stage, to_stage + 1))
