"""Test-only ASR doubles."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from audio_analyzer.asr import ASRBackend
from audio_analyzer.models import ASRChunk


class FakeASRBackend(ASRBackend):
    """Return predefined chunks and record which audio paths were requested."""

    def __init__(
        self,
        chunks: Iterable[ASRChunk],
        *,
        backend_name: str = "fake",
        model_name: str | None = "fixture-model",
        error: Exception | None = None,
    ) -> None:
        self._chunks = tuple(chunks)
        self._backend_name = backend_name
        self._model_name = model_name
        self._error = error
        self.calls: list[Path] = []

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def model_name(self) -> str | None:
        return self._model_name

    def transcribe(self, audio_path: Path) -> tuple[ASRChunk, ...]:
        self.calls.append(audio_path)
        if self._error is not None:
            raise self._error
        return self._chunks
