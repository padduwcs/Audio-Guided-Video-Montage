from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

from integration.sample_data import copy_sample_contracts
from integration.stages import STAGE_BY_NUMBER, stage_numbers
from shared import read_json, repo_root, run_validate, write_json
from timeline_planner.planner import TimelinePlanningError, build_timeline


ARTIFACTS = {
    1: ("media_metadata.json",),
    2: ("audio_segments.json",),
    3: ("clip_metadata.json",),
    4: ("embedding_metadata.json",),
    5: ("matching_candidates.json",),
    6: ("timeline.json",),
    8: ("render_log.json",),
}

CONTRACT_FILES = (
    "media_metadata.json",
    "audio_segments.json",
    "clip_metadata.json",
    "embedding_metadata.json",
    "matching_candidates.json",
    "timeline.json",
    "render_config.json",
    "render_log.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Audio-Guided Video Montage pipeline. By default this runs "
            "real module code; use --use-sample-data for the contract-only demo."
        )
    )
    parser.add_argument("--project-id", default="demo_01")
    parser.add_argument("--data-dir", type=Path, default=repo_root() / "data")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Intermediate artifact directory. Default: <data-dir>/intermediate.",
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=repo_root() / "docs" / "samples",
        help="Directory containing *_sample.json files.",
    )
    parser.add_argument("--from-stage", type=int, default=1, choices=sorted(STAGE_BY_NUMBER))
    parser.add_argument("--to-stage", type=int, default=8, choices=sorted(STAGE_BY_NUMBER))
    parser.add_argument(
        "--use-sample-data",
        action="store_true",
        help="Copy docs/samples into input-dir for stages 1-5. Rendering still needs real media paths.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    parser.add_argument("--validate-only", action="store_true", help="Validate a complete runtime contract set and exit.")
    parser.add_argument("--validate-when-complete", action="store_true", help="Run full contract validation whenever all contract files exist.")

    parser.add_argument("--videos", nargs="+", default=None, help="Raw video path(s) for Stage 1.")
    parser.add_argument("--audio", default=None, help="Raw voice-over audio path for Stage 1.")
    parser.add_argument("--ffmpeg-path", default="ffmpeg")
    parser.add_argument("--ffprobe-path", default="ffprobe")
    parser.add_argument("--target-fps", type=float, default=30.0)
    parser.add_argument("--audio-sample-rate", type=int, default=16000)
    parser.add_argument("--audio-channels", type=int, default=1)
    parser.add_argument("--drop-original-audio", action="store_true")
    parser.add_argument("--no-copy-if-compatible", action="store_true")
    parser.add_argument("--no-normalize-video", action="store_true")
    parser.add_argument("--no-normalize-audio", action="store_true")

    parser.add_argument("--asr-model", default="base")
    parser.add_argument("--language", choices=("auto", "vi", "en"), default="auto")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--query-backend", choices=("rules", "local-embedding"), default="rules")
    parser.add_argument("--query-model", default=None)
    parser.add_argument("--query-min-similarity", type=float, default=0.72)

    parser.add_argument("--video-method", choices=("content", "fixed_window"), default="content")
    parser.add_argument("--scene-threshold", type=float, default=27.0)
    parser.add_argument("--clip-duration", type=float, default=6.0)
    parser.add_argument("--min-clip-duration", type=float, default=1.5)
    parser.add_argument("--max-clip-duration", type=float, default=8.0)
    parser.add_argument("--max-clips-per-video", type=int, default=500)
    parser.add_argument("--allow-fixed-window-fallback", action="store_true")
    parser.add_argument("--keyframe-positions", default="middle")
    parser.add_argument("--keyframe-dir", type=Path, default=None)

    parser.add_argument("--fake-embeddings", action="store_true", help="Use deterministic fake CLIP vectors for Stage 4.")
    parser.add_argument("--embedding-dir", type=Path, default=None)
    parser.add_argument("--index-dir", type=Path, default=None)
    parser.add_argument("--embedding-config", default=None)

    parser.add_argument("--matching-config", default=None)
    parser.add_argument("--top-k", type=int, default=None)

    parser.add_argument("--skip-ui", action="store_true", help="Skip Stage 7 entirely.")
    parser.add_argument("--launch-ui", action="store_true", help="Launch Gradio at Stage 7 and continue after it exits.")
    parser.add_argument("--readonly-ui", action="store_true")
    parser.add_argument("--no-ui-backup", action="store_true")
    parser.add_argument("--ui-host", default="127.0.0.1")
    parser.add_argument("--ui-port", type=int, default=7860)

    parser.add_argument("--output-video", type=Path, default=None)
    parser.add_argument("--render-log", type=Path, default=None)
    parser.add_argument("--voiceover", type=Path, default=None)
    parser.add_argument("--preview-render", action="store_true")
    parser.add_argument("--video-codec", default=None)
    parser.add_argument("--video-bitrate", default=None)
    parser.add_argument("--audio-codec", default=None)
    parser.add_argument("--audio-bitrate", default=None)
    parser.add_argument("--hwaccel", default=None)
    return parser.parse_args()


def _path_text(path: Path) -> str:
    try:
        return str(path.relative_to(repo_root()))
    except ValueError:
        return str(path)


def _input_dir(args: argparse.Namespace) -> Path:
    return (args.input_dir or (args.data_dir / "intermediate")).resolve()


def _copy_samples(*, input_dir: Path, samples_dir: Path, overwrite: bool) -> None:
    copied = copy_sample_contracts(samples_dir=samples_dir, output_dir=input_dir, overwrite=overwrite)
    print(f"  copied {len(copied)} sample JSON files into {_path_text(input_dir)}")


def _require_files(input_dir: Path, stage_number: int) -> None:
    missing = [
        name for name in ARTIFACTS.get(stage_number, ())
        if not (input_dir / name).exists()
    ]
    if missing:
        raise RuntimeError(
            f"Stage {stage_number} did not produce required artifact(s): {', '.join(missing)}"
        )


def _validate_if_complete(input_dir: Path) -> None:
    missing = [name for name in CONTRACT_FILES if not (input_dir / name).exists()]
    if missing:
        print(f"  full contract validation skipped; missing: {', '.join(missing)}")
        return
    print("  validating complete runtime contract set...")
    exit_code = run_validate(input_dir=input_dir)
    if exit_code != 0:
        raise RuntimeError("Runtime contract validation failed.")


def _run_input_processor(args: argparse.Namespace, input_dir: Path) -> None:
    if not args.videos or not args.audio:
        raise RuntimeError("Stage 1 requires --videos and --audio unless --use-sample-data is set.")
    from input_processor.main import InputProcessorError, process_inputs

    ns = SimpleNamespace(
        project_id=args.project_id,
        videos=args.videos,
        audio=args.audio,
        output_dir=str(args.data_dir),
        overwrite=args.overwrite,
        ffmpeg_path=args.ffmpeg_path,
        ffprobe_path=args.ffprobe_path,
        target_fps=args.target_fps,
        audio_sample_rate=args.audio_sample_rate,
        audio_channels=args.audio_channels,
        drop_original_audio=args.drop_original_audio,
        no_copy_if_compatible=args.no_copy_if_compatible,
        no_normalize_video=args.no_normalize_video,
        no_normalize_audio=args.no_normalize_audio,
    )
    try:
        result = process_inputs(ns)
    except InputProcessorError as exc:
        raise RuntimeError(f"Input Processor failed: {exc}") from exc
    print(f"  wrote {_path_text(result['metadata_path'])}")
    print(f"  usable videos: {result['videos']}")


def _run_audio_analyzer(args: argparse.Namespace, input_dir: Path) -> None:
    from audio_analyzer.asr import FasterWhisperBackend
    from audio_analyzer.pipeline import PipelineError, run_pipeline

    query_reranker = None
    if args.query_backend == "local-embedding":
        from audio_analyzer.query_reranker import (
            DEFAULT_QUERY_MODEL,
            SentenceTransformerQueryReranker,
        )

        query_reranker = SentenceTransformerQueryReranker(
            model=args.query_model or DEFAULT_QUERY_MODEL,
            min_similarity=args.query_min_similarity,
        )

    backend = FasterWhisperBackend(
        model=args.asr_model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
    )
    try:
        result = run_pipeline(
            media_metadata_path=input_dir / "media_metadata.json",
            output_dir=input_dir,
            asr_backend=backend,
            overwrite=args.overwrite,
            language=args.language,
            query_reranker=query_reranker,
            project_root=repo_root(),
        )
    except PipelineError as exc:
        raise RuntimeError(f"Audio Analyzer failed: {exc}") from exc
    print(f"  wrote {_path_text(result.audio_segments_path)} ({result.segment_count} segments)")


def _run_video_analyzer(args: argparse.Namespace, input_dir: Path) -> None:
    from video_analyzer.main import VideoAnalyzerError, process

    keyframe_dir = args.keyframe_dir or (args.data_dir / "keyframes")
    ns = SimpleNamespace(
        project_id=args.project_id,
        media_metadata=str(input_dir / "media_metadata.json"),
        output_dir=str(input_dir),
        keyframe_dir=str(keyframe_dir),
        ffmpeg_path=args.ffmpeg_path,
        method=args.video_method,
        scene_threshold=args.scene_threshold,
        clip_duration=args.clip_duration,
        min_clip_duration=args.min_clip_duration,
        max_clip_duration=args.max_clip_duration,
        max_clips_per_video=args.max_clips_per_video,
        allow_fixed_window_fallback=args.allow_fixed_window_fallback,
        keyframe_positions=args.keyframe_positions,
        overwrite=args.overwrite,
    )
    try:
        result = process(ns)
    except VideoAnalyzerError as exc:
        raise RuntimeError(f"Video Analyzer failed: {exc}") from exc
    print(f"  wrote {_path_text(result['clip_metadata_path'])} ({result['clip_count']} clips)")


def _run_embedding_indexer(args: argparse.Namespace, input_dir: Path) -> None:
    from embedding_indexer.io_utils import InputError
    from embedding_indexer.main import run

    embedding_dir = args.embedding_dir or (input_dir / "embeddings")
    index_dir = args.index_dir or (input_dir / "index")
    try:
        metadata_path = run(
            audio_segments_path=str(input_dir / "audio_segments.json"),
            clip_metadata_path=str(input_dir / "clip_metadata.json"),
            output_dir=str(input_dir),
            embedding_dir=str(embedding_dir),
            index_dir=str(index_dir),
            config_path=args.embedding_config,
            overwrite=args.overwrite,
            use_fake=args.fake_embeddings,
        )
    except InputError as exc:
        raise RuntimeError(f"Embedding Indexer failed: {exc}") from exc
    print(f"  wrote {_path_text(Path(metadata_path))}")


def _run_matching_engine(args: argparse.Namespace, input_dir: Path) -> None:
    from matching_engine.io_utils import InputError
    from matching_engine.main import run

    try:
        candidates_path = run(
            audio_segments_path=str(input_dir / "audio_segments.json"),
            clip_metadata_path=str(input_dir / "clip_metadata.json"),
            embedding_metadata_path=str(input_dir / "embedding_metadata.json"),
            output_dir=str(input_dir),
            config_path=args.matching_config,
            top_k=args.top_k,
            overwrite=args.overwrite,
        )
    except InputError as exc:
        raise RuntimeError(f"Matching Engine failed: {exc}") from exc
    print(f"  wrote {_path_text(Path(candidates_path))}")


def _run_timeline_planner(input_dir: Path) -> None:
    try:
        timeline, planning_log = build_timeline(
            read_json(input_dir / "media_metadata.json"),
            read_json(input_dir / "audio_segments.json"),
            read_json(input_dir / "clip_metadata.json"),
            read_json(input_dir / "matching_candidates.json"),
        )
    except (TimelinePlanningError, ValueError, OSError) as exc:
        raise RuntimeError(f"Timeline Planner failed: {exc}") from exc

    write_json(input_dir / "timeline.json", timeline)
    write_json(input_dir / "timeline_planning_log.json", planning_log)
    print(f"  wrote {_path_text(input_dir / 'timeline.json')}")


def _run_review_stage(args: argparse.Namespace, input_dir: Path) -> None:
    if args.skip_ui:
        print("  skipped by --skip-ui")
        return

    from review_ui.loader import load_project_data
    from review_ui.validator import validate_project_data

    paths = {
        "timeline_path": str(input_dir / "timeline.json"),
        "matching_candidates_path": str(input_dir / "matching_candidates.json"),
        "clip_metadata_path": str(input_dir / "clip_metadata.json"),
        "audio_segments_path": str(input_dir / "audio_segments.json"),
        "media_metadata_path": str(input_dir / "media_metadata.json"),
    }
    project_data = load_project_data(**paths, project_id=args.project_id)
    mode = "renderer_handoff" if args.to_stage >= 8 else "edit_save"
    messages = validate_project_data(project_data, mode=mode)
    errors = [message for message in messages if message.level == "error"]
    warnings = [message for message in messages if message.level == "warning"]
    if errors:
        for message in errors:
            print(f"  ERROR {message}")
        raise RuntimeError("Review UI validation failed.")
    for message in warnings:
        print(f"  WARNING {message}")
    print(f"  validated timeline for {mode}: {len(warnings)} warning(s)")

    if args.launch_ui:
        from review_ui.app import launch_review_ui

        launch_review_ui(
            **paths,
            project_id=args.project_id,
            readonly=args.readonly_ui,
            no_backup=args.no_ui_backup,
            log_path=str(input_dir / "review_ui_log.json"),
            host=args.ui_host,
            port=args.ui_port,
        )


def _write_render_config(args: argparse.Namespace, input_dir: Path, output_video: Path, voiceover_path: Path | None) -> None:
    timeline = read_json(input_dir / "timeline.json")
    media = read_json(input_dir / "media_metadata.json")
    settings = timeline.get("render_settings", {})
    render_config = {
        "schema_version": timeline.get("schema_version", "1.0"),
        "project_id": timeline["project_id"],
        "output": {
            "path": _path_text(output_video),
            "width": settings.get("width", 1920),
            "height": settings.get("height", 1080),
            "fps": settings.get("fps", 30),
            "format": settings.get("format", "mp4"),
        },
        "audio": {
            "voiceover_path": _path_text(voiceover_path) if voiceover_path else media.get("audio", {}).get("normalized_path"),
            "keep_original_audio": settings.get("keep_original_audio", False),
            "original_audio_volume": settings.get("original_audio_volume", 0.0),
        },
        "video": {
            "crop_mode": settings.get("crop_mode", "center_crop"),
            "default_transition": settings.get("default_transition", "cut"),
        },
    }
    write_json(input_dir / "render_config.json", render_config)
    print(f"  wrote {_path_text(input_dir / 'render_config.json')}")


def _run_renderer(args: argparse.Namespace, input_dir: Path) -> None:
    from renderer.core import render_timeline
    from renderer.validate import validate_timeline

    output_video = (args.output_video or (args.data_dir / "final" / "final_video.mp4")).resolve()
    render_log = (args.render_log or (input_dir / "render_log.json")).resolve()
    output_video.parent.mkdir(parents=True, exist_ok=True)
    render_log.parent.mkdir(parents=True, exist_ok=True)

    media = read_json(input_dir / "media_metadata.json")
    voiceover_path = args.voiceover
    if voiceover_path is None:
        normalized = media.get("audio", {}).get("normalized_path")
        voiceover_path = (repo_root() / normalized).resolve() if normalized else None

    validate_timeline(str(input_dir / "timeline.json"))
    _write_render_config(args, input_dir, output_video, voiceover_path)
    render_timeline(
        str(input_dir / "timeline.json"),
        str(output_video),
        log_path=str(render_log),
        video_codec=args.video_codec,
        video_bitrate=args.video_bitrate,
        audio_codec=args.audio_codec,
        audio_bitrate=args.audio_bitrate,
        hwaccel=args.hwaccel,
        preview=args.preview_render,
        voice_over_path=str(voiceover_path) if voiceover_path else None,
    )
    print(f"  wrote {_path_text(output_video)}")
    print(f"  wrote {_path_text(render_log)}")


def _run_stage(args: argparse.Namespace, stage_number: int, *, input_dir: Path) -> None:
    stage = STAGE_BY_NUMBER[stage_number]
    print(f"[stage {stage_number}] {stage.description}")

    if args.use_sample_data and stage_number <= 5:
        print("  using sample artifact copied before pipeline execution")
        _require_files(input_dir, stage_number)
        return

    if stage_number == 1:
        _run_input_processor(args, input_dir)
    elif stage_number == 2:
        _run_audio_analyzer(args, input_dir)
    elif stage_number == 3:
        _run_video_analyzer(args, input_dir)
    elif stage_number == 4:
        _run_embedding_indexer(args, input_dir)
    elif stage_number == 5:
        _run_matching_engine(args, input_dir)
    elif stage_number == 6:
        _run_timeline_planner(input_dir)
    elif stage_number == 7:
        _run_review_stage(args, input_dir)
    elif stage_number == 8:
        _run_renderer(args, input_dir)
    else:
        raise RuntimeError(f"Unsupported stage: {stage_number}")

    _require_files(input_dir, stage_number)
    if args.validate_when_complete:
        if stage_number == 8 and args.preview_render:
            print("[validate] skipped complete contract validation for preview render")
        else:
            _validate_if_complete(input_dir)


def main() -> int:
    args = parse_args()
    input_dir = _input_dir(args)
    input_dir.mkdir(parents=True, exist_ok=True)

    if args.from_stage > args.to_stage:
        print("ERROR: --from-stage must be <= --to-stage", file=sys.stderr)
        return 1

    if args.validate_only:
        return run_validate(input_dir=input_dir)

    selected = stage_numbers(args.from_stage, args.to_stage)
    if args.use_sample_data and any(stage <= 5 for stage in selected):
        print("[samples] preparing Stage 1-5 runtime artifacts")
        _copy_samples(input_dir=input_dir, samples_dir=args.samples_dir, overwrite=args.overwrite)

    try:
        for stage_number in selected:
            _run_stage(args, stage_number, input_dir=input_dir)
        if args.preview_render and 8 in selected:
            print("[validate] skipped complete contract validation for preview render")
        else:
            _validate_if_complete(input_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
