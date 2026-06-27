"""Internal data models used by Audio Analyzer."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class ASRChunk:
    """A timestamped piece of transcript returned by an ASR backend."""

    start: float
    end: float
    text: str
    confidence: float | None = None
    timestamp_estimated: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.start, (int, float))
            or isinstance(self.start, bool)
            or self.start < 0
        ):
            raise ValueError("ASR chunk start must be a number greater than or equal to 0")
        if (
            not isinstance(self.end, (int, float))
            or isinstance(self.end, bool)
            or self.end <= self.start
        ):
            raise ValueError("ASR chunk end must be a number greater than start")
        if not isinstance(self.text, str):
            raise TypeError("ASR chunk text must be a string")
        if self.confidence is not None and (
            not isinstance(self.confidence, (int, float))
            or isinstance(self.confidence, bool)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("ASR chunk confidence must be null or a number in [0.0, 1.0]")
        if not isinstance(self.timestamp_estimated, bool):
            raise TypeError("ASR chunk timestamp_estimated must be boolean")

        # Normalize numeric values without changing text or inventing confidence.
        object.__setattr__(self, "start", float(self.start))
        object.__setattr__(self, "end", float(self.end))
        if self.confidence is not None:
            object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True)
class AudioSegment:
    """An internal, time-aligned transcript segment."""

    segment_id: str
    start: float
    end: float
    duration: float
    text: str
    confidence: float | None = None
    timestamp_estimated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.segment_id, str) or not re.fullmatch(
            r"a\d{3,}", self.segment_id
        ):
            raise ValueError("audio segment ID must match 'a001', 'a002', ...")
        if (
            not isinstance(self.start, (int, float))
            or isinstance(self.start, bool)
            or self.start < 0
        ):
            raise ValueError(
                "audio segment start must be a number greater than or equal to 0"
            )
        if (
            not isinstance(self.end, (int, float))
            or isinstance(self.end, bool)
            or self.end <= self.start
        ):
            raise ValueError("audio segment end must be a number greater than start")
        if not isinstance(self.duration, (int, float)) or isinstance(
            self.duration, bool
        ):
            raise ValueError("audio segment duration must be a number")
        if abs(float(self.duration) - (float(self.end) - float(self.start))) > 1e-9:
            raise ValueError("audio segment duration must equal end - start")
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("audio segment text must be a non-empty string")
        if self.confidence is not None and (
            not isinstance(self.confidence, (int, float))
            or isinstance(self.confidence, bool)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError(
                "audio segment confidence must be null or a number in [0.0, 1.0]"
            )
        if not isinstance(self.timestamp_estimated, bool):
            raise TypeError("audio segment timestamp_estimated must be boolean")

        object.__setattr__(self, "start", float(self.start))
        object.__setattr__(self, "end", float(self.end))
        object.__setattr__(self, "duration", float(self.duration))
        if self.confidence is not None:
            object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True)
class EnrichedAudioSegment:
    """An AudioSegment plus deterministic, internal NLP enrichment."""

    segment: AudioSegment
    query: str
    keywords: tuple[str, ...]
    segment_type: str
    needs_review: bool
    review_reasons: tuple[str, ...]
    translated_query: None = None
    query_candidates: tuple[str, ...] = ()
    query_strategy: str = "rules"
    query_fallback_reason: str | None = None
    query_visual_suitability: float = 0.0
    query_candidate_evaluations: tuple[dict[str, Any], ...] = ()
