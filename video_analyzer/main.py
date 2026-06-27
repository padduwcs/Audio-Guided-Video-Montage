from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
USABLE_MEDIA_STATUS = {"ready", "warning"}
KEYFRAME_POSITIONS = {"start", "middle", "end"}


class VideoAnalyzerError(Exception):
    pass


@dataclass
class RunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def repo_relative(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise VideoAnalyzerError(f"Path must stay inside repo root: {path}") from None
    return relative.as_posix()


def ensure_ffmpeg(path_or_name: str) -> str:
    tool = shutil.which(path_or_name) if not Path(path_or_name).is_file() else path_or_name
    if not tool:
        raise VideoAnalyzerError("ffmpeg not found. Install FFmpeg or pass --ffmpeg-path with an executable path.")
    return tool


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VideoAnalyzerError(f"Input JSON not found: {repo_relative(path)}") from exc
    except json.JSONDecodeError as exc:
        raise VideoAnalyzerError(f"Invalid JSON: {repo_relative(path)}") from exc
    if not isinstance(data, dict):
        raise VideoAnalyzerError(f"Top-level JSON must be an object: {repo_relative(path)}")
    return data


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


def video_prefix(video_id: str) -> str:
    digits = "".join(ch for ch in video_id if ch.isdigit())
    if digits:
        return f"v{int(digits):02d}"
    return video_id.replace("video_", "v").replace("-", "_")


def round_time(value: float) -> float:
    return round(float(value), 3)


def parse_positions(raw: str) -> list[str]:
    positions = [item.strip() for item in raw.split(",") if item.strip()]
    if not positions:
        raise VideoAnalyzerError("At least one keyframe position is required.")
    unsupported = [item for item in positions if item not in KEYFRAME_POSITIONS]
    if unsupported:
        raise VideoAnalyzerError(f"Unsupported keyframe positions: {', '.join(unsupported)}")
    return positions


def build_clip_windows(
    duration: float,
    *,
    clip_duration: float,
    min_clip_duration: float,
    max_clips: int,
) -> tuple[list[tuple[float, float]], list[str]]:
    windows: list[tuple[float, float]] = []
    warnings: list[str] = []
    start = 0.0

    while start < duration:
        if len(windows) >= max_clips:
            warnings.append(f"Reached max_clips_per_video={max_clips}; remaining video was not analyzed.")
            break
        end = min(start + clip_duration, duration)
        if end - start >= min_clip_duration:
            windows.append((round_time(start), round_time(end)))
        else:
            warnings.append(f"Skipped trailing short clip {start:.3f}-{end:.3f}s (< {min_clip_duration}s).")
        start += clip_duration

    return windows, warnings


def normalize_scene_windows(
    raw_windows: list[tuple[float, float]],
    *,
    min_clip_duration: float,
    max_clip_duration: float,
    max_clips: int,
) -> tuple[list[tuple[float, float]], list[str]]:
    warnings: list[str] = []
    merged: list[list[float]] = []

    for start, end in raw_windows:
        if end <= start:
            continue
        if end - start < min_clip_duration and merged:
            merged[-1][1] = end
            warnings.append(f"Merged short scene {start:.3f}-{end:.3f}s into previous scene.")
        else:
            merged.append([start, end])

    if len(merged) > 1 and merged[0][1] - merged[0][0] < min_clip_duration:
        warnings.append(f"Merged short opening scene {merged[0][0]:.3f}-{merged[0][1]:.3f}s into next scene.")
        merged[1][0] = merged[0][0]
        merged.pop(0)

    windows: list[tuple[float, float]] = []
    for scene_start, scene_end in merged:
        scene_duration = scene_end - scene_start
        part_count = max(1, math.ceil(scene_duration / max_clip_duration))
        part_duration = scene_duration / part_count
        if part_count > 1:
            warnings.append(
                f"Split long scene {scene_start:.3f}-{scene_end:.3f}s into {part_count} balanced clips."
            )
        for part_index in range(part_count):
            if len(windows) >= max_clips:
                warnings.append(f"Reached max_clips_per_video={max_clips}; remaining scenes were not analyzed.")
                return windows, warnings
            start = scene_start + (part_index * part_duration)
            end = scene_end if part_index == part_count - 1 else scene_start + ((part_index + 1) * part_duration)
            windows.append((round_time(start), round_time(end)))

    return windows, warnings


def detect_content_scenes(
    source_path: Path,
    *,
    fps: float,
    threshold: float,
    min_clip_duration: float,
    max_clip_duration: float,
    max_clips: int,
) -> tuple[list[tuple[float, float]], list[str]]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector
    except ImportError as exc:
        raise VideoAnalyzerError(
            "PySceneDetect is required for content-aware scene detection. "
            "Install it with: python -m pip install \"scenedetect[opencv]\""
        ) from exc

    try:
        video = open_video(str(source_path))
        manager = SceneManager()
        min_scene_len = max(1, int(round(min_clip_duration * max(fps, 1.0))))
        manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))
        manager.detect_scenes(video, show_progress=False)
        scene_list = manager.get_scene_list(start_in_scene=True)
    except Exception as exc:
        raise VideoAnalyzerError(f"Scene detection failed for {repo_relative(source_path)}: {exc}") from exc

    raw_windows = [(start.get_seconds(), end.get_seconds()) for start, end in scene_list]
    if not raw_windows:
        return [], ["Content detector returned no scene windows."]
    windows, warnings = normalize_scene_windows(
        raw_windows,
        min_clip_duration=min_clip_duration,
        max_clip_duration=max_clip_duration,
        max_clips=max_clips,
    )
    warnings.insert(0, f"Content detector found {len(scene_list)} raw scene(s).")
    return windows, warnings


