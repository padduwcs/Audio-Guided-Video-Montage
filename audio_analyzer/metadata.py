"""Read and validate the normalized audio input from media metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


USABLE_AUDIO_STATUSES = {"ready", "warning"}


class MetadataValidationError(ValueError):
    """Raised when media metadata cannot provide a usable audio input."""


@dataclass(frozen=True)
class AudioInput:
    """Validated information needed by later Audio Analyzer phases."""

    project_id: str
    audio_id: str
    status: str
    normalized_path: Path
    duration: float


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise MetadataValidationError(
            f"media metadata file does not exist: {path}"
        ) from exc
    except OSError as exc:
        raise MetadataValidationError(
            f"cannot read media metadata file {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise MetadataValidationError(
            f"invalid JSON in media metadata file {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise MetadataValidationError("media metadata must be a JSON object")
    return data


def load_audio_input(metadata_path: Path, project_root: Path) -> AudioInput:
    """Load and validate the audio entry in ``media_metadata.json``.

    Contract paths are relative to the project root. Absolute paths are rejected
    so the metadata remains portable between machines.
    """

    metadata_path = metadata_path.resolve()
    project_root = project_root.resolve()
    metadata = _load_json(metadata_path)

    project_id = metadata.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise MetadataValidationError("project_id must be a non-empty string")

    audio = metadata.get("audio")
    if not isinstance(audio, dict):
        raise MetadataValidationError(
            "media metadata must contain an 'audio' object"
        )

    audio_id = audio.get("audio_id")
    if not isinstance(audio_id, str) or not audio_id:
        raise MetadataValidationError("audio.audio_id must be a non-empty string")

    status = audio.get("status")
    if not isinstance(status, str) or not status:
        raise MetadataValidationError("audio.status must be a non-empty string")
    if status == "error":
        raise MetadataValidationError(
            "audio.status is 'error'; the normalized audio is not usable"
        )
    if status not in USABLE_AUDIO_STATUSES:
        raise MetadataValidationError(
            "audio.status must be 'ready' or 'warning' "
            f"(received {status!r})"
        )

    normalized_path_value = audio.get("normalized_path")
    if not isinstance(normalized_path_value, str) or not normalized_path_value.strip():
        raise MetadataValidationError(
            "audio.normalized_path must be a non-empty string"
        )

    contract_path = Path(normalized_path_value)
    if contract_path.is_absolute():
        raise MetadataValidationError(
            "audio.normalized_path must be relative to the project root"
        )

    duration = audio.get("duration")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or duration <= 0
    ):
        raise MetadataValidationError("audio.duration must be a number greater than 0")

    normalized_path = (project_root / contract_path).resolve()
    try:
        normalized_path.relative_to(project_root)
    except ValueError as exc:
        raise MetadataValidationError(
            "audio.normalized_path must stay inside the project root"
        ) from exc

    if not normalized_path.is_file():
        raise MetadataValidationError(
            "normalized audio file does not exist or is not a file: "
            f"{normalized_path}"
        )

    return AudioInput(
        project_id=project_id,
        audio_id=audio_id,
        status=status,
        normalized_path=normalized_path,
        duration=float(duration),
    )
