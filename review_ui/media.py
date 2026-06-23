"""Media utilities for Review UI (Stage 7).

Trách nhiệm:
- Resolve path preview video/audio an toàn từ timeline, clip_metadata, media_metadata.
- Không trả về absolute path khi save.
- Chỉ resolve path nội bộ repo/data.
"""

def resolve_video_path(project_data, segment_id, visual_item_id=None):
    """
    Resolve video preview path for a given segment/visual item.
    Priority: visual_items[].source_path > clip_metadata.source_path > media_metadata.videos[].normalized_path
    """
    # Try visual_items[].source_path
    timeline_item = None
    for item in project_data.timeline["items"]:
        if item["segment_id"] == segment_id:
            timeline_item = item
            break
    if not timeline_item:
        return None
    if visual_item_id:
        for vi in timeline_item.get("visual_items", []):
            if vi["timeline_item_id"] == visual_item_id:
                if vi.get("source_path"):
                    return vi["source_path"]
                clip_id = vi.get("clip_id")
                break
        else:
            return None
    else:
        # First visual item
        if timeline_item.get("visual_items"):
            vi = timeline_item["visual_items"][0]
            if vi.get("source_path"):
                return vi["source_path"]
            clip_id = vi.get("clip_id")
        else:
            return None
    # Try clip_metadata
    clip = project_data.clips_by_id.get(clip_id)
    if clip and clip.get("source_path"):
        return clip["source_path"]
    # Try media_metadata
    video_id = clip.get("video_id") if clip else None
    if video_id:
        video = project_data.videos_by_id.get(video_id)
        if video and video.get("normalized_path"):
            return video["normalized_path"]
    return None

def resolve_audio_path(project_data):
    """
    Resolve audio preview path (voice-over).
    """
    audio = project_data.media_metadata.get("audio", {})
    return audio.get("normalized_path")
