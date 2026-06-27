"""Reconcile small ASR timestamp overruns with the source audio duration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from audio_analyzer.models import ASRChunk


MAX_END_OVERRUN_SECONDS = 0.5


class TimestampAlignmentError(ValueError):
    """Raised when ASR timestamps cannot be safely aligned to the audio."""


@dataclass(frozen=True)
class TimestampAlignmentResult:
    chunks: tuple[ASRChunk, ...]
    adjustments: tuple[dict[str, Any], ...]


def align_chunks_to_audio_duration(
    chunks: list[ASRChunk],
    *,
    audio_duration: float,
    max_end_overrun: float = MAX_END_OVERRUN_SECONDS,
) -> TimestampAlignmentResult:
    """Clamp small end overruns while rejecting materially invalid timestamps."""

    if audio_duration <= 0:
        raise ValueError("audio_duration must be greater than 0")
    if max_end_overrun < 0:
        raise ValueError("max_end_overrun must be greater than or equal to 0")

    aligned: list[ASRChunk] = []
    adjustments: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        if chunk.end <= audio_duration:
            aligned.append(chunk)
            continue

        overrun = chunk.end - audio_duration
        if overrun > max_end_overrun:
            raise TimestampAlignmentError(
                f"ASR chunk {index} ends {overrun:.3f}s after audio duration; "
                f"maximum safe overrun is {max_end_overrun:.3f}s"
            )
        if chunk.start >= audio_duration:
            raise TimestampAlignmentError(
                f"ASR chunk {index} starts at or after audio duration and cannot be clamped"
            )

        aligned.append(
            ASRChunk(
                start=chunk.start,
                end=audio_duration,
                text=chunk.text,
                confidence=chunk.confidence,
                timestamp_estimated=True,
            )
        )
        adjustments.append(
            {
                "chunk_index": index,
                "original_end": chunk.end,
                "adjusted_end": audio_duration,
                "overrun_seconds": overrun,
                "reason": "small_end_overrun_clamped_to_audio_duration",
            }
        )

    return TimestampAlignmentResult(
        chunks=tuple(aligned),
        adjustments=tuple(adjustments),
    )
