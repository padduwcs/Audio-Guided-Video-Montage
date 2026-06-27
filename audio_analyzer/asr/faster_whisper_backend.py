"""Real ASR backend powered by faster-whisper."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from audio_analyzer.asr.base import ASRBackend
from audio_analyzer.models import ASRChunk


ModelFactory = Callable[..., Any]


class FasterWhisperBackendError(RuntimeError):
    """Raised when faster-whisper cannot load or transcribe audio."""


class FasterWhisperBackend(ASRBackend):
    """Lazy faster-whisper adapter that returns backend-neutral ASR chunks."""

    def __init__(
        self,
        *,
        model: str = "base",
        language: str = "auto",
        device: str = "cpu",
        compute_type: str = "int8",
        model_factory: ModelFactory | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        if language not in {"auto", "vi", "en"}:
            raise ValueError("language must be one of: auto, vi, en")
        if not isinstance(device, str) or not device.strip():
            raise ValueError("device must be a non-empty string")
        if not isinstance(compute_type, str) or not compute_type.strip():
            raise ValueError("compute_type must be a non-empty string")

        self._model_name = model
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model_factory = model_factory
        self._model: Any | None = None

    @property
    def backend_name(self) -> str:
        return "faster-whisper"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _resolve_model_factory(self) -> ModelFactory:
        if self._model_factory is not None:
            return self._model_factory
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:
            raise FasterWhisperBackendError(
                "cannot import faster-whisper; install requirements.txt and verify "
                f"its native runtime dependencies before running real ASR: {exc}"
            ) from exc
        return WhisperModel

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        factory = self._resolve_model_factory()
        try:
            self._model = factory(
                self._model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:
            raise FasterWhisperBackendError(
                f"failed to load faster-whisper model {self._model_name!r} "
                f"on device {self.device!r} with compute type {self.compute_type!r}: {exc}"
            ) from exc
        return self._model

    def transcribe(self, audio_path: Path) -> list[ASRChunk]:
        """Transcribe the supplied path without assuming a fixed filename."""

        audio_path = Path(audio_path)
        if not audio_path.is_file():
            raise FasterWhisperBackendError(
                f"audio file does not exist or is not a file: {audio_path}"
            )

        model = self._load_model()
        try:
            transcribe_options: dict[str, Any] = {
                "language": None if self.language == "auto" else self.language,
                "task": "transcribe",
            }
            if self.language == "auto":
                transcribe_options["multilingual"] = True
            segments, _info = model.transcribe(
                str(audio_path),
                **transcribe_options,
            )
            chunks = [
                ASRChunk(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    # faster-whisper segments expose avg_logprob, not a direct
                    # calibrated confidence. We deliberately do not convert it.
                    confidence=None,
                )
                for segment in segments
            ]
        except Exception as exc:
            raise FasterWhisperBackendError(
                f"faster-whisper failed to decode or transcribe {audio_path}: {exc}"
            ) from exc
        return chunks
