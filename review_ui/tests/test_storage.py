"""Unit tests for review_ui.storage."""

import json
import os
from pathlib import Path
import tempfile
from review_ui.loader import load_project_data
from review_ui.storage import save_timeline, backup_timeline

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SAMPLES_DIR = REPO_ROOT / "docs" / "samples"

def _get_clean_data():
    return load_project_data(
        timeline_path=str(SAMPLES_DIR / "timeline_sample.json"),
        matching_candidates_path=str(SAMPLES_DIR / "matching_candidates_sample.json"),
        clip_metadata_path=str(SAMPLES_DIR / "clip_metadata_sample.json"),
        audio_segments_path=str(SAMPLES_DIR / "audio_segments_sample.json"),
        media_metadata_path=str(SAMPLES_DIR / "media_metadata_sample.json"),
        project_id="demo_01"
    )

def test_save_and_backup_timeline():
    """Test saving and backing up timeline data."""
    project_data = _get_clean_data()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        timeline_file = os.path.join(tmpdir, "timeline.json")
        backup_file = os.path.join(tmpdir, "timeline.before_review.json")
        
        # Save
        save_timeline(project_data.timeline, timeline_file)
        assert os.path.exists(timeline_file)
        
        # Verify saved data
        with open(timeline_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["project_id"] == "demo_01"
        assert "updated_at" in saved_data
        
        # Backup
        backup_timeline(project_data.timeline, backup_file)
        assert os.path.exists(backup_file)
        
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        assert backup_data["project_id"] == "demo_01"

if __name__ == "__main__":
    unittest.main()