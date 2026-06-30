from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


KAGGLE_INPUT = Path("/kaggle/input")
SCRIPT_ROOT = Path(__file__).resolve().parent
WORK_ROOT = Path("/kaggle/working")
PROJECT_ROOT = WORK_ROOT / "audio-guided-video-montage"
OUTPUT_DATA = WORK_ROOT / "output_data"
OUTPUT_ZIP = WORK_ROOT / "kaggle_outputs.zip"
INPUT_ROOT = SCRIPT_ROOT
EMBEDDED_FILES: dict[str, str] = {}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)


def read_config() -> dict:
    candidates = sorted(KAGGLE_INPUT.glob("*/kaggle_job_config.json"))
    if not candidates:
        bundled = SCRIPT_ROOT / "kaggle_job_config.json"
        if bundled.is_file():
            config_path = bundled
        elif EMBEDDED_FILES:
            config_path = materialize_embedded_inputs() / "kaggle_job_config.json"
        else:
            raise FileNotFoundError(
                f"Missing kaggle_job_config.json under {KAGGLE_INPUT} "
                f"or bundled script dir {SCRIPT_ROOT}"
            )
    else:
        config_path = candidates[0]
    global INPUT_ROOT
    INPUT_ROOT = config_path.parent
    print(f"Using job input root: {INPUT_ROOT}", flush=True)
    return json.loads(config_path.read_text(encoding="utf-8"))


def materialize_embedded_inputs() -> Path:
    target_root = WORK_ROOT / "embedded_input"
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)
    for relative_name, encoded in EMBEDDED_FILES.items():
        target = target_root / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(encoded))
    return target_root


def unpack_source(config: dict) -> None:
    source_zip = INPUT_ROOT / "source.zip"
    if PROJECT_ROOT.exists():
        shutil.rmtree(PROJECT_ROOT)
    source_dir_names = [
        config.get("source_dir"),
        "project_source",
        "source",
    ]
    source_dirs = [INPUT_ROOT / name for name in source_dir_names if name]
    existing_source_dir = next((path for path in source_dirs if path.is_dir()), None)
    if existing_source_dir is not None:
        shutil.copytree(existing_source_dir, PROJECT_ROOT)
    elif source_zip.is_file():
        PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source_zip) as archive:
            archive.extractall(PROJECT_ROOT)
    else:
        raise FileNotFoundError(
            f"Missing source directory/archive under {INPUT_ROOT}; tried {source_dirs} and {source_zip}"
        )


def install_requirements() -> None:
    requirements = PROJECT_ROOT / "requirements-kaggle.txt"
    if not requirements.is_file():
        requirements = PROJECT_ROOT / "requirements.txt"
    run([sys.executable, "-m", "pip", "install", "-r", str(requirements)])


def resolve_input(relative_path: str) -> Path:
    path = INPUT_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Input file does not exist in job input root: {path}")
    return path


def prepare_project_inputs(config: dict) -> dict:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    updated = dict(config)
    videos = []
    for relative_path in config["videos"]:
        source = resolve_input(relative_path)
        target = raw_dir / source.name
        shutil.copy2(source, target)
        videos.append(f"data/raw/{source.name}")
    audio_source = resolve_input(config["audio"])
    audio_target = raw_dir / audio_source.name
    shutil.copy2(audio_source, audio_target)
    updated["videos"] = videos
    updated["audio"] = f"data/raw/{audio_source.name}"
    return updated


def run_pipeline(config: dict) -> None:
    config = prepare_project_inputs(config)
    audio = str(PROJECT_ROOT / config["audio"])
    videos = [str(PROJECT_ROOT / path) for path in config["videos"]]
    # Keep Kaggle's default path aligned with integration.run_pipeline. Some
    # Kaggle GPU sessions expose CUDA but reject faster-whisper float16 kernels,
    # so opt into GPU only when the submit command explicitly asks for it.
    device = config.get("device") or "cpu"
    compute_type = config.get("compute_type") or "int8"
    print(
        f"ASR runtime options: device={device}, compute_type={compute_type}",
        flush=True,
    )

    command = [
        sys.executable,
        "-m",
        "integration.run_pipeline",
        "--project-id",
        config.get("project_id", "demo_01"),
        "--data-dir",
        str(PROJECT_ROOT / "data"),
        "--from-stage",
        str(config.get("from_stage", 1)),
        "--to-stage",
        str(config.get("to_stage", 6)),
        "--videos",
        *videos,
        "--audio",
        audio,
        "--overwrite",
        "--skip-ui",
        "--video-method",
        config.get("video_method", "fixed_window"),
        "--asr-model",
        config.get("asr_model", "base"),
        "--language",
        config.get("language", "auto"),
        "--device",
        device,
        "--compute-type",
        compute_type,
    ]
    if config.get("fake_embeddings", True):
        command.append("--fake-embeddings")
    run(command, cwd=PROJECT_ROOT)


def collect_outputs() -> None:
    project_data = PROJECT_ROOT / "data"
    if OUTPUT_DATA.exists():
        shutil.rmtree(OUTPUT_DATA)
    if project_data.exists():
        shutil.copytree(project_data, OUTPUT_DATA)


def zip_outputs() -> None:
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if OUTPUT_DATA.exists():
            for path in OUTPUT_DATA.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(WORK_ROOT))
        for log_name in ("job.log",):
            log_path = WORK_ROOT / log_name
            if log_path.is_file():
                archive.write(log_path, log_path.name)
    print(f"Wrote {OUTPUT_ZIP}", flush=True)


def main() -> None:
    try:
        config = read_config()
        unpack_source(config)
        install_requirements()
        OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
        run_pipeline(config)
    finally:
        collect_outputs()
        zip_outputs()


if __name__ == "__main__":
    main()
