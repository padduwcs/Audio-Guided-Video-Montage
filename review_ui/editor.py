"""Editor for Review UI (Stage 7).

Trách nhiệm:
- Cung cấp các transaction chỉnh timeline: replace_clip, create visual, update timing/speed, mark reviewed, chỉnh transition/crop/volume/locked.
- Đảm bảo atomic, chỉ mutate field được phép, preserve optional fields.
"""

# Transaction helpers below mutate only the allowed timeline fields.

def replace_clip(project_data, segment_id, visual_item_id, candidate_clip_id, locked=False):
    """
    Replace visual item clip by candidate.
    Update: clip_id, video_id, source_path, clip_start, clip_end, speed, source_candidate_rank, locked, user_edited.
    Preserve: candidates_ref, timeline_item_id, timing, notes, etc.
    """
    # Find timeline item
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        raise ValueError(f"Segment {segment_id} not found in timeline")
    # Find visual item
    visual_item = None
    for vi in timeline_item["visual_items"]:
        if vi["timeline_item_id"] == visual_item_id:
            visual_item = vi
            break
    if not visual_item:
        raise ValueError(f"Visual item {visual_item_id} not found in segment {segment_id}")
    # Find candidate in matching_candidates
    cref = timeline_item.get("candidates_ref")
    candidate_set = project_data.candidate_sets_by_id.get(cref)
    candidate = None
    if candidate_set:
        for cand in candidate_set.get("candidates", []):
            if cand["clip_id"] == candidate_clip_id:
                candidate = cand
                break
    # Find clip metadata
    clip = project_data.clips_by_id.get(candidate_clip_id)
    if not clip:
        raise ValueError(f"clip_id {candidate_clip_id} not found in clip_metadata")
    # Compute timing
    timeline_start = visual_item.get("timeline_start", timeline_item.get("audio_start"))
    timeline_end = visual_item.get("timeline_end", timeline_item.get("audio_end"))
    timeline_duration = timeline_end - timeline_start
    clip_start = clip["start"]
    # Fit clip duration to timeline duration, prefer speed=1.0 if possible
    clip_duration = clip["end"] - clip["start"]
    if clip_duration >= timeline_duration:
        new_clip_start = clip_start
        new_clip_end = new_clip_start + timeline_duration
        speed = 1.0
    else:
        speed = clip_duration / timeline_duration
        if not (0.75 <= speed <= 1.25):
            raise ValueError(f"Cannot fit clip {candidate_clip_id} to segment {segment_id} within speed range")
        new_clip_start = clip_start
        new_clip_end = clip["end"]
    # Update visual item fields
    visual_item.update({
        "clip_id": candidate_clip_id,
        "video_id": clip["video_id"],
        "source_path": clip.get("source_path"),
        "clip_start": new_clip_start,
        "clip_end": new_clip_end,
        "speed": speed,
        "source_candidate_rank": candidate["rank"] if candidate else None,
        "locked": locked,
    })
    timeline_item["user_edited"] = True

def create_visual_from_candidate(project_data, segment_id, candidate_clip_id):
    """
    Create new visual item for segment with visual_items=[] from candidate.
    """
    # Find timeline item
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        raise ValueError(f"Segment {segment_id} not found in timeline")
    if timeline_item["visual_items"]:
        raise ValueError(f"Segment {segment_id} already has visual_items")
    # Find candidate in matching_candidates
    cref = timeline_item.get("candidates_ref")
    candidate_set = project_data.candidate_sets_by_id.get(cref)
    candidate = None
    if candidate_set:
        for cand in candidate_set.get("candidates", []):
            if cand["clip_id"] == candidate_clip_id:
                candidate = cand
                break
    # Find clip metadata
    clip = project_data.clips_by_id.get(candidate_clip_id)
    if not clip:
        raise ValueError(f"clip_id {candidate_clip_id} not found in clip_metadata")
    # Compute timing
    timeline_start = timeline_item.get("audio_start")
    timeline_end = timeline_item.get("audio_end")
    timeline_duration = timeline_end - timeline_start
    clip_start = clip["start"]
    clip_duration = clip["end"] - clip["start"]
    if clip_duration >= timeline_duration:
        new_clip_start = clip_start
        new_clip_end = new_clip_start + timeline_duration
        speed = 1.0
    else:
        speed = clip_duration / timeline_duration
        if not (0.75 <= speed <= 1.25):
            raise ValueError(f"Cannot fit clip {candidate_clip_id} to segment {segment_id} within speed range")
        new_clip_start = clip_start
        new_clip_end = clip["end"]
    # Generate timeline_item_id
    idx = [i for i, item in enumerate(project_data.timeline["items"]) if item["segment_id"] == segment_id][0]
    timeline_item_id = f"t{str(idx+1).zfill(3)}_i01"
    # Build visual item
    visual_item = {
        "timeline_item_id": timeline_item_id,
        "clip_id": candidate_clip_id,
        "video_id": clip["video_id"],
        "source_path": clip.get("source_path"),
        "clip_start": new_clip_start,
        "clip_end": new_clip_end,
        "timeline_start": timeline_start,
        "timeline_end": timeline_end,
        "speed": speed,
        "transition": project_data.timeline.get("render_settings", {}).get("default_transition", "cut"),
        "effect": None,
        "crop_mode": project_data.timeline.get("render_settings", {}).get("crop_mode", "fit"),
        "volume": 0.0,
        "source_candidate_rank": candidate["rank"] if candidate else None,
        "locked": False,
    }
    timeline_item["visual_items"].append(visual_item)
    timeline_item["user_edited"] = True

