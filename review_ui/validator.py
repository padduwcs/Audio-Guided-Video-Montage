"""Validator for Review UI (Stage 7).

Trách nhiệm:
- Validate schema, cross-file mapping, renderer-readiness cho toàn bộ project data.
- Phân loại error/warning/info theo Data Contract.
- Chuẩn hóa format ValidationMessage.
"""


class ValidationMessage:
    def __init__(self, level, code, message, file=None, segment_id=None, timeline_item_id=None, field=None):
        self.level = level  # "error", "warning", "info"
        self.code = code
        self.message = message
        self.file = file
        self.segment_id = segment_id
        self.timeline_item_id = timeline_item_id
        self.field = field

    def __repr__(self):
        return f"[{self.level.upper()}] {self.code}: {self.message}"

def validate_project_data(project_data, mode="edit_save"):
    """
    Validate all loaded project data.
    mode: "edit_save" (chặn lỗi contract nghiêm trọng), "renderer_handoff" (chặn thêm visual_items=[] và source_path missing)
    Returns: List[ValidationMessage]
    """
    msgs = []
    timeline = project_data.timeline
    audio_segments = project_data.audio_segments
    clip_metadata = project_data.clip_metadata
    matching_candidates = project_data.matching_candidates
    media_metadata = project_data.media_metadata

    # Top-level checks
    for name, obj in [
        ("timeline.json", timeline),
        ("matching_candidates.json", matching_candidates),
        ("clip_metadata.json", clip_metadata),
        ("audio_segments.json", audio_segments),
        ("media_metadata.json", media_metadata),
    ]:
        for field in ["schema_version", "project_id"]:
            if field not in obj:
                msgs.append(ValidationMessage("error", "MISSING_FIELD", f"{name} missing {field}", file=name, field=field))
    # Timeline top-level
    for field in ["audio_id", "created_at", "updated_at", "render_settings", "items"]:
        if field not in timeline:
            msgs.append(ValidationMessage("error", "MISSING_FIELD", f"timeline.json missing {field}", file="timeline.json", field=field))
    if not isinstance(timeline.get("items", []), list) or not timeline.get("items"):
        msgs.append(ValidationMessage("error", "EMPTY_TIMELINE", "timeline.items is empty", file="timeline.json", field="items"))

    # Render settings
    rs = timeline.get("render_settings", {})
    for f in ["width", "height", "fps", "format"]:
        if f not in rs:
            msgs.append(ValidationMessage("error", "MISSING_RENDER_SETTING", f"render_settings missing {f}", file="timeline.json", field=f))
    if rs.get("format") not in ("mp4", None):
        msgs.append(ValidationMessage("error", "INVALID_FORMAT", f"render_settings.format must be mp4", file="timeline.json", field="format"))

    # Cross-file mapping
    seg_ids = set(project_data.segments_by_id)
    clip_ids = set(project_data.clips_by_id)
    video_ids = set(project_data.videos_by_id)
    candidate_set_ids = set(project_data.candidate_sets_by_id)
    candidate_set_seg_ids = set(project_data.candidate_sets_by_segment_id)

    # Timeline items
    for item in timeline.get("items", []):
        seg_id = item.get("segment_id")
        if seg_id not in seg_ids:
            msgs.append(ValidationMessage("error", "SEGMENT_ID_NOT_FOUND", f"segment_id {seg_id} not in audio_segments", file="timeline.json", segment_id=seg_id, field="segment_id"))
            continue
        seg = project_data.segments_by_id[seg_id]
        # Text exact match
        if item.get("text") != seg.get("text"):
            msgs.append(ValidationMessage("error", "TEXT_MISMATCH", f"text mismatch for segment_id {seg_id}", file="timeline.json", segment_id=seg_id, field="text"))
        # Audio timing match (tolerance 0.01s)
        for f in ["audio_start", "audio_end", "duration"]:
            seg_val = None
            if f == "audio_start":
                seg_val = seg.get("start", 0)
            elif f == "audio_end":
                seg_val = seg.get("end", 0)
            else:
                seg_val = seg.get(f, 0)
            if abs(item.get(f, 0) - seg_val) > 0.01:
                msgs.append(ValidationMessage("error", "AUDIO_TIMING_MISMATCH", f"{f} mismatch for segment_id {seg_id}", file="timeline.json", segment_id=seg_id, field=f))
        # Confidence
        if item.get("confidence") not in ("high", "medium", "low"):
            msgs.append(ValidationMessage("error", "INVALID_CONFIDENCE", f"Invalid confidence for segment_id {seg_id}", file="timeline.json", segment_id=seg_id, field="confidence"))
        # Candidates_ref
        cref = item.get("candidates_ref")
        if cref and cref not in candidate_set_ids:
            msgs.append(ValidationMessage("error", "CANDIDATES_REF_NOT_FOUND", f"candidates_ref {cref} not in matching_candidates", file="timeline.json", segment_id=seg_id, field="candidates_ref"))
        # Visual items
        visual_items = item.get("visual_items", [])
        if not isinstance(visual_items, list):
            msgs.append(ValidationMessage("error", "VISUAL_ITEMS_NOT_LIST", f"visual_items not a list for segment_id {seg_id}", file="timeline.json", segment_id=seg_id, field="visual_items"))
            continue
        if not visual_items:
            if mode == "renderer_handoff":
                msgs.append(ValidationMessage("error", "MISSING_VISUAL", f"visual_items is empty for segment_id {seg_id} (not render-ready)", file="timeline.json", segment_id=seg_id, field="visual_items"))
            else:
                msgs.append(ValidationMessage("warning", "MISSING_VISUAL", f"visual_items is empty for segment_id {seg_id}", file="timeline.json", segment_id=seg_id, field="visual_items"))
        for vi in visual_items:
            # Required fields
            for f in ["timeline_item_id", "clip_id", "video_id", "source_path", "clip_start", "clip_end", "timeline_start", "timeline_end", "speed", "transition"]:
                if f not in vi:
                    msgs.append(ValidationMessage("error", "MISSING_FIELD", f"visual_item missing {f} for segment_id {seg_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field=f))
            # Clip_id
            clip_id = vi.get("clip_id")
            if clip_id and clip_id not in clip_ids:
                msgs.append(ValidationMessage("error", "CLIP_ID_NOT_FOUND", f"clip_id {clip_id} not in clip_metadata", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="clip_id"))
            # Video_id
            video_id = vi.get("video_id")
            if video_id and video_id not in video_ids:
                msgs.append(ValidationMessage("error", "VIDEO_ID_NOT_FOUND", f"video_id {video_id} not in media_metadata", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="video_id"))
            # Clip timing
            if clip_id in clip_ids:
                clip = project_data.clips_by_id[clip_id]
                if vi.get("clip_start", 0) < clip.get("start", 0) - 0.01:
                    msgs.append(ValidationMessage("error", "CLIP_START_OUT_OF_RANGE", f"clip_start < clip_metadata.start for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="clip_start"))
                if vi.get("clip_end", 0) > clip.get("end", 0) + 0.01:
                    msgs.append(ValidationMessage("error", "CLIP_END_OUT_OF_RANGE", f"clip_end > clip_metadata.end for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="clip_end"))
                if vi.get("clip_end", 0) <= vi.get("clip_start", 0):
                    msgs.append(ValidationMessage("error", "CLIP_END_BEFORE_START", f"clip_end <= clip_start for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="clip_end"))
            # Speed
            speed = vi.get("speed")
            if speed is not None and (speed < 0.75 or speed > 1.25):
                msgs.append(ValidationMessage("error", "SPEED_OUT_OF_RANGE", f"speed {speed} out of [0.75, 1.25] for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="speed"))
            # Transition
            if vi.get("transition") not in ("cut", "fade", "crossfade"):
                msgs.append(ValidationMessage("error", "INVALID_TRANSITION", f"Invalid transition for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="transition"))
            # Effect
            if "effect" in vi and vi["effect"] not in (None, "none"):
                msgs.append(ValidationMessage("error", "INVALID_EFFECT", f"Invalid effect for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="effect"))
            # Crop mode
            if "crop_mode" in vi and vi["crop_mode"] not in (None, "fit", "fill", "center_crop", "blur_background"):
                msgs.append(ValidationMessage("error", "INVALID_CROP_MODE", f"Invalid crop_mode for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="crop_mode"))
            # Volume
            if "volume" in vi and (vi["volume"] is not None) and (vi["volume"] < 0.0 or vi["volume"] > 1.0):
                msgs.append(ValidationMessage("error", "VOLUME_OUT_OF_RANGE", f"volume {vi['volume']} out of [0.0, 1.0] for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="volume"))
            # Source path
            if mode == "renderer_handoff" and not vi.get("source_path"):
                msgs.append(ValidationMessage("error", "MISSING_SOURCE_PATH", f"Missing source_path for {clip_id}", file="timeline.json", segment_id=seg_id, timeline_item_id=vi.get("timeline_item_id"), field="source_path"))
    # Duplicate segment_id
    seen_seg = set()
    for item in timeline.get("items", []):
        seg_id = item.get("segment_id")
        if seg_id in seen_seg:
            msgs.append(ValidationMessage("error", "DUPLICATE_SEGMENT_ID", f"Duplicate segment_id {seg_id} in timeline", file="timeline.json", segment_id=seg_id, field="segment_id"))
        seen_seg.add(seg_id)
    # Duplicate timeline_item_id
    seen_ti = set()
    for item in timeline.get("items", []):
        for vi in item.get("visual_items", []):
            tiid = vi.get("timeline_item_id")
            if tiid in seen_ti:
                msgs.append(ValidationMessage("error", "DUPLICATE_TIMELINE_ITEM_ID", f"Duplicate timeline_item_id {tiid} in timeline", file="timeline.json", timeline_item_id=tiid, field="timeline_item_id"))
            seen_ti.add(tiid)
    # Candidates mapping
    for cs in matching_candidates.get("items", []):
        if cs.get("audio_segment_id") not in seg_ids:
            msgs.append(ValidationMessage("error", "CANDIDATE_SEGMENT_ID_NOT_FOUND", f"audio_segment_id {cs.get('audio_segment_id')} in matching_candidates not in audio_segments", file="matching_candidates.json", segment_id=cs.get("audio_segment_id"), field="audio_segment_id"))
        for cand in cs.get("candidates", []):
            cid = cand.get("clip_id")
            if cid and cid not in clip_ids:
                msgs.append(ValidationMessage("error", "CANDIDATE_CLIP_ID_NOT_FOUND", f"clip_id {cid} in matching_candidates not in clip_metadata", file="matching_candidates.json", field="clip_id"))
            if "rank" in cand and (not isinstance(cand["rank"], int) or cand["rank"] < 1):
                msgs.append(ValidationMessage("error", "INVALID_CANDIDATE_RANK", f"Invalid rank for candidate {cid}", file="matching_candidates.json", field="rank"))
            if "final_score" in cand and (cand["final_score"] < 0.0 or cand["final_score"] > 1.0):
                msgs.append(ValidationMessage("error", "FINAL_SCORE_OUT_OF_RANGE", f"final_score {cand['final_score']} out of [0.0, 1.0] for {cid}", file="matching_candidates.json", field="final_score"))
    # Warnings
    for item in timeline.get("items", []):
        if item.get("confidence") == "low":
            msgs.append(ValidationMessage("warning", "LOW_CONFIDENCE", f"Segment {item.get('segment_id')} has low confidence", file="timeline.json", segment_id=item.get("segment_id"), field="confidence"))
        if item.get("needs_review"):
            msgs.append(ValidationMessage("warning", "NEEDS_REVIEW", f"Segment {item.get('segment_id')} needs review", file="timeline.json", segment_id=item.get("segment_id"), field="needs_review"))
        if item.get("fallback_used"):
            msgs.append(ValidationMessage("warning", "FALLBACK_USED", f"Segment {item.get('segment_id')} used fallback", file="timeline.json", segment_id=item.get("segment_id"), field="fallback_used"))
    return msgs
