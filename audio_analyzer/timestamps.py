"""Reconcile ASR timestamps with the authoritative source audio duration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from audio_analyzer.models import ASRChunk


@dataclass(frozen=True)
class TimestampAlignmentResult:
    chunks: tuple[ASRChunk, ...]
    adjustments: tuple[dict[str, Any], ...]


def align_chunks_to_audio_duration(
    chunks: list[ASRChunk],
    *,
    audio_duration: float,
) -> TimestampAlignmentResult:
    """Clamp overlapping chunks and discard chunks fully outside the audio."""

    if audio_duration <= 0:
        raise ValueError("audio_duration must be greater than 0")

    indexed_chunks = list(enumerate(chunks))
    ordered_chunks = sorted(
        indexed_chunks,
        key=lambda item: (item[1].start, item[1].end, item[0]),
    )

    adjustments: list[dict[str, Any]] = []
    if [index for index, _chunk in ordered_chunks] != list(range(len(chunks))):
        adjustments.append(
            {
                "reason": "chunks_reordered_by_timestamp",
                "original_order": list(range(len(chunks))),
                "adjusted_order": [index for index, _chunk in ordered_chunks],
            }
        )

    bounded: list[tuple[int, ASRChunk]] = []
    for index, chunk in ordered_chunks:
        if chunk.start >= audio_duration:
            adjustments.append(
                {
                    "chunk_index": index,
                    "original_start": chunk.start,
                    "original_end": chunk.end,
                    "adjusted_end": None,
                    "overrun_seconds": chunk.end - audio_duration,
                    "reason": "chunk_outside_audio_discarded",
                }
            )
            continue

        if chunk.end <= audio_duration:
            bounded.append((index, chunk))
            continue

        overrun = chunk.end - audio_duration
        bounded.append(
            (
                index,
                ASRChunk(
                    start=chunk.start,
                    end=audio_duration,
                    text=chunk.text,
                    confidence=chunk.confidence,
                    timestamp_estimated=True,
                ),
            )
        )
        adjustments.append(
            {
                "chunk_index": index,
                "original_end": chunk.end,
                "adjusted_end": audio_duration,
                "overrun_seconds": overrun,
                "reason": "end_overrun_clamped_to_audio_duration",
            }
        )

    aligned: list[tuple[int, ASRChunk]] = []
    for index, chunk in bounded:
        if aligned and chunk.start < aligned[-1][1].end:
            previous_index, previous = aligned[-1]
            overlap_start = max(previous.start, chunk.start)
            overlap_end = min(previous.end, chunk.end)
            boundary = (overlap_start + overlap_end) / 2.0

            aligned[-1] = (
                previous_index,
                ASRChunk(
                    start=previous.start,
                    end=boundary,
                    text=previous.text,
                    confidence=previous.confidence,
                    timestamp_estimated=True,
                ),
            )
            chunk = ASRChunk(
                start=boundary,
                end=chunk.end,
                text=chunk.text,
                confidence=chunk.confidence,
                timestamp_estimated=True,
            )
            adjustments.append(
                {
                    "reason": "overlap_split_at_midpoint",
                    "left_chunk_index": previous_index,
                    "right_chunk_index": index,
                    "overlap_start": overlap_start,
                    "overlap_end": overlap_end,
                    "boundary": boundary,
                }
            )
        aligned.append((index, chunk))

    return TimestampAlignmentResult(
        chunks=tuple(chunk for _index, chunk in aligned),
        adjustments=tuple(adjustments),
    )
