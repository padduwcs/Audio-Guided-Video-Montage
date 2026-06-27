"""Unit tests for renderer.validate."""

import os
import pytest
from renderer.validate import validate_timeline

SAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/samples"))

def test_validate_timeline_sample():
    timeline_path = os.path.join(SAMPLES_DIR, "timeline_sample.json")
    assert validate_timeline(timeline_path) is True

def test_validate_timeline_missing_file():
    with pytest.raises(FileNotFoundError):
        validate_timeline("nonexistent_timeline.json")

def test_validate_timeline_missing_field(tmp_path):
    # Create a minimal invalid timeline
    invalid = {
        "schema_version": "1.0",
        "project_id": "demo_01",
        "audio_id": "audio_01",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "render_settings": {},
        # Missing "items"
    }
    f = tmp_path / "invalid_timeline.json"
    f.write_text(str(invalid))
    with pytest.raises(ValueError):
        validate_timeline(str(f))