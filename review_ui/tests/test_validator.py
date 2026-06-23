"""Unit tests for review_ui.validator."""

import unittest
from pathlib import Path
from review_ui.loader import load_project_data
from review_ui.validator import validate_project_data

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SAMPLES_DIR = REPO_ROOT / "docs" / "samples"

class TestValidator(unittest.TestCase):
    def _get_clean_data(self):
        return load_project_data(
            timeline_path=str(SAMPLES_DIR / "timeline_sample.json"),
            matching_candidates_path=str(SAMPLES_DIR / "matching_candidates_sample.json"),
            clip_metadata_path=str(SAMPLES_DIR / "clip_metadata_sample.json"),
            audio_segments_path=str(SAMPLES_DIR / "audio_segments_sample.json"),
            media_metadata_path=str(SAMPLES_DIR / "media_metadata_sample.json"),
            project_id="demo_01"
        )

    def test_validate_success(self):
        """Test validation of clean sample data."""
        project_data = self._get_clean_data()
        msgs = validate_project_data(project_data, mode="edit_save")
        errors = [m for m in msgs if m.level == "error"]
        if errors:
            print("VALIDATION ERRORS:")
            for err in errors:
                print(f"Code: {err.code}, Segment: {err.segment_id}, Msg: {err.message}")
        self.assertEqual(len(errors), 0)

    def test_validate_invalid_speed(self):
        """Test validator catches invalid clip speed."""
        project_data = self._get_clean_data()
        project_data.timeline["items"][0]["visual_items"][0]["speed"] = 1.5
        
        msgs = validate_project_data(project_data, mode="edit_save")
        errors = [m for m in msgs if m.code == "SPEED_OUT_OF_RANGE"]
        self.assertEqual(len(errors), 1)

    def test_validate_missing_visual_handoff(self):
        """Test validator catches empty visual items in handoff mode."""
        project_data = self._get_clean_data()
        project_data.timeline["items"][0]["visual_items"] = []
        
        # In edit_save mode, it should be a warning
        msgs_edit = validate_project_data(project_data, mode="edit_save")
        warnings = [m for m in msgs_edit if m.code == "MISSING_VISUAL" and m.level == "warning"]
        self.assertEqual(len(warnings), 1)
        
        # In renderer_handoff mode, it must be an error
        msgs_handoff = validate_project_data(project_data, mode="renderer_handoff")
        errors = [m for m in msgs_handoff if m.code == "MISSING_VISUAL" and m.level == "error"]
        self.assertEqual(len(errors), 1)

    def test_validate_invalid_transition(self):
        """Test validator catches invalid transition setting."""
        project_data = self._get_clean_data()
        project_data.timeline["items"][0]["visual_items"][0]["transition"] = "dissolve"
        
        msgs = validate_project_data(project_data, mode="edit_save")
        errors = [m for m in msgs if m.code == "INVALID_TRANSITION"]
        self.assertEqual(len(errors), 1)

if __name__ == "__main__":
    unittest.main()