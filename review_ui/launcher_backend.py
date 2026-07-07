from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from scripts.kaggle_job import kaggle_command


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
FINAL_VIDEO = DATA_DIR / "final" / "final_video.mp4"

REQUIRED_DRAFT_FILES = (
    "media_metadata.json",
    "audio_segments.json",
    "clip_metadata.json",
    "embedding_metadata.json",
    "matching_candidates.json",
    "timeline.json",
)

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

_review_process: subprocess.Popen | None = None


def _is_inside_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT)
    except ValueError:
        return False
    return True


def _uploaded_path(value) -> Path:
    if isinstance(value, (str, os.PathLike)):
        return Path(value)
    name = getattr(value, "name", None)
    if name:
        return Path(name)
    raise ValueError("Khong doc duoc file upload.")


def _safe_filename(name: str) -> str:
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not stem:
        stem = "input"
    return f"{stem}{suffix}"


def _unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        next_candidate = directory / f"{stem}_{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def read_kaggle_username() -> str:
    env_username = os.environ.get("KAGGLE_USERNAME")
    if env_username:
        return env_username

    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.is_file():
        return ""
    try:
        data = json.loads(kaggle_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(data.get("username") or "")


def save_kaggle_credentials(username: str, api_key: str) -> str:
    username = (username or "").strip()
    api_key = (api_key or "").strip()
    if not username:
        raise ValueError("Vui long nhap Kaggle username.")
    if not api_key:
        raise ValueError("Vui long nhap Kaggle API key.")

    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(parents=True, exist_ok=True)
    kaggle_json = kaggle_dir / "kaggle.json"
    kaggle_json.write_text(
        json.dumps({"username": username, "key": api_key}, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(kaggle_json, 0o600)
    except OSError:
        pass
    return f"Da luu Kaggle API cho user `{username}` tai `{kaggle_json}`."


def check_kaggle_credentials(timeout_seconds: int = 45) -> str:
    username = read_kaggle_username()
    if not username:
        return "Chua tim thay Kaggle API. Hay nhap username va API key roi bam Luu."

    command = kaggle_command("datasets", "list", "--mine")
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return "Khong tim thay Kaggle CLI. Hay cai dependency bang requirements-terminal.txt."
    except subprocess.TimeoutExpired:
        return "Kaggle CLI phan hoi qua lau. Kiem tra internet hoac API key."

    if result.returncode == 0:
        return f"Kaggle da san sang cho user `{username}`."
    return "Kaggle chua san sang:\n" + _tail(result.stdout)


def stage_inputs(video_files: Iterable, audio_file) -> tuple[list[Path], Path, str]:
    video_files = list(video_files or [])
    if not video_files:
        raise ValueError("Hay chon it nhat mot video nguon.")
    if not audio_file:
        raise ValueError("Hay chon mot file voice-over/audio.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    staged_videos: list[Path] = []
    messages: list[str] = []

    for value in video_files:
        source = _uploaded_path(value)
        suffix = source.suffix.lower()
        if suffix not in SUPPORTED_VIDEO_SUFFIXES:
            raise ValueError(f"File video khong ho tro: {source.name}")
        destination = _unique_destination(RAW_DIR, _safe_filename(source.name))
        shutil.copy2(source, destination)
        staged_videos.append(destination)
        messages.append(f"Video: `{destination.relative_to(ROOT)}`")

    audio_source = _uploaded_path(audio_file)
    audio_suffix = audio_source.suffix.lower()
    if audio_suffix not in SUPPORTED_AUDIO_SUFFIXES:
        raise ValueError(f"File audio khong ho tro: {audio_source.name}")
    audio_destination = _unique_destination(RAW_DIR, _safe_filename(audio_source.name))
    shutil.copy2(audio_source, audio_destination)
    messages.append(f"Voice: `{audio_destination.relative_to(ROOT)}`")

    return staged_videos, audio_destination, "\n".join(messages)


def draft_status() -> tuple[bool, str]:
    missing = [name for name in REQUIRED_DRAFT_FILES if not (INTERMEDIATE_DIR / name).is_file()]
    if missing:
        return False, "Chua co ban nhap. Thieu: " + ", ".join(missing)
    return True, "Ban nhap da san sang. Co the mo man hinh chinh sua."


def final_status() -> tuple[bool, str]:
    if FINAL_VIDEO.is_file():
        return True, f"Video cuoi da san sang: `{FINAL_VIDEO.relative_to(ROOT)}`"
    return False, "Chua co video cuoi. Hay render sau khi review."


def run_kaggle_draft(
    videos: list[Path | str],
    audio: Path | str,
    *,
    project_id: str = "demo_01",
    device: str = "cpu",
    compute_type: str = "int8",
    fake_embeddings: bool = False,
):
    if not videos or not audio:
        raise ValueError("Thieu video hoac audio da chon.")
    videos = [Path(path) for path in videos]
    audio = Path(audio)
    for path in [*videos, audio]:
        if not _is_inside_root(path):
            raise ValueError(f"Duong dan phai nam trong repo: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Khong tim thay file: {path}")

    device = (device or "cpu").strip()
    compute_type = (compute_type or "int8").strip()

    command = [
        sys.executable,
        "-B",
        str(ROOT / "scripts" / "kaggle_job.py"),
        "submit",
        "--project-id",
        project_id or "demo_01",
        "--videos",
        *[str(path.relative_to(ROOT)) for path in videos],
        "--audio",
        str(audio.relative_to(ROOT)),
        "--device",
        device,
        "--compute-type",
        compute_type,
        "--wait",
        "--pull",
    ]
    if fake_embeddings:
        command.append("--fake-embeddings")

    yield from _run_command_stream(command, success_message="Da tao ban nhap va tai output ve may.")


def launch_review_server(port: int = 7870) -> str:
    global _review_process

    ready, message = draft_status()
    if not ready:
        return message

    if _review_process and _review_process.poll() is None:
        return f"Review UI dang chay tai http://127.0.0.1:{port}"

    command = [
        sys.executable,
        "-B",
        "-m",
        "integration.run_pipeline",
        "--from-stage",
        "7",
        "--to-stage",
        "7",
        "--launch-ui",
        "--no-ui-backup",
        "--ui-port",
        str(port),
    ]
    _review_process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return f"Da mo Review UI: http://127.0.0.1:{port}"


def run_render_final():
    command = [
        sys.executable,
        "-B",
        "-m",
        "integration.run_pipeline",
        "--from-stage",
        "8",
        "--to-stage",
        "8",
        "--overwrite",
    ]
    yield from _run_command_stream(command, success_message="Da render video cuoi.")


def _run_command_stream(command: list[str], *, success_message: str):
    lines = ["Dang chay lenh..."]
    yield "\n".join(lines)

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    assert process.stdout is not None
    for line in process.stdout:
        lines.append(_redact_secret(line.rstrip()))
        yield "\n".join(lines[-80:])

    exit_code = process.wait()
    if exit_code == 0:
        lines.append(success_message)
    else:
        lines.append(f"Lenh dung voi ma loi {exit_code}. Xem log phia tren.")
    yield "\n".join(lines[-100:])


def _tail(text: str, limit: int = 2000) -> str:
    text = text or ""
    return text[-limit:]


def _redact_secret(text: str) -> str:
    return re.sub(r'("key"\s*:\s*")[^"]+(")', r"\1***\2", text)
