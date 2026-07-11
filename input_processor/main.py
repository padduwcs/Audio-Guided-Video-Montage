from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}


class InputProcessorError(Exception):
    pass


@dataclass
class RunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_relative(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise InputProcessorError(f"Path must stay inside repo root: {path}") from None
    return relative.as_posix()


def resolve_input(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def parse_rate(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0


def round_number(value: float | int | None, digits: int = 3) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def run_command(command: list[str]) -> RunResult:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return RunResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def ensure_tool(path_or_name: str, label: str) -> str:
    tool = shutil.which(path_or_name) if not Path(path_or_name).is_file() else path_or_name
    if not tool:
        raise InputProcessorError(
            f"{label} not found. Install FFmpeg or pass --{label.lower()}-path with an executable path."
        )
    return tool


def ffprobe(ffprobe_path: str, media_path: Path) -> dict[str, Any]:
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    ]
    result = run_command(command)
    if result.returncode != 0:
        raise InputProcessorError(f"ffprobe failed for {repo_relative(media_path)}: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InputProcessorError(f"ffprobe returned invalid JSON for {repo_relative(media_path)}") from exc


def stream_by_type(probe: dict[str, Any], stream_type: str) -> dict[str, Any] | None:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == stream_type:
            return stream
    return None


def format_duration(probe: dict[str, Any], stream: dict[str, Any] | None = None) -> float:
    if stream and stream.get("duration") is not None:
        return round_number(float(stream["duration"]))
    fmt = probe.get("format", {})
    if fmt.get("duration") is not None:
        return round_number(float(fmt["duration"]))
    return 0.0


def is_compatible_mp4(path: Path, video_stream: dict[str, Any], target_fps: float) -> bool:
    codec = str(video_stream.get("codec_name", "")).lower()
    fps = parse_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    return path.suffix.lower() == ".mp4" and codec == "h264" and abs(fps - target_fps) < 0.05


def normalize_video(
    ffmpeg_path: str,
    source: Path,
    target: Path,
    *,
    target_fps: float,
    preserve_audio: bool,
    copy_if_compatible: bool,
    video_stream: dict[str, Any],
    overwrite: bool,
) -> RunResult:
    target.parent.mkdir(parents=True, exist_ok=True)
    overwrite_flag = "-y" if overwrite else "-n"
    map_audio = "0:a?" if preserve_audio else "-0:a"

    if copy_if_compatible and is_compatible_mp4(source, video_stream, target_fps):
        command = [
            ffmpeg_path,
            overwrite_flag,
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            map_audio,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(target),
        ]
    else:
        command = [
            ffmpeg_path,
            overwrite_flag,
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            map_audio,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-r",
            str(target_fps),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(target),
        ]

    result = run_command(command)
    if result.returncode != 0:
        raise InputProcessorError(f"ffmpeg video normalize failed for {repo_relative(source)}: {result.stderr.strip()}")
    return result


def normalize_audio(
    ffmpeg_path: str,
    source: Path,
    target: Path,
    *,
    sample_rate: int,
    channels: int,
    overwrite: bool,
) -> RunResult:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y" if overwrite else "-n",
        "-i",
        str(source),
        "-vn",
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(target),
    ]
    result = run_command(command)
    if result.returncode != 0:
        raise InputProcessorError(f"ffmpeg audio normalize failed for {repo_relative(source)}: {result.stderr.strip()}")
    return result


def video_metadata_item(
    video_id: str,
    original_path: Path,
    normalized_path: Path,
    probe: dict[str, Any],
    *,
    status: str,
    notes: str | None = None,
) -> dict[str, Any]:
    video_stream = stream_by_type(probe, "video") or {}
    audio_stream = stream_by_type(probe, "audio")
    item: dict[str, Any] = {
        "video_id": video_id,
        "original_path": repo_relative(original_path),
        "normalized_path": repo_relative(normalized_path),
        "duration": format_duration(probe, video_stream),
        "fps": round_number(parse_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))),
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "has_audio": audio_stream is not None,
        "codec": video_stream.get("codec_name"),
        "status": status,
    }
    if notes:
        item["notes"] = notes
    return item


def audio_metadata_object(
    audio_id: str,
    original_path: Path,
    normalized_path: Path,
    probe: dict[str, Any],
    *,
    status: str,
    notes: str | None = None,
) -> dict[str, Any]:
    audio_stream = stream_by_type(probe, "audio") or {}
    item: dict[str, Any] = {
        "audio_id": audio_id,
        "original_path": repo_relative(original_path),
        "normalized_path": repo_relative(normalized_path),
        "duration": format_duration(probe, audio_stream),
        "sample_rate": int(audio_stream.get("sample_rate") or 0),
        "channels": int(audio_stream.get("channels") or 0),
        "status": status,
    }
    if notes:
        item["notes"] = notes
    return item


def validate_raw_video(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise InputProcessorError(f"Video input not found: {path}")
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        expected = ", ".join(sorted(VIDEO_EXTENSIONS))
        raise InputProcessorError(f"Unsupported video extension for {path.name}. Expected: {expected}")


def validate_raw_audio(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise InputProcessorError(f"Audio input not found: {path}")
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        expected = ", ".join(sorted(AUDIO_EXTENSIONS))
        raise InputProcessorError(f"Unsupported audio extension for {path.name}. Expected: {expected}")


def output_paths(output_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (
        output_dir / "normalized",
        output_dir / "intermediate",
        output_dir / "intermediate" / "media_metadata.json",
        output_dir / "intermediate" / "input_processing_log.json",
    )


def process_inputs(args: argparse.Namespace) -> dict[str, Any]:
    ffmpeg_path = ensure_tool(args.ffmpeg_path, "ffmpeg")
    ffprobe_path = ensure_tool(args.ffprobe_path, "ffprobe")

    video_paths = [resolve_input(path) for path in args.videos]
    audio_path = resolve_input(args.audio)
    output_dir = resolve_input(args.output_dir)
    normalized_dir, intermediate_dir, metadata_path, log_path = output_paths(output_dir)

    if metadata_path.exists() and not args.overwrite:
        raise InputProcessorError(f"{repo_relative(metadata_path)} already exists. Re-run with --overwrite.")
    if log_path.exists() and not args.overwrite:
        raise InputProcessorError(f"{repo_relative(log_path)} already exists. Re-run with --overwrite.")

    for video_path in video_paths:
        validate_raw_video(video_path)
    validate_raw_audio(audio_path)

    intermediate_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    created_at = utc_now()
    log: dict[str, Any] = {
        "schema_version": "1.0",
        "project_id": args.project_id,
        "created_at": created_at,
        "config": {
            "normalize_video": not args.no_normalize_video,
            "normalize_audio": not args.no_normalize_audio,
            "target_video": {
                "format": "mp4",
                "codec": "h264",
                "fps": args.target_fps,
                "preserve_original_audio": not args.drop_original_audio,
            },
            "target_audio": {
                "format": "wav",
                "sample_rate": args.audio_sample_rate,
                "channels": args.audio_channels,
            },
            "copy_if_compatible": not args.no_copy_if_compatible,
        },
        "tools": {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path},
        "videos": [],
        "audio": {},
        "warnings": [],
        "errors": [],
    }

    videos: list[dict[str, Any]] = []
    for index, original_video in enumerate(video_paths, start=1):
        video_id = f"video_{index:02d}"
        normalized_video = normalized_dir / f"{video_id}.mp4"
        try:
            original_probe = ffprobe(ffprobe_path, original_video)
            video_stream = stream_by_type(original_probe, "video")
            if not video_stream:
                raise InputProcessorError(f"No video stream found in {repo_relative(original_video)}")
            if format_duration(original_probe, video_stream) <= 0:
                raise InputProcessorError(f"Video duration must be > 0: {repo_relative(original_video)}")

            if args.no_normalize_video:
                normalized_video = original_video
                video_command = None
            else:
                result = normalize_video(
                    ffmpeg_path,
                    original_video,
                    normalized_video,
                    target_fps=args.target_fps,
                    preserve_audio=not args.drop_original_audio,
                    copy_if_compatible=not args.no_copy_if_compatible,
                    video_stream=video_stream,
                    overwrite=args.overwrite,
                )
                video_command = asdict(result)

            normalized_probe = ffprobe(ffprobe_path, normalized_video)
            item = video_metadata_item(video_id, original_video, normalized_video, normalized_probe, status="ready")
            if item["fps"] <= 0 or item["width"] <= 0 or item["height"] <= 0 or item["duration"] <= 0:
                item["status"] = "warning"
                item["notes"] = "Normalized video metadata has unusual fps, size, or duration."
                log["warnings"].append({"video_id": video_id, "message": item["notes"]})
            videos.append(item)
            log["videos"].append(
                {
                    "video_id": video_id,
                    "original_path": repo_relative(original_video),
                    "normalized_path": repo_relative(normalized_video),
                    "status": item["status"],
                    "original_probe_summary": {
                        "duration": format_duration(original_probe, video_stream),
                        "codec": video_stream.get("codec_name"),
                        "fps": round_number(parse_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))),
                    },
                    "normalize_command": video_command,
                }
            )
        except InputProcessorError as exc:
            error_item = {
                "video_id": video_id,
                "original_path": repo_relative(original_video),
                "normalized_path": repo_relative(normalized_video),
                "duration": 0.0,
                "fps": 0.0,
                "width": 0,
                "height": 0,
                "has_audio": False,
                "status": "error",
                "notes": str(exc),
            }
            videos.append(error_item)
            log["videos"].append(error_item)
            log["errors"].append({"video_id": video_id, "message": str(exc)})

    usable_videos = [video for video in videos if video["status"] in {"ready", "warning"}]
    if not usable_videos:
        raise InputProcessorError("No usable video output was produced.")

    normalized_audio = normalized_dir / "voiceover.wav"
    original_audio_probe = ffprobe(ffprobe_path, audio_path)
    audio_stream = stream_by_type(original_audio_probe, "audio")
    if not audio_stream:
        raise InputProcessorError(f"No audio stream found in {repo_relative(audio_path)}")
    if format_duration(original_audio_probe, audio_stream) <= 0:
        raise InputProcessorError(f"Audio duration must be > 0: {repo_relative(audio_path)}")

    if args.no_normalize_audio:
        normalized_audio = audio_path
        audio_command = None
    else:
        audio_result = normalize_audio(
            ffmpeg_path,
            audio_path,
            normalized_audio,
            sample_rate=args.audio_sample_rate,
            channels=args.audio_channels,
            overwrite=args.overwrite,
        )
        audio_command = asdict(audio_result)

    normalized_audio_probe = ffprobe(ffprobe_path, normalized_audio)
    audio = audio_metadata_object("audio_01", audio_path, normalized_audio, normalized_audio_probe, status="ready")
    if audio["duration"] <= 0 or audio["sample_rate"] <= 0 or audio["channels"] <= 0:
        raise InputProcessorError("Normalized audio metadata is invalid.")

    log["audio"] = {
        "audio_id": "audio_01",
        "original_path": repo_relative(audio_path),
        "normalized_path": repo_relative(normalized_audio),
        "status": audio["status"],
        "original_probe_summary": {
            "duration": format_duration(original_audio_probe, audio_stream),
            "sample_rate": int(audio_stream.get("sample_rate") or 0),
            "channels": int(audio_stream.get("channels") or 0),
        },
        "normalize_command": audio_command,
    }

    metadata = {
        "schema_version": "1.0",
        "project_id": args.project_id,
        "created_at": created_at,
        "videos": videos,
        "audio": audio,
    }

    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"metadata_path": metadata_path, "log_path": log_path, "videos": len(usable_videos)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage 1: normalize raw media and write media_metadata.json.")
    parser.add_argument("--project-id", default="demo_01", help="Project ID written to media_metadata.json.")
    parser.add_argument("--videos", nargs="+", required=True, help="One or more raw video paths.")
    parser.add_argument("--audio", required=True, help="Raw voice-over audio path.")
    parser.add_argument("--output-dir", default="data", help="Output data directory. Default: data")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    parser.add_argument("--ffmpeg-path", default="ffmpeg", help="ffmpeg executable path or name.")
    parser.add_argument("--ffprobe-path", default="ffprobe", help="ffprobe executable path or name.")
    parser.add_argument("--target-fps", type=float, default=30.0, help="Target normalized video FPS.")
    parser.add_argument("--audio-sample-rate", type=int, default=16000, help="Target voice-over sample rate.")
    parser.add_argument("--audio-channels", type=int, default=1, help="Target voice-over channel count.")
    parser.add_argument("--drop-original-audio", action="store_true", help="Do not preserve audio streams in normalized videos.")
    parser.add_argument("--no-copy-if-compatible", action="store_true", help="Always transcode normalized videos.")
    parser.add_argument("--no-normalize-video", action="store_true", help="Use raw video paths as normalized paths.")
    parser.add_argument("--no-normalize-audio", action="store_true", help="Use raw audio path as normalized path.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = process_inputs(args)
    except InputProcessorError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"OK: wrote {repo_relative(result['metadata_path'])}")
    print(f"OK: wrote {repo_relative(result['log_path'])}")
    print(f"OK: usable videos: {result['videos']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
