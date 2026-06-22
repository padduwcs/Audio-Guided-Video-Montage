"""Storage utilities for Review UI (Stage 7).

Trách nhiệm:
- Save timeline an toàn (atomic write).
- Backup timeline.before_review.json nếu cần.
- Ghi review_ui_log.json nếu bật.
- Preserve unknown optional fields khi save.
"""

import os

import json
import time

def save_timeline(timeline_data, path, updated_at=None, validate_fn=None):
    """
    Validate and save timeline.json atomically. Update updated_at if provided.
    Only save if no error contract.
    """
    # Validate before save
    if validate_fn:
        msgs = validate_fn(timeline_data)
        errors = [m for m in msgs if m.level == "error"]
        if errors:
            raise ValueError(f"Cannot save: contract errors: {errors}")
    # Update updated_at
    if updated_at is not None:
        timeline_data["updated_at"] = updated_at
    else:
        timeline_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_write(timeline_data, path)

def backup_timeline(timeline_data, backup_path):
    """
    Save backup timeline.before_review.json.
    """
    atomic_write(timeline_data, backup_path)

def atomic_write(data, path):
    """
    Write data to path atomically (via temp file and rename).
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