def keyframe_timestamp(start: float, end: float, position: str) -> float:
    duration = end - start
    if position == "start":
        timestamp = start + min(0.2, duration / 2)
    elif position == "end":
        timestamp = end - min(0.2, duration / 2)
    else:
        timestamp = start + duration / 2
    return round_time(max(start, min(timestamp, end)))


def extract_keyframe(ffmpeg_path: str, source_path: Path, timestamp: float, output_path: Path, *, overwrite: bool) -> RunResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y" if overwrite else "-n",
        "-ss",
        str(timestamp),
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]
    result = run_command(command)
    if result.returncode != 0:
        raise VideoAnalyzerError(f"Failed to extract keyframe at {timestamp}s from {repo_relative(source_path)}: {result.stderr.strip()}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise VideoAnalyzerError(f"FFmpeg did not create keyframe: {repo_relative(output_path)}")
    return result


def validate_media_metadata(data: dict[str, Any], expected_project_id: str | None) -> None:
    for field in ["schema_version", "project_id", "videos"]:
        if field not in data:
            raise VideoAnalyzerError(f"media_metadata.json missing required field: {field}")
    if expected_project_id and data["project_id"] != expected_project_id:
        raise VideoAnalyzerError(f"project_id mismatch: expected {expected_project_id}, got {data['project_id']}")
    if not isinstance(data["videos"], list) or not data["videos"]:
        raise VideoAnalyzerError("media_metadata.videos must be a non-empty array.")


def analyze_video(video: dict[str, Any], args: argparse.Namespace, ffmpeg_path: str, keyframe_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    video_id = video.get("video_id")
    if not isinstance(video_id, str) or not video_id:
        raise VideoAnalyzerError("Every video item must have a non-empty video_id.")

    status = video.get("status")
    log_item: dict[str, Any] = {"video_id": video_id, "status": "skipped", "warnings": [], "clips": []}
    if status not in USABLE_MEDIA_STATUS:
        log_item["reason"] = f"Skipped media status {status!r}."
        return [], log_item

    normalized_path = video.get("normalized_path")
    if not isinstance(normalized_path, str) or not normalized_path:
        raise VideoAnalyzerError(f"{video_id}: missing normalized_path.")
    source_path = resolve_path(normalized_path)
    if not source_path.exists():
        raise VideoAnalyzerError(f"{video_id}: normalized video not found: {normalized_path}")

    duration = float(video.get("duration") or 0.0)
    if duration <= 0:
        raise VideoAnalyzerError(f"{video_id}: video duration must be > 0.")

    detection_method = args.method
    if detection_method == "content":
        windows, warnings = detect_content_scenes(
            source_path,
            fps=float(video.get("fps") or 0.0),
            threshold=args.scene_threshold,
            min_clip_duration=args.min_clip_duration,
            max_clip_duration=args.max_clip_duration,
            max_clips=args.max_clips_per_video,
        )
        if not windows and args.allow_fixed_window_fallback:
            detection_method = "fixed_window_fallback"
            windows, fallback_warnings = build_clip_windows(
                duration,
                clip_duration=args.clip_duration,
                min_clip_duration=args.min_clip_duration,
                max_clips=args.max_clips_per_video,
            )
            warnings.extend(fallback_warnings)
            warnings.append("Used explicit fixed-window fallback because content detection returned no clips.")
    else:
        windows, warnings = build_clip_windows(
            duration,
            clip_duration=args.clip_duration,
            min_clip_duration=args.min_clip_duration,
            max_clips=args.max_clips_per_video,
        )
    log_item["method"] = detection_method
    log_item["warnings"].extend(warnings)
    if not windows:
        raise VideoAnalyzerError(f"{video_id}: no clip windows could be produced.")

    positions = parse_positions(args.keyframe_positions)
    prefix = video_prefix(video_id)
    clips: list[dict[str, Any]] = []
    for clip_index, (start, end) in enumerate(windows, start=1):
        clip_id = f"{prefix}_c{clip_index:03d}"
        keyframes: list[dict[str, Any]] = []
        commands: list[dict[str, Any]] = []

        for keyframe_index, position in enumerate(positions, start=1):
            timestamp = keyframe_timestamp(start, end, position)
            keyframe_id = f"{clip_id}_k{keyframe_index:02d}"
            keyframe_path = keyframe_dir / f"{keyframe_id}.jpg"
            result = extract_keyframe(ffmpeg_path, source_path, timestamp, keyframe_path, overwrite=args.overwrite)
            commands.append(asdict(result))
            keyframes.append(
                {
                    "keyframe_id": keyframe_id,
                    "timestamp": timestamp,
                    "position": position,
                    "path": repo_relative(keyframe_path),
                    "quality_score": None,
                }
            )

        clip_duration = round_time(end - start)
        clip = {
            "clip_id": clip_id,
            "video_id": video_id,
            "source_path": repo_relative(source_path),
            "scene_index": clip_index,
            "start": start,
            "end": end,
            "duration": clip_duration,
            "keyframes": keyframes,
            "quality": {
                "blur_score": None,
                "brightness_score": None,
                "motion_score": None,
                "stability_score": None,
                "quality_score": None,
            },
            "quality_score": None,
            "content_tags": [],
            "caption": None,
            "status": "usable",
            "notes": f"Generated by {detection_method} detection.",
        }
        clips.append(clip)
        log_item["clips"].append(
            {
                "clip_id": clip_id,
                "start": start,
                "end": end,
                "duration": clip_duration,
                "keyframes": [item["path"] for item in keyframes],
                "commands": commands,
            }
        )

    log_item["status"] = "processed"
    log_item["clip_count"] = len(clips)
    return clips, log_item


def process(args: argparse.Namespace) -> dict[str, Path | int]:
    ffmpeg_path = ensure_ffmpeg(args.ffmpeg_path)
    media_metadata_path = resolve_path(args.media_metadata)
    output_dir = resolve_path(args.output_dir)
    keyframe_dir = resolve_path(args.keyframe_dir)
    clip_metadata_path = output_dir / "clip_metadata.json"
    log_path = output_dir / "video_analysis_log.json"

    if clip_metadata_path.exists() and not args.overwrite:
        raise VideoAnalyzerError(f"{repo_relative(clip_metadata_path)} already exists. Re-run with --overwrite.")
    if log_path.exists() and not args.overwrite:
        raise VideoAnalyzerError(f"{repo_relative(log_path)} already exists. Re-run with --overwrite.")

    data = load_json(media_metadata_path)
    validate_media_metadata(data, args.project_id)

    output_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)

    created_at = utc_now()
    log: dict[str, Any] = {
        "schema_version": "1.0",
        "project_id": data["project_id"],
        "created_at": created_at,
        "method": args.method,
        "config": {
            "scene_threshold": args.scene_threshold,
            "clip_duration": args.clip_duration,
            "min_clip_duration": args.min_clip_duration,
            "max_clip_duration": args.max_clip_duration,
            "max_clips_per_video": args.max_clips_per_video,
            "allow_fixed_window_fallback": args.allow_fixed_window_fallback,
            "keyframe_positions": parse_positions(args.keyframe_positions),
        },
        "tools": {"ffmpeg": ffmpeg_path},
        "videos": [],
        "warnings": [],
        "errors": [],
    }

    all_clips: list[dict[str, Any]] = []
    for video in data["videos"]:
        try:
            clips, log_item = analyze_video(video, args, ffmpeg_path, keyframe_dir)
            all_clips.extend(clips)
            log["videos"].append(log_item)
            log["warnings"].extend({"video_id": log_item["video_id"], "message": warning} for warning in log_item.get("warnings", []))
        except VideoAnalyzerError as exc:
            video_id = video.get("video_id", "unknown")
            error = {"video_id": video_id, "message": str(exc)}
            log["errors"].append(error)
            log["videos"].append({"video_id": video_id, "status": "error", "error": str(exc)})

    usable_count = sum(1 for clip in all_clips if clip["status"] == "usable")
    if usable_count == 0:
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise VideoAnalyzerError("No usable clips were produced.")

    clip_metadata = {
        "schema_version": "1.0",
        "project_id": data["project_id"],
        "created_at": created_at,
        "items": all_clips,
    }
    clip_metadata_path.write_text(json.dumps(clip_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log["summary"] = {"clip_count": len(all_clips), "usable_clip_count": usable_count}
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"clip_metadata_path": clip_metadata_path, "log_path": log_path, "clip_count": len(all_clips)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage 3: split normalized videos into clips and extract keyframes.")
    parser.add_argument("--project-id", default=None, help="Optional project ID guard.")
    parser.add_argument("--media-metadata", default="data/intermediate/media_metadata.json", help="Path to media_metadata.json.")
    parser.add_argument("--output-dir", default="data/intermediate", help="Directory for clip_metadata.json and log.")
    parser.add_argument("--keyframe-dir", default="data/keyframes", help="Directory for extracted keyframe images.")
    parser.add_argument("--ffmpeg-path", default="ffmpeg", help="ffmpeg executable path or name.")
    parser.add_argument(
        "--method",
        choices=["content", "fixed_window"],
        default="content",
        help="Clip boundary method. Default: content-aware scene detection.",
    )
    parser.add_argument("--scene-threshold", type=float, default=27.0, help="ContentDetector sensitivity; lower finds more cuts.")
    parser.add_argument("--clip-duration", type=float, default=6.0, help="Fixed-window duration, used only in fixed mode/fallback.")
    parser.add_argument("--min-clip-duration", type=float, default=1.5, help="Short scenes are merged with adjacent scenes.")
    parser.add_argument("--max-clip-duration", type=float, default=8.0, help="Long continuous scenes are split at this duration.")
    parser.add_argument("--max-clips-per-video", type=int, default=500, help="Safety cap for long videos.")
    parser.add_argument(
        "--allow-fixed-window-fallback",
        action="store_true",
        help="Allow fixed-window fallback only when content detection returns no clips.",
    )
    parser.add_argument(
        "--keyframe-positions",
        default="middle",
        help="Comma-separated positions: start,middle,end. Default: middle",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite clip metadata, log, and keyframes.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.clip_duration <= 0:
        print("ERROR: --clip-duration must be > 0")
        return 1
    if args.min_clip_duration <= 0:
        print("ERROR: --min-clip-duration must be > 0")
        return 1
    if args.max_clip_duration < args.min_clip_duration:
        print("ERROR: --max-clip-duration must be >= --min-clip-duration")
        return 1
    if args.scene_threshold <= 0:
        print("ERROR: --scene-threshold must be > 0")
        return 1
    if args.max_clips_per_video <= 0:
        print("ERROR: --max-clips-per-video must be > 0")
        return 1

    try:
        result = process(args)
    except VideoAnalyzerError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"OK: wrote {repo_relative(result['clip_metadata_path'])}")
    print(f"OK: wrote {repo_relative(result['log_path'])}")
    print(f"OK: clips: {result['clip_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
