"""Unit tests for review_ui.media."""

import unittest
from pathlib import Path
from review_ui.loader import load_project_data
from review_ui.media import resolve_video_path, resolve_audio_path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SAMPLES_DIR = REPO_ROOT / "docs" / "samples"

class TestMedia(unittest.TestCase):
    def _get_clean_data(self):
        return load_project_data(
            timeline_path=str(SAMPLES_DIR / "timeline_sample.json"),
            matching_candidates_path=str(SAMPLES_DIR / "matching_candidates_sample.json"),
            clip_metadata_path=str(SAMPLES_DIR / "clip_metadata_sample.json"),
            audio_segments_path=str(SAMPLES_DIR / "audio_segments_sample.json"),
            media_metadata_path=str(SAMPLES_DIR / "media_metadata_sample.json"),
            project_id="demo_01"
        )

    def test_resolve_paths(self):
        """Test resolving video and audio preview paths."""
        project_data = self._get_clean_data()
        
        # Audio
        audio_path = resolve_audio_path(project_data)
        self.assertEqual(audio_path, "data/normalized/voiceover.wav")
        
        # Video
        first_seg_id = project_data.timeline["items"][0]["segment_id"]
        vi_id = project_data.timeline["items"][0]["visual_items"][0]["timeline_item_id"]
        
        video_path = resolve_video_path(project_data, first_seg_id, vi_id)
        self.assertIsNotNone(video_path)
        self.assertTrue("data/normalized/" in video_path or "video_" in video_path)

if __name__ == "__main__":
    unittest.main()