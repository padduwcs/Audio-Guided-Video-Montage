"""Injected-backend Audio Analyzer pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audio_analyzer.asr import ASRBackend
from audio_analyzer.enrichment import enrich_segments
from audio_analyzer.metadata import AudioInput, load_audio_input
from audio_analyzer.models import ASRChunk, EnrichedAudioSegment
from audio_analyzer.output import (
    build_audio_segments_document,
    validate_audio_segments_document,
    write_json_atomic,
)
from audio_analyzer.segmentation import create_segments_with_report
from audio_analyzer.transcript import clean_transcript_chunks
from audio_analyzer.timestamps import align_chunks_to_audio_duration


Clock = Callable[[], datetime]


class PipelineError(RuntimeError):
    """Raised when Audio Analyzer cannot produce a valid output."""


@dataclass(frozen=True)
class PipelineResult:
    audio_segments_path: Path
    analysis_log_path: Path
    segment_count: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_timestamp(clock: Clock) -> str:
    value = clock()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _raw_chunk_document(chunk: ASRChunk) -> dict[str, Any]:
    return {
        "start": chunk.start,
        "end": chunk.end,
        "text": chunk.text,
        "confidence": chunk.confidence,
    }


def _review_document(segments: list[EnrichedAudioSegment]) -> list[dict[str, Any]]:
    return [
        {
            "segment_id": enriched.segment.segment_id,
            "reasons": list(enriched.review_reasons),
            "timestamp_estimated": enriched.segment.timestamp_estimated,
        }
        for enriched in segments
        if enriched.needs_review
    ]


def _base_log(backend: ASRBackend, started_at: str) -> dict[str, Any]:
    return {
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "asr": {
            "backend": backend.backend_name,
            "model": backend.model_name,
        },
        "project_id": None,
        "audio_id": None,
        "audio_path": None,
        "raw_asr_chunks": [],
        "segmentation_events": [],
        "timestamp_adjustments": [],
        "review_segments": [],
        "warnings": [],
        "errors": [],
    }


def run_pipeline(
    *,
    media_metadata_path: Path,
    output_dir: Path,
    asr_backend: ASRBackend,
    overwrite: bool = False,
    language: str = "vi",
    project_root: Path | None = None,
    clock: Clock = _utc_now,
) -> PipelineResult:
    """Run Stage 2 with an injected ASR backend and atomically write artifacts."""

    if not isinstance(asr_backend, ASRBackend):
        raise TypeError("asr_backend must implement ASRBackend")

    output_dir = output_dir.resolve()
    audio_segments_path = output_dir / "audio_segments.json"
    analysis_log_path = output_dir / "audio_analysis_log.json"
    if audio_segments_path.exists() and not overwrite:
        raise PipelineError(
            f"output already exists: {audio_segments_path}; use overwrite=True to replace it"
        )

    started_at = _iso_timestamp(clock)
    analysis_log = _base_log(asr_backend, started_at)
    audio_input: AudioInput | None = None

    try:
        root = (project_root or Path.cwd()).resolve()
        audio_input = load_audio_input(media_metadata_path, root)
        analysis_log.update(
            {
                "project_id": audio_input.project_id,
                "audio_id": audio_input.audio_id,
                "audio_path": str(audio_input.normalized_path),
            }
        )
        if audio_input.status == "warning":
            analysis_log["warnings"].append("media_metadata audio.status is 'warning'")

        raw_chunks = list(asr_backend.transcribe(audio_input.normalized_path))
        analysis_log["raw_asr_chunks"] = [
            _raw_chunk_document(chunk) for chunk in raw_chunks
        ]
        cleaned_chunks = clean_transcript_chunks(raw_chunks)
        if not cleaned_chunks:
            raise PipelineError("ASR backend returned no non-empty transcript chunks")

        timestamp_alignment = align_chunks_to_audio_duration(
            cleaned_chunks,
            audio_duration=audio_input.duration,
        )
        cleaned_chunks = list(timestamp_alignment.chunks)
        analysis_log["timestamp_adjustments"] = list(
            timestamp_alignment.adjustments
        )
        for adjustment in timestamp_alignment.adjustments:
            analysis_log["warnings"].append(
                "clamped ASR chunk "
                f"{adjustment['chunk_index']} end from "
                f"{adjustment['original_end']:.3f}s to "
                f"{adjustment['adjusted_end']:.3f}s"
            )

        segmentation = create_segments_with_report(cleaned_chunks)
        enriched_segments = enrich_segments(segmentation.segments)
        analysis_log["segmentation_events"] = list(segmentation.events)
        analysis_log["review_segments"] = _review_document(enriched_segments)

        created_at = _iso_timestamp(clock)
        document = build_audio_segments_document(
            project_id=audio_input.project_id,
            audio_id=audio_input.audio_id,
            created_at=created_at,
            segments=enriched_segments,
            language=language,
        )
        validate_audio_segments_document(
            document,
            audio_duration=audio_input.duration,
        )

        analysis_log["finished_at"] = _iso_timestamp(clock)
        analysis_log["status"] = "success"
        write_json_atomic(audio_segments_path, document)
        write_json_atomic(analysis_log_path, analysis_log)
        return PipelineResult(
            audio_segments_path=audio_segments_path,
            analysis_log_path=analysis_log_path,
            segment_count=len(enriched_segments),
        )
    except Exception as exc:
        analysis_log["finished_at"] = _iso_timestamp(clock)
        analysis_log["status"] = "failed"
        analysis_log["errors"].append(str(exc))
        try:
            write_json_atomic(analysis_log_path, analysis_log)
        except OSError:
            pass
        if isinstance(exc, PipelineError):
            raise
        raise PipelineError(f"audio analysis pipeline failed: {exc}") from exc
