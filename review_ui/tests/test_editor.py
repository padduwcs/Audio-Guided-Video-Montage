"""Unit tests for review_ui.editor."""

import unittest
from pathlib import Path
from review_ui.loader import load_project_data
from review_ui.editor import replace_clip, create_visual_from_candidate, update_timing, update_speed, mark_reviewed

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SAMPLES_DIR = REPO_ROOT / "docs" / "samples"

class TestEditor(unittest.TestCase):
    def _get_clean_data(self):
        return load_project_data(
            timeline_path=str(SAMPLES_DIR / "timeline_sample.json"),
            matching_candidates_path=str(SAMPLES_DIR / "matching_candidates_sample.json"),
            clip_metadata_path=str(SAMPLES_DIR / "clip_metadata_sample.json"),
            audio_segments_path=str(SAMPLES_DIR / "audio_segments_sample.json"),
            media_metadata_path=str(SAMPLES_DIR / "media_metadata_sample.json"),
            project_id="demo_01"
        )

    def test_replace_clip_success(self):
        """Test replacing a clip with a valid candidate."""
        project_data = self._get_clean_data()
        item = project_data.timeline["items"][0]
        seg_id = item["segment_id"]
        vi_id = item["visual_items"][0]["timeline_item_id"]
        
        cref = item["candidates_ref"]
        candidates = project_data.candidate_sets_by_id[cref]["candidates"]
        cand_clip_id = candidates[1]["clip_id"]
        
        replace_clip(project_data, seg_id, vi_id, cand_clip_id)
        
        self.assertEqual(item["visual_items"][0]["clip_id"], cand_clip_id)
        self.assertTrue(item["user_edited"])

    def test_create_visual_from_candidate(self):
        """Test creating a visual item when empty."""
        project_data = self._get_clean_data()
        item = project_data.timeline["items"][0]
        seg_id = item["segment_id"]
        
        item["visual_items"] = []
        
        cref = item["candidates_ref"]
        candidates = project_data.candidate_sets_by_id[cref]["candidates"]
        cand_clip_id = candidates[0]["clip_id"]
        
        create_visual_from_candidate(project_data, seg_id, cand_clip_id)
        
        self.assertEqual(len(item["visual_items"]), 1)
        self.assertEqual(item["visual_items"][0]["clip_id"], cand_clip_id)
        self.assertTrue(item["user_edited"])

    def test_update_timing_speed_bounds(self):
        """Test timing update constraints."""
        project_data = self._get_clean_data()
        item = project_data.timeline["items"][0]
        seg_id = item["segment_id"]
        vi = item["visual_items"][0]
        vi_id = vi["timeline_item_id"]
        
        clip_id = vi["clip_id"]
        clip = project_data.clips_by_id[clip_id]
        
        # Valid timing update
        update_timing(project_data, seg_id, vi_id, clip["start"], clip["start"] + 5.0)
        
        # Out of bounds speed -> raises ValueError
        with self.assertRaises(ValueError):
            update_timing(project_data, seg_id, vi_id, clip["start"], clip["start"] + 0.1)

    def test_mark_reviewed(self):
        """Test marking as reviewed."""
        project_data = self._get_clean_data()
        item = project_data.timeline["items"][0]
        seg_id = item["segment_id"]
        
        item["needs_review"] = True
        mark_reviewed(project_data, seg_id)
        
        self.assertFalse(item["needs_review"])
        self.assertTrue(item["user_edited"])

if __name__ == "__main__":
    unittest.main()