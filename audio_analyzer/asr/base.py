"""Backend-independent ASR interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from audio_analyzer.models import ASRChunk


class ASRBackend(ABC):
    """Convert an audio file into timestamped transcript chunks."""

    @property
    def backend_name(self) -> str:
        """Stable backend identifier used in analysis logs."""

        return type(self).__name__

    @property
    def model_name(self) -> str | None:
        """Model identifier when the backend uses one."""

        return None

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Iterable[ASRChunk]:
        """Return raw chunks without segmentation or NLP enrichment."""
