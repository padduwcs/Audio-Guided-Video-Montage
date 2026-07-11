from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.contract import (
    CLIP_STATUS_VALUES,
    CONFIDENCE_VALUES,
    CROP_MODE_VALUES,
    EPS,
    MEDIA_STATUS_VALUES,
    TRANSITION_VALUES,
)


SAMPLES = ROOT / "docs" / "samples"
SEGMENT_TYPE_VALUES = {"description", "action", "transition", "abstract", "unknown"}
EFFECT_VALUES = {None, "none"}
RENDER_STATUS_VALUES = {"success", "warning", "failed"}


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: top-level value must be an object")
    return data


def require(data: dict[str, Any], path: Path, fields: list[str]) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValidationError(f"{path}: missing required fields: {', '.join(missing)}")


def require_items(data: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    items = data.get("items")
    if not isinstance(items, list):
        raise ValidationError(f"{path}: items must be an array")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError(f"{path}: items[{index}] must be an object")
    return items


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_number(value: Any, label: str, *, minimum: float | None = None) -> None:
    if not is_number(value):
        raise ValidationError(f"{label}: must be a number")
    if minimum is not None and float(value) < minimum:
        raise ValidationError(f"{label}: must be >= {minimum}")


def check_positive(value: Any, label: str) -> None:
    check_number(value, label)
    if float(value) <= 0:
        raise ValidationError(f"{label}: must be > 0")


def check_integer(value: Any, label: str, *, minimum: int | None = None) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{label}: must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{label}: must be >= {minimum}")


def check_score(value: Any, label: str) -> None:
    if value is None:
        return
    if not is_number(value) or not 0.0 <= float(value) <= 1.0:
        raise ValidationError(f"{label}: score must be null or in [0.0, 1.0]")


def check_confidence(value: Any, label: str) -> None:
    if value not in CONFIDENCE_VALUES:
        raise ValidationError(f"{label}: confidence must be high, medium, or low")


def check_allowed(value: Any, allowed: set[Any], label: str) -> None:
    if value not in allowed:
        raise ValidationError(f"{label}: unsupported value {value!r}")


def check_relative_path(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label}: path must be a non-empty string")
    if value.startswith(("/", "\\")) or (len(value) >= 2 and value[1] == ":"):
        raise ValidationError(f"{label}: path must be relative, got {value!r}")


def approx_equal(left: Any, right: Any, label: str, *, eps: float = EPS) -> None:
    check_number(left, f"{label} left")
    check_number(right, f"{label} right")
    if abs(float(left) - float(right)) > eps:
        raise ValidationError(f"{label}: {left} != {right} within {eps}s")


def check_time_range(start: Any, end: Any, duration: Any, label: str) -> None:
    check_number(start, f"{label}.start", minimum=0)
    check_positive(end, f"{label}.end")
    if float(end) <= float(start):
        raise ValidationError(f"{label}: end must be greater than start")
    approx_equal(float(end) - float(start), duration, f"{label}.duration")


def collect_unique(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise ValidationError(f"{label}: {key} must be a non-empty string")
        if value in result:
            raise ValidationError(f"{label}: duplicate {key} {value!r}")
        result[value] = item
    return result


def contract_files(directory: Path, *, runtime: bool) -> dict[str, Path]:
    if runtime:
        names = {
            "media": "media_metadata.json",
            "audio": "audio_segments.json",
            "clips": "clip_metadata.json",
            "embeddings": "embedding_metadata.json",
            "matching": "matching_candidates.json",
            "timeline": "timeline.json",
            "render_config": "render_config.json",
            "render_log": "render_log.json",
        }
    else:
        names = {
            "media": "media_metadata_sample.json",
            "audio": "audio_segments_sample.json",
            "clips": "clip_metadata_sample.json",
            "embeddings": "embedding_metadata_sample.json",
            "matching": "matching_candidates_sample.json",
            "timeline": "timeline_sample.json",
            "render_config": "render_config_sample.json",
            "render_log": "render_log_sample.json",
        }
    return {key: directory / filename for key, filename in names.items()}


def validate_samples(samples_dir: Path, *, runtime: bool = False) -> None:
    files = contract_files(samples_dir, runtime=runtime)

    data = {name: load_json(path) for name, path in files.items()}

    require(data["media"], files["media"], ["schema_version", "project_id", "created_at", "videos", "audio"])
    require(data["audio"], files["audio"], ["schema_version", "project_id", "audio_id", "language", "created_at", "items"])
    require(data["clips"], files["clips"], ["schema_version", "project_id", "created_at", "items"])
    require(data["embeddings"], files["embeddings"], ["schema_version", "project_id", "model", "created_at", "text_embeddings", "visual_embeddings", "index"])
    require(data["matching"], files["matching"], ["schema_version", "project_id", "top_k", "created_at", "items"])
    require(data["timeline"], files["timeline"], ["schema_version", "project_id", "audio_id", "created_at", "updated_at", "render_settings", "items"])
    require(data["render_config"], files["render_config"], ["schema_version", "project_id", "output", "audio", "video"])
    require(data["render_log"], files["render_log"], ["schema_version", "project_id", "started_at", "finished_at", "status", "output_path", "duration", "render_time", "warnings", "errors"])

    project_ids = {item["project_id"] for item in data.values()}
    if len(project_ids) != 1:
        raise ValidationError(f"sample project_id mismatch: {sorted(project_ids)}")

    media_audio = data["media"].get("audio", {})
    require(media_audio, files["media"], ["audio_id", "original_path", "normalized_path", "duration", "sample_rate", "channels", "status"])
    if data["audio"]["audio_id"] != media_audio.get("audio_id"):
        raise ValidationError("audio_segments.audio_id must match media_metadata.audio.audio_id")
    if data["timeline"]["audio_id"] != media_audio.get("audio_id"):
        raise ValidationError("timeline.audio_id must match media_metadata.audio.audio_id")
    check_relative_path(media_audio["original_path"], "media.audio.original_path")
    check_relative_path(media_audio["normalized_path"], "media.audio.normalized_path")
    check_positive(media_audio["duration"], "media.audio.duration")
    check_integer(media_audio["sample_rate"], "media.audio.sample_rate", minimum=1)
    check_integer(media_audio["channels"], "media.audio.channels", minimum=1)
    check_allowed(media_audio["status"], MEDIA_STATUS_VALUES, "media.audio.status")

    videos = data["media"].get("videos")
    if not isinstance(videos, list) or not videos:
        raise ValidationError(f"{files['media']}: videos must be a non-empty array")
    for video in videos:
        require(video, files["media"], ["video_id", "original_path", "normalized_path", "duration", "fps", "width", "height", "has_audio", "status"])
        check_relative_path(video["original_path"], f"video {video.get('video_id')}.original_path")
        check_relative_path(video["normalized_path"], f"video {video.get('video_id')}.normalized_path")
        check_positive(video["duration"], f"video {video.get('video_id')}.duration")
        check_positive(video["fps"], f"video {video.get('video_id')}.fps")
        check_integer(video["width"], f"video {video.get('video_id')}.width", minimum=1)
        check_integer(video["height"], f"video {video.get('video_id')}.height", minimum=1)
        if not isinstance(video["has_audio"], bool):
            raise ValidationError(f"video {video.get('video_id')}.has_audio must be boolean")
        check_allowed(video["status"], MEDIA_STATUS_VALUES, f"video {video.get('video_id')}.status")

    video_by_id = collect_unique(videos, "video_id", "media.videos")
    audio_items = require_items(data["audio"], files["audio"])
    clip_items = require_items(data["clips"], files["clips"])
    matching_items = require_items(data["matching"], files["matching"])
    timeline_items = require_items(data["timeline"], files["timeline"])

    segment_by_id = collect_unique(audio_items, "segment_id", "audio.items")
    clip_by_id = collect_unique(clip_items, "clip_id", "clip.items")

    previous_end = 0.0
    for segment in audio_items:
        label = f"segment {segment['segment_id']}"
        require(segment, files["audio"], ["segment_id", "start", "end", "duration", "text", "query", "asr_confidence"])
        check_time_range(segment["start"], segment["end"], segment["duration"], label)
        if abs(float(segment["start"]) - previous_end) > EPS:
            raise ValidationError(f"{label}: is not contiguous with previous segment")
        previous_end = float(segment["end"])
        if not segment["text"]:
            raise ValidationError(f"{label}.text must not be empty")
        if not segment["query"]:
            raise ValidationError(f"{label}.query must not be empty")
        check_score(segment.get("asr_confidence"), f"{label}.asr_confidence")
        if "segment_type" in segment:
            check_allowed(segment["segment_type"], SEGMENT_TYPE_VALUES, f"{label}.segment_type")
    if previous_end > float(media_audio["duration"]) + EPS:
        raise ValidationError("audio segments exceed media audio duration")

    keyframe_ids: set[str] = set()
    for clip in clip_items:
        label = f"clip {clip['clip_id']}"
        require(clip, files["clips"], ["clip_id", "video_id", "start", "end", "duration", "keyframes", "quality_score"])
        video = video_by_id.get(clip["video_id"])
        if video is None:
            raise ValidationError(f"{label}: video_id not found in media_metadata")
        check_time_range(clip["start"], clip["end"], clip["duration"], label)
        if float(clip["end"]) > float(video["duration"]) + EPS:
            raise ValidationError(f"{label}: end exceeds source video duration")
        if clip.get("source_path") is not None:
            check_relative_path(clip["source_path"], f"{label}.source_path")
            if clip["source_path"] != video["normalized_path"]:
                raise ValidationError(f"{label}: source_path must match media_metadata normalized_path")
        check_score(clip.get("quality_score"), f"{label}.quality_score")
        if "status" in clip:
            check_allowed(clip["status"], CLIP_STATUS_VALUES, f"{label}.status")
        keyframes = clip.get("keyframes")
        if not isinstance(keyframes, list) or not keyframes:
            raise ValidationError(f"{label}: keyframes must be a non-empty array")
        for keyframe in keyframes:
            require(keyframe, files["clips"], ["keyframe_id", "timestamp", "path"])
            if keyframe["keyframe_id"] in keyframe_ids:
                raise ValidationError(f"{label}: duplicate keyframe_id {keyframe['keyframe_id']!r}")
            keyframe_ids.add(keyframe["keyframe_id"])
            check_number(keyframe["timestamp"], f"{label}.{keyframe['keyframe_id']}.timestamp", minimum=0)
            if not float(clip["start"]) <= float(keyframe["timestamp"]) <= float(clip["end"]):
                raise ValidationError(f"{label}.{keyframe['keyframe_id']}: timestamp outside clip range")
            check_relative_path(keyframe["path"], f"{label}.{keyframe['keyframe_id']}.path")
            if "quality_score" in keyframe:
                check_score(keyframe["quality_score"], f"{label}.{keyframe['keyframe_id']}.quality_score")

    model = data["embeddings"].get("model")
    require(model, files["embeddings"], ["name", "type", "dimension"])
    check_allowed(model["type"], {"text", "image", "multimodal"}, "embedding.model.type")
    check_integer(model["dimension"], "embedding.model.dimension", minimum=1)

    text_segment_ids = set()
    for embedding in data["embeddings"].get("text_embeddings", []):
        require(embedding, files["embeddings"], ["embedding_id", "segment_id", "source_text", "vector_path"])
        if embedding["segment_id"] not in segment_by_id:
            raise ValidationError(f"text embedding {embedding['embedding_id']}: unknown segment_id")
        text_segment_ids.add(embedding["segment_id"])
        if embedding["vector_path"] is not None:
            check_relative_path(embedding["vector_path"], f"text embedding {embedding['embedding_id']}.vector_path")
    missing_text_embeddings = set(segment_by_id) - text_segment_ids
    if missing_text_embeddings:
        raise ValidationError(f"missing text embeddings for segments: {sorted(missing_text_embeddings)}")

    visual_clip_ids = set()
    for embedding in data["embeddings"].get("visual_embeddings", []):
        require(embedding, files["embeddings"], ["embedding_id", "clip_id", "keyframe_id", "vector_path"])
        if embedding["clip_id"] not in clip_by_id:
            raise ValidationError(f"visual embedding {embedding['embedding_id']}: unknown clip_id")
        if embedding["keyframe_id"] is not None and embedding["keyframe_id"] not in keyframe_ids:
            raise ValidationError(f"visual embedding {embedding['embedding_id']}: unknown keyframe_id")
        if embedding["vector_path"] is not None:
            check_relative_path(embedding["vector_path"], f"visual embedding {embedding['embedding_id']}.vector_path")
        visual_clip_ids.add(embedding["clip_id"])
    expected_visual_clip_ids = {
        clip_id
        for clip_id, clip in clip_by_id.items()
        if clip.get("status", "usable") not in {"too_short", "error"}
    }
    missing_visual_embeddings = expected_visual_clip_ids - visual_clip_ids
    if missing_visual_embeddings:
        raise ValidationError(f"missing visual embeddings for clips: {sorted(missing_visual_embeddings)}")

    index = data["embeddings"].get("index")
    if index.get("path") is not None:
        check_relative_path(index["path"], "embedding.index.path")

    check_integer(data["matching"]["top_k"], "matching.top_k", minimum=1)
    candidate_set_ids = set()
    candidate_segment_ids = set()
    for candidate_set in matching_items:
        require(candidate_set, files["matching"], ["candidate_set_id", "audio_segment_id", "selected_clip_id", "confidence", "candidates"])
        set_id = candidate_set["candidate_set_id"]
        if set_id in candidate_set_ids:
            raise ValidationError(f"duplicate candidate_set_id {set_id!r}")
        candidate_set_ids.add(set_id)
        segment_id = candidate_set["audio_segment_id"]
        if segment_id not in segment_by_id:
            raise ValidationError(f"candidate set {set_id}: unknown audio_segment_id")
        candidate_segment_ids.add(segment_id)
        check_confidence(candidate_set["confidence"], f"candidate set {set_id}")
        candidates = candidate_set["candidates"]
        if not isinstance(candidates, list) or not candidates:
            raise ValidationError(f"candidate set {set_id}: candidates must be a non-empty array")
        if len(candidates) > data["matching"]["top_k"]:
            raise ValidationError(f"candidate set {set_id}: candidates exceed top_k")
        ranks = [candidate.get("rank") for candidate in candidates]
        if ranks != list(range(1, len(candidates) + 1)):
            raise ValidationError(f"candidate set {set_id}: ranks must be contiguous from 1")
        candidate_ids = []
        for candidate in candidates:
            require(candidate, files["matching"], ["rank", "clip_id", "final_score"])
            clip_id = candidate["clip_id"]
            if clip_id not in clip_by_id:
                raise ValidationError(f"candidate set {set_id}: unknown clip_id {clip_id!r}")
            candidate_ids.append(clip_id)
            for score_field in [
                "final_score",
                "semantic_score",
                "visual_quality_score",
                "duration_fit_score",
                "continuity_score",
                "diversity_score",
                "repetition_penalty",
                "bad_clip_penalty",
            ]:
                if score_field in candidate:
                    check_score(candidate.get(score_field), f"candidate set {set_id}.{clip_id}.{score_field}")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValidationError(f"candidate set {set_id}: duplicate clip_id in candidates")
        selected_clip_id = candidate_set["selected_clip_id"]
        if selected_clip_id is not None and selected_clip_id not in candidate_ids:
            raise ValidationError(f"candidate set {set_id}: selected_clip_id is not in candidates")
    missing_candidate_sets = set(segment_by_id) - candidate_segment_ids
    if missing_candidate_sets:
        raise ValidationError(f"missing candidate sets for segments: {sorted(missing_candidate_sets)}")

    render_settings = data["timeline"].get("render_settings")
    require(render_settings, files["timeline"], ["width", "height", "fps", "format"])
    check_integer(render_settings["width"], "timeline.render_settings.width", minimum=1)
    check_integer(render_settings["height"], "timeline.render_settings.height", minimum=1)
    check_positive(render_settings["fps"], "timeline.render_settings.fps")
    check_allowed(render_settings["format"], {"mp4"}, "timeline.render_settings.format")
    if "default_transition" in render_settings:
        check_allowed(render_settings["default_transition"], TRANSITION_VALUES, "timeline.render_settings.default_transition")
    if "crop_mode" in render_settings:
        check_allowed(render_settings["crop_mode"], CROP_MODE_VALUES, "timeline.render_settings.crop_mode")

    timeline_segment_ids = set()
    previous_timeline_end = 0.0
    for item in timeline_items:
        require(item, files["timeline"], ["segment_id", "audio_start", "audio_end", "duration", "text", "confidence", "score", "visual_items", "candidates_ref"])
        segment_id = item["segment_id"]
        if segment_id in timeline_segment_ids:
            raise ValidationError(f"timeline item {segment_id}: duplicate segment_id")
        timeline_segment_ids.add(segment_id)
        segment = segment_by_id.get(segment_id)
        if segment is None:
            raise ValidationError(f"timeline item {segment_id}: unknown segment_id")
        approx_equal(item["audio_start"], segment["start"], f"timeline item {segment_id}.audio_start")
        approx_equal(item["audio_end"], segment["end"], f"timeline item {segment_id}.audio_end")
        approx_equal(item["duration"], segment["duration"], f"timeline item {segment_id}.duration")
        if float(item["audio_start"]) < previous_timeline_end - EPS:
            raise ValidationError(f"timeline item {segment_id}: overlaps previous timeline item")
        previous_timeline_end = float(item["audio_end"])
        if item["text"] != segment["text"]:
            raise ValidationError(f"timeline item {segment_id}: text must match audio segment text")
        check_confidence(item["confidence"], f"timeline item {segment_id}")
        check_score(item["score"], f"timeline item {segment_id}.score")
        if item["candidates_ref"] is not None and item["candidates_ref"] not in candidate_set_ids:
            raise ValidationError(f"timeline item {segment_id}: candidates_ref not found")
        visual_items = item["visual_items"]
        if not isinstance(visual_items, list) or not visual_items:
            raise ValidationError(f"timeline item {segment_id}: visual_items must be a non-empty array for renderable samples")
        previous_visual_end = float(item["audio_start"])
        for visual in visual_items:
            require(visual, files["timeline"], ["timeline_item_id", "clip_id", "video_id", "source_path", "clip_start", "clip_end", "timeline_start", "timeline_end", "speed", "transition"])
            clip = clip_by_id.get(visual["clip_id"])
            if clip is None:
                raise ValidationError(f"timeline visual item {visual['timeline_item_id']}: unknown clip_id")
            if visual["video_id"] != clip["video_id"]:
                raise ValidationError(f"timeline visual item {visual['timeline_item_id']}: video_id must match clip metadata")
            if visual["source_path"] != clip.get("source_path"):
                raise ValidationError(f"timeline visual item {visual['timeline_item_id']}: source_path must match clip metadata")
            check_number(visual["clip_start"], f"timeline visual item {visual['timeline_item_id']}.clip_start", minimum=0)
            check_number(visual["clip_end"], f"timeline visual item {visual['timeline_item_id']}.clip_end", minimum=0)
            if float(visual["clip_start"]) < float(clip["start"]) - EPS or float(visual["clip_end"]) > float(clip["end"]) + EPS:
                raise ValidationError(f"timeline visual item {visual['timeline_item_id']}: clip range outside clip metadata range")
            check_number(visual["timeline_start"], f"timeline visual item {visual['timeline_item_id']}.timeline_start", minimum=0)
            check_number(visual["timeline_end"], f"timeline visual item {visual['timeline_item_id']}.timeline_end", minimum=0)
            if float(visual["timeline_start"]) < float(item["audio_start"]) - EPS or float(visual["timeline_end"]) > float(item["audio_end"]) + EPS:
                raise ValidationError(f"timeline visual item {visual['timeline_item_id']}: timeline range outside segment range")
            approx_equal(visual["timeline_start"], previous_visual_end, f"timeline visual item {visual['timeline_item_id']}.visual continuity")
            previous_visual_end = float(visual["timeline_end"])
            check_number(visual["speed"], f"timeline visual item {visual['timeline_item_id']}.speed")
            if not 0.75 <= float(visual["speed"]) <= 1.25:
                raise ValidationError(f"timeline visual item {visual['timeline_item_id']}: speed outside MVP range")
            visual_duration = (float(visual["clip_end"]) - float(visual["clip_start"])) / float(visual["speed"])
            timeline_duration = float(visual["timeline_end"]) - float(visual["timeline_start"])
            approx_equal(visual_duration, timeline_duration, f"timeline visual item {visual['timeline_item_id']}.duration")
            check_allowed(visual["transition"], TRANSITION_VALUES, f"timeline visual item {visual['timeline_item_id']}.transition")
            if "crop_mode" in visual and visual["crop_mode"] is not None:
                check_allowed(visual["crop_mode"], CROP_MODE_VALUES, f"timeline visual item {visual['timeline_item_id']}.crop_mode")
            if "effect" in visual:
                check_allowed(visual["effect"], EFFECT_VALUES, f"timeline visual item {visual['timeline_item_id']}.effect")
            if "volume" in visual:
                check_score(visual["volume"], f"timeline visual item {visual['timeline_item_id']}.volume")
        approx_equal(previous_visual_end, item["audio_end"], f"timeline item {segment_id}.visual end")
    missing_timeline_items = set(segment_by_id) - timeline_segment_ids
    if missing_timeline_items:
        raise ValidationError(f"missing timeline items for segments: {sorted(missing_timeline_items)}")
    approx_equal(previous_timeline_end, media_audio["duration"], "timeline total duration")

    output = data["render_config"].get("output", {})
    audio = data["render_config"].get("audio", {})
    video = data["render_config"].get("video", {})
    require(output, files["render_config"], ["path", "width", "height", "fps", "format"])
    require(audio, files["render_config"], ["voiceover_path", "keep_original_audio", "original_audio_volume"])
    require(video, files["render_config"], ["crop_mode", "default_transition"])
    check_relative_path(output["path"], "render_config.output.path")
    approx_equal(output["width"], render_settings["width"], "render_config.output.width")
    approx_equal(output["height"], render_settings["height"], "render_config.output.height")
    approx_equal(output["fps"], render_settings["fps"], "render_config.output.fps")
    if output["format"] != render_settings["format"]:
        raise ValidationError("render_config.output.format must match timeline.render_settings.format")
    if audio["voiceover_path"] != media_audio["normalized_path"]:
        raise ValidationError("render_config.audio.voiceover_path must match media_metadata.audio.normalized_path")
    if not isinstance(audio["keep_original_audio"], bool):
        raise ValidationError("render_config.audio.keep_original_audio must be boolean")
    check_score(audio["original_audio_volume"], "render_config.audio.original_audio_volume")
    check_allowed(video["crop_mode"], CROP_MODE_VALUES, "render_config.video.crop_mode")
    check_allowed(video["default_transition"], TRANSITION_VALUES, "render_config.video.default_transition")

    check_allowed(data["render_log"]["status"], RENDER_STATUS_VALUES, "render_log.status")
    check_relative_path(data["render_log"]["output_path"], "render_log.output_path")
    approx_equal(data["render_log"]["duration"], media_audio["duration"], "render_log.duration")
    check_number(data["render_log"]["render_time"], "render_log.render_time", minimum=0)
    if not isinstance(data["render_log"]["warnings"], list) or not isinstance(data["render_log"]["errors"], list):
        raise ValidationError("render_log.warnings and render_log.errors must be arrays")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON contracts against the shared schema rules.")
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=None,
        help="Directory with *_sample.json files (default: docs/samples).",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Directory with runtime JSON artifacts (e.g. data/intermediate).",
    )
    args = parser.parse_args()

    if args.samples_dir is not None and args.input_dir is not None:
        print("ERROR: use only one of --samples-dir or --input-dir")
        return 1

    if args.input_dir is not None:
        target_dir = args.input_dir
        runtime = True
        label = "runtime JSON contracts"
    else:
        target_dir = args.samples_dir or SAMPLES
        runtime = False
        label = "JSON samples"

    try:
        validate_samples(target_dir, runtime=runtime)
    except ValidationError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"OK: {label} validated in {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
