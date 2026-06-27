import json
import os

OVERRIDE_FILE = "data/correct/override_mapping.json"

def get_feedback_override(segment_id):
    if not os.path.exists(OVERRIDE_FILE):
        return None
    try:
        with open(OVERRIDE_FILE, "r") as f:
            mapping = json.load(f)
            return mapping.get(segment_id)
    except Exception:
        return None