def update_timing(project_data, segment_id, visual_item_id, clip_start, clip_end):
    """
    Update clip_start/clip_end and recalculate speed.
    """
    # Find timeline item
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        raise ValueError(f"Segment {segment_id} not found in timeline")
    # Find visual item
    visual_item = None
    for vi in timeline_item["visual_items"]:
        if vi["timeline_item_id"] == visual_item_id:
            visual_item = vi
            break
    if not visual_item:
        raise ValueError(f"Visual item {visual_item_id} not found in segment {segment_id}")
    # Validate range
    clip_id = visual_item["clip_id"]
    clip = project_data.clips_by_id.get(clip_id)
    if not clip:
        raise ValueError(f"clip_id {clip_id} not found in clip_metadata")
    if clip_start < clip["start"] - 0.01 or clip_end > clip["end"] + 0.01 or clip_end <= clip_start:
        raise ValueError(f"clip_start/end out of range for {clip_id}")
    # Compute speed
    timeline_start = visual_item.get("timeline_start", timeline_item.get("audio_start"))
    timeline_end = visual_item.get("timeline_end", timeline_item.get("audio_end"))
    timeline_duration = timeline_end - timeline_start
    source_duration = clip_end - clip_start
    speed = source_duration / timeline_duration
    if not (0.75 <= speed <= 1.25):
        raise ValueError(f"speed {speed:.2f} out of [0.75, 1.25]")
    # Update
    visual_item["clip_start"] = clip_start
    visual_item["clip_end"] = clip_end
    visual_item["speed"] = speed
    timeline_item["user_edited"] = True

def update_speed(project_data, segment_id, visual_item_id, speed):
    """
    Update speed and recalculate clip_end.
    """
    # Find timeline item
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        raise ValueError(f"Segment {segment_id} not found in timeline")
    # Find visual item
    visual_item = None
    for vi in timeline_item["visual_items"]:
        if vi["timeline_item_id"] == visual_item_id:
            visual_item = vi
            break
    if not visual_item:
        raise ValueError(f"Visual item {visual_item_id} not found in segment {segment_id}")
    if not (0.75 <= speed <= 1.25):
        raise ValueError(f"speed {speed:.2f} out of [0.75, 1.25]")
    # Compute new clip_end
    timeline_start = visual_item.get("timeline_start", timeline_item.get("audio_start"))
    timeline_end = visual_item.get("timeline_end", timeline_item.get("audio_end"))
    timeline_duration = timeline_end - timeline_start
    clip_start = visual_item["clip_start"]
    new_clip_end = clip_start + timeline_duration * speed
    clip_id = visual_item["clip_id"]
    clip = project_data.clips_by_id.get(clip_id)
    if not clip:
        raise ValueError(f"clip_id {clip_id} not found in clip_metadata")
    if new_clip_end > clip["end"] + 0.01:
        raise ValueError(f"clip_end {new_clip_end:.2f} > clip_metadata.end {clip['end']}")
    # Update
    visual_item["clip_end"] = new_clip_end
    visual_item["speed"] = speed
    timeline_item["user_edited"] = True

def mark_reviewed(project_data, segment_id):
    """
    Mark segment as reviewed (needs_review=False, user_edited=True).
    """
    # Find timeline item
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        raise ValueError(f"Segment {segment_id} not found in timeline")
    timeline_item["needs_review"] = False
    timeline_item["user_edited"] = True

def update_visual_properties(project_data, segment_id, visual_item_id, transition=None, crop_mode=None, volume=None, locked=None, notes=None, needs_review=None):
    """
    Update visual item properties (transition, crop_mode, volume, locked) and timeline item (notes, needs_review).
    """
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        raise ValueError(f"Segment {segment_id} not found in timeline")
    
    if needs_review is not None:
        timeline_item["needs_review"] = needs_review
    if notes is not None:
        timeline_item["notes"] = notes
    
    if visual_item_id:
        visual_item = None
        for vi in timeline_item.get("visual_items", []):
            if vi["timeline_item_id"] == visual_item_id:
                visual_item = vi
                break
        if visual_item:
            if transition is not None:
                visual_item["transition"] = transition
            if crop_mode is not None:
                visual_item["crop_mode"] = crop_mode
            if volume is not None:
                visual_item["volume"] = volume
            if locked is not None:
                visual_item["locked"] = locked
                
    timeline_item["user_edited"] = True

