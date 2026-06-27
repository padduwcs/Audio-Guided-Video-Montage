"""Minimal, meaning-preserving cleanup for raw ASR transcript chunks."""

from __future__ import annotations

from collections.abc import Iterable

from audio_analyzer.models import ASRChunk


def normalize_whitespace(text: str) -> str:
    """Collapse Unicode whitespace without rewriting transcript content."""

    if not isinstance(text, str):
        raise TypeError("transcript text must be a string")
    return " ".join(text.split())


def clean_transcript_chunks(chunks: Iterable[ASRChunk]) -> list[ASRChunk]:
    """Normalize whitespace and discard chunks with no spoken text.

    Timestamps and confidence values are copied exactly. This phase does not
    merge, split, summarize, translate, or enrich chunks.
    """

    cleaned_chunks: list[ASRChunk] = []
    for chunk in chunks:
        if not isinstance(chunk, ASRChunk):
            raise TypeError("all transcript chunks must be ASRChunk instances")

        cleaned_text = normalize_whitespace(chunk.text)
        if not cleaned_text:
            continue

        cleaned_chunks.append(
            ASRChunk(
                start=chunk.start,
                end=chunk.end,
                text=cleaned_text,
                confidence=chunk.confidence,
                timestamp_estimated=chunk.timestamp_estimated,
            )
        )

    return cleaned_chunks
