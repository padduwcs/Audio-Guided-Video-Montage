"""Unit tests for review_ui.loader."""

import unittest
from pathlib import Path
from review_ui.loader import load_project_data, ProjectData

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SAMPLES_DIR = REPO_ROOT / "docs" / "samples"

class TestLoader(unittest.TestCase):
    def test_load_project_data_success(self):
        """Test loading valid sample files."""
        timeline_path = str(SAMPLES_DIR / "timeline_sample.json")
        matching_candidates_path = str(SAMPLES_DIR / "matching_candidates_sample.json")
        clip_metadata_path = str(SAMPLES_DIR / "clip_metadata_sample.json")
        audio_segments_path = str(SAMPLES_DIR / "audio_segments_sample.json")
        media_metadata_path = str(SAMPLES_DIR / "media_metadata_sample.json")

        project_data = load_project_data(
            timeline_path=timeline_path,
            matching_candidates_path=matching_candidates_path,
            clip_metadata_path=clip_metadata_path,
            audio_segments_path=audio_segments_path,
            media_metadata_path=media_metadata_path,
            project_id="demo_01"
        )

        self.assertIsInstance(project_data, ProjectData)
        self.assertEqual(project_data.timeline["project_id"], "demo_01")
        self.assertGreater(len(project_data.segments_by_id), 0)
        self.assertGreater(len(project_data.clips_by_id), 0)
        self.assertGreater(len(project_data.videos_by_id), 0)
        self.assertGreater(len(project_data.candidate_sets_by_id), 0)

    def test_load_project_data_missing_file(self):
        """Test loader handles missing file error."""
        with self.assertRaises(FileNotFoundError):
            load_project_data(
                timeline_path="nonexistent.json",
                matching_candidates_path="nonexistent.json",
                clip_metadata_path="nonexistent.json",
                audio_segments_path="nonexistent.json",
                media_metadata_path="nonexistent.json"
            )

    def test_load_project_data_id_mismatch(self):
        """Test loader raises ValueError on project_id mismatch."""
        timeline_path = str(SAMPLES_DIR / "timeline_sample.json")
        matching_candidates_path = str(SAMPLES_DIR / "matching_candidates_sample.json")
        clip_metadata_path = str(SAMPLES_DIR / "clip_metadata_sample.json")
        audio_segments_path = str(SAMPLES_DIR / "audio_segments_sample.json")
        media_metadata_path = str(SAMPLES_DIR / "media_metadata_sample.json")

        with self.assertRaisesRegex(ValueError, "project_id mismatch"):
            load_project_data(
                timeline_path=timeline_path,
                matching_candidates_path=matching_candidates_path,
                clip_metadata_path=clip_metadata_path,
                audio_segments_path=audio_segments_path,
                media_metadata_path=media_metadata_path,
                project_id="wrong_id"
            )

if __name__ == "__main__":
    unittest.main()