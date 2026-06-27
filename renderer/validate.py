"""Validation logic for Stage 8 Renderer."""

import json
import os

def validate_timeline(timeline_path):
    if not os.path.exists(timeline_path):
        raise FileNotFoundError(f"Timeline file not found: {timeline_path}")
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    # Basic contract checks (expand as needed)
    required_fields = ["schema_version", "project_id", "audio_id", "created_at", "updated_at", "render_settings", "items"]
    for field in required_fields:
        if field not in timeline:
            raise ValueError(f"Missing required field in timeline.json: {field}")

    if not isinstance(timeline["items"], list) or not timeline["items"]:
        raise ValueError("timeline.items must be a non-empty list")

    # Check each item for required fields
    for idx, item in enumerate(timeline["items"]):
        for f in ["segment_id", "audio_start", "audio_end", "duration", "visual_items"]:
            if f not in item:
                raise ValueError(f"Missing field '{f}' in timeline.items[{idx}]")
        if not isinstance(item["visual_items"], list):
            raise ValueError(f"visual_items must be a list in timeline.items[{idx}]")
        if len(item["visual_items"]) == 0:
            raise ValueError(f"visual_items is empty in timeline.items[{idx}] (segment_id: {item.get('segment_id')}) - Cannot render MVP timeline with missing visual items")
        for vidx, vi in enumerate(item["visual_items"]):
            if "source_path" not in vi or not vi["source_path"]:
                raise ValueError(f"Missing source_path in visual_items[{vidx}] of segment {item.get('segment_id')}")
            clip_start = vi.get("clip_start")
            clip_end = vi.get("clip_end")
            if clip_start is None or clip_end is None:
                raise ValueError(f"Missing clip_start/clip_end in visual_items[{vidx}] of segment {item.get('segment_id')}")
            if clip_end <= clip_start:
                raise ValueError(f"clip_end ({clip_end}) <= clip_start ({clip_start}) in visual_items[{vidx}] of segment {item.get('segment_id')}")
            speed = vi.get("speed", 1.0)
            if not (0.75 <= speed <= 1.25):
                raise ValueError(f"speed {speed} out of range [0.75, 1.25] in visual_items[{vidx}] of segment {item.get('segment_id')}")

    # TODO: Add more contract checks as per schema

    return True