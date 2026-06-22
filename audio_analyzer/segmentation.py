"""Create internal audio segments from cleaned ASR chunks."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from audio_analyzer.models import ASRChunk, AudioSegment
from audio_analyzer.transcript import clean_transcript_chunks


@dataclass(frozen=True)
class SegmentationConfig:
    """Timing rules for deterministic MVP segmentation."""

    min_duration: float = 2.0
    max_duration: float = 8.0
    max_merge_gap: float = 0.75
    max_sentence_duration: float = 30.0

    def __post_init__(self) -> None:
        if self.min_duration <= 0:
            raise ValueError("min_duration must be greater than 0")
        if self.max_duration < self.min_duration:
            raise ValueError("max_duration must be greater than or equal to min_duration")
        if self.max_merge_gap < 0:
            raise ValueError("max_merge_gap must be greater than or equal to 0")
        if self.max_sentence_duration < self.max_duration:
            raise ValueError(
                "max_sentence_duration must be greater than or equal to max_duration"
            )


@dataclass(frozen=True)
class SegmentationResult:
    segments: tuple[AudioSegment, ...]
    events: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class _SegmentPart:
    start: float
    end: float
    text: str
    confidence: float | None
    timestamp_estimated: bool = False

    @property
    def duration(self) -> float:
        return self.end - self.start


_SENTENCE_PATTERN = re.compile(r".+?(?:[.!?…]+(?=\s|$)|$)")
_SENTENCE_END_PATTERN = re.compile(r"[.!?…]+[\"')\]}]*\s*$")


def _sentence_parts(text: str) -> list[str]:
    """Split only at explicit punctuation and preserve every spoken token."""

    return [match.group(0).strip() for match in _SENTENCE_PATTERN.finditer(text) if match.group(0).strip()]


def _split_long_part(
    part: _SegmentPart,
    max_duration: float,
    events: list[dict[str, Any]],
) -> list[_SegmentPart]:
    if part.duration <= max_duration:
        return [part]

    sentences = _sentence_parts(part.text)
    if len(sentences) <= 1:
        # There is no trustworthy textual boundary. Keeping one long segment is
        # safer than splitting it into words or arbitrary equal-sized pieces.
        events.append(
            {
                "type": "retained_long_no_safe_boundary",
                "source_start": part.start,
                "source_end": part.end,
            }
        )
        return [part]

    weights = [max(len(sentence.replace(" ", "")), 1) for sentence in sentences]
    total_weight = sum(weights)
    chunk_duration = part.duration
    parts: list[_SegmentPart] = []
    current_start = part.start

    for index, (sentence, weight) in enumerate(zip(sentences, weights)):
        if index == len(sentences) - 1:
            current_end = part.end
        else:
            current_end = current_start + chunk_duration * weight / total_weight
        parts.append(
            _SegmentPart(
                current_start,
                current_end,
                sentence,
                part.confidence,
                timestamp_estimated=True,
            )
        )
        current_start = current_end

    events.append(
        {
            "type": "split",
            "source_start": part.start,
            "source_end": part.end,
            "output_count": len(parts),
            "timestamp_estimated": True,
        }
    )

    return parts


def _validate_order_and_overlap(chunks: list[ASRChunk]) -> None:
    previous_start = -1.0
    previous_end = -1.0
    for chunk in chunks:
        if chunk.start < previous_start:
            raise ValueError("ASR chunks must be sorted by increasing start timestamp")
        if chunk.start < previous_end:
            raise ValueError("ASR chunks must not overlap")
        previous_start = chunk.start
        previous_end = chunk.end


def _can_merge(left: _SegmentPart, right: _SegmentPart, config: SegmentationConfig) -> bool:
    gap = right.start - left.end
    combined_duration = right.end - left.start
    return 0 <= gap <= config.max_merge_gap and combined_duration <= config.max_duration


def _merge(left: _SegmentPart, right: _SegmentPart) -> _SegmentPart:
    known_confidences = [
        value for value in (left.confidence, right.confidence) if value is not None
    ]
    return _SegmentPart(
        start=left.start,
        end=right.end,
        text=f"{left.text} {right.text}",
        # The lowest known value is a conservative aggregate. If neither source
        # has confidence, it remains null rather than being invented.
        confidence=min(known_confidences) if known_confidences else None,
        timestamp_estimated=left.timestamp_estimated or right.timestamp_estimated,
    )


def _part_from_chunk(chunk: ASRChunk) -> _SegmentPart:
    return _SegmentPart(
        start=chunk.start,
        end=chunk.end,
        text=chunk.text,
        confidence=chunk.confidence,
        timestamp_estimated=chunk.timestamp_estimated,
    )


def _ends_sentence(text: str) -> bool:
    return bool(_SENTENCE_END_PATTERN.search(text))


def _reassemble_sentences(
    chunks: list[ASRChunk],
    config: SegmentationConfig,
    events: list[dict[str, Any]],
) -> list[_SegmentPart]:
    """Join ASR timing chunks until their transcript reaches a sentence end."""

    if not chunks:
        return []

    assembled: list[_SegmentPart] = []
    current = _part_from_chunk(chunks[0])
    for chunk in chunks[1:]:
        right = _part_from_chunk(chunk)
        if _ends_sentence(current.text):
            assembled.append(current)
            current = right
            continue

        gap = right.start - current.end
        combined_duration = right.end - current.start
        if gap > config.max_merge_gap:
            events.append(
                {
                    "type": "retained_incomplete_boundary",
                    "source_start": current.start,
                    "source_end": current.end,
                    "next_start": right.start,
                    "gap": gap,
                    "reason": "large_gap_before_sentence_completion",
                }
            )
            assembled.append(current)
            current = right
            continue
        if combined_duration > config.max_sentence_duration:
            events.append(
                {
                    "type": "retained_incomplete_boundary",
                    "source_start": current.start,
                    "source_end": current.end,
                    "next_start": right.start,
                    "combined_duration": combined_duration,
                    "reason": "sentence_reassembly_duration_limit",
                }
            )
            assembled.append(current)
            current = right
            continue

        left = current
        current = _merge(left, right)
        events.append(
            {
                "type": "merge",
                "left_start": left.start,
                "left_end": left.end,
                "right_start": right.start,
                "right_end": right.end,
                "combined_duration": current.duration,
                "reason": "sentence_continuation",
            }
        )

    assembled.append(current)
    return assembled


def create_segments(
    chunks: Iterable[ASRChunk],
    config: SegmentationConfig | None = None,
) -> list[AudioSegment]:
    """Create stable, non-overlapping segments from ASR chunks.

    Input order is significant and must already follow the audio timeline.
    Empty chunks are defensively discarded by the Phase 2A cleanup function.
    """

    return list(create_segments_with_report(chunks, config).segments)


def create_segments_with_report(
    chunks: Iterable[ASRChunk],
    config: SegmentationConfig | None = None,
) -> SegmentationResult:
    """Create segments and retain internal merge/split diagnostics."""

    rules = config or SegmentationConfig()
    cleaned_chunks = clean_transcript_chunks(chunks)
    _validate_order_and_overlap(cleaned_chunks)

    events: list[dict[str, Any]] = []
    parts: list[_SegmentPart] = []
    sentence_parts = _reassemble_sentences(cleaned_chunks, rules, events)
    for part in sentence_parts:
        parts.extend(_split_long_part(part, rules.max_duration, events))

    merged_parts: list[_SegmentPart] = []
    for part in parts:
        if (
            merged_parts
            and merged_parts[-1].duration < rules.min_duration
            and not _ends_sentence(merged_parts[-1].text)
        ):
            if _can_merge(merged_parts[-1], part, rules):
                left = merged_parts[-1]
                merged_parts[-1] = _merge(merged_parts[-1], part)
                events.append(
                    {
                        "type": "merge",
                        "left_start": left.start,
                        "left_end": left.end,
                        "right_start": part.start,
                        "right_end": part.end,
                        "reason": "short_duration",
                    }
                )
                continue

        if (
            part.duration < rules.min_duration
            and merged_parts
            and not _ends_sentence(merged_parts[-1].text)
        ):
            if _can_merge(merged_parts[-1], part, rules):
                left = merged_parts[-1]
                merged_parts[-1] = _merge(merged_parts[-1], part)
                events.append(
                    {
                        "type": "merge",
                        "left_start": left.start,
                        "left_end": left.end,
                        "right_start": part.start,
                        "right_end": part.end,
                        "reason": "short_duration",
                    }
                )
                continue

        merged_parts.append(part)

    segments = tuple(
        AudioSegment(
            segment_id=f"a{index:03d}",
            start=part.start,
            end=part.end,
            duration=part.end - part.start,
            text=part.text,
            confidence=part.confidence,
            timestamp_estimated=part.timestamp_estimated,
        )
        for index, part in enumerate(merged_parts, start=1)
    )
    return SegmentationResult(segments=segments, events=tuple(events))
