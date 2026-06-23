"""Unified unit tests for review_ui."""

import unittest
import os
import json
import tempfile
from pathlib import Path
from review_ui.loader import load_project_data, ProjectData
from review_ui.validator import validate_project_data
from review_ui.editor import replace_clip, create_visual_from_candidate, update_timing, update_speed, mark_reviewed
from review_ui.storage import save_timeline, backup_timeline
from review_ui.media import resolve_video_path, resolve_audio_path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SAMPLES_DIR = REPO_ROOT / "docs" / "samples"

# Force tempdir inside the workspace to avoid sandbox block on /var/folders/
LOCAL_TMP_DIR = os.path.join(REPO_ROOT, "tmp")
os.makedirs(LOCAL_TMP_DIR, exist_ok=True)
tempfile.tempdir = LOCAL_TMP_DIR

class TestUnified(unittest.TestCase):
    def _get_clean_data(self):
        return load_project_data(
            timeline_path=str(SAMPLES_DIR / "timeline_sample.json"),
            matching_candidates_path=str(SAMPLES_DIR / "matching_candidates_sample.json"),
            clip_metadata_path=str(SAMPLES_DIR / "clip_metadata_sample.json"),
            audio_segments_path=str(SAMPLES_DIR / "audio_segments_sample.json"),
            media_metadata_path=str(SAMPLES_DIR / "media_metadata_sample.json"),
            project_id="demo_01"
        )

    # --- Loader Tests ---
    def test_load_project_data_success(self):
        project_data = self._get_clean_data()
        self.assertIsInstance(project_data, ProjectData)
        self.assertEqual(project_data.timeline["project_id"], "demo_01")
        self.assertGreater(len(project_data.segments_by_id), 0)

    def test_load_project_data_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_project_data(
                timeline_path="nonexistent.json",
                matching_candidates_path="nonexistent.json",
                clip_metadata_path="nonexistent.json",
                audio_segments_path="nonexistent.json",
                media_metadata_path="nonexistent.json"
            )

    def test_load_project_data_id_mismatch(self):
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

    # --- Validator Tests ---
    def test_validate_success(self):
        project_data = self._get_clean_data()
        msgs = validate_project_data(project_data, mode="edit_save")
        errors = [m for m in msgs if m.level == "error"]
        self.assertEqual(len(errors), 0)

    def test_validate_invalid_speed(self):
        project_data = self._get_clean_data()
        project_data.timeline["items"][0]["visual_items"][0]["speed"] = 1.5
        msgs = validate_project_data(project_data, mode="edit_save")
        errors = [m for m in msgs if m.code == "SPEED_OUT_OF_RANGE"]
        self.assertEqual(len(errors), 1)

    def test_validate_missing_visual_handoff(self):
        project_data = self._get_clean_data()
        project_data.timeline["items"][0]["visual_items"] = []
        
        msgs_edit = validate_project_data(project_data, mode="edit_save")
        warnings = [m for m in msgs_edit if m.code == "MISSING_VISUAL" and m.level == "warning"]
        self.assertEqual(len(warnings), 1)
        
        msgs_handoff = validate_project_data(project_data, mode="renderer_handoff")
        errors = [m for m in msgs_handoff if m.code == "MISSING_VISUAL" and m.level == "error"]
        self.assertEqual(len(errors), 1)

    def test_validate_invalid_transition(self):
        project_data = self._get_clean_data()
        project_data.timeline["items"][0]["visual_items"][0]["transition"] = "dissolve"
        msgs = validate_project_data(project_data, mode="edit_save")
        errors = [m for m in msgs if m.code == "INVALID_TRANSITION"]
        self.assertEqual(len(errors), 1)

    # --- Editor Tests ---
    def test_replace_clip_success(self):
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
        project_data = self._get_clean_data()
        item = project_data.timeline["items"][0]
        seg_id = item["segment_id"]
        vi = item["visual_items"][0]
        vi_id = vi["timeline_item_id"]
        
        clip_id = vi["clip_id"]
        clip = project_data.clips_by_id[clip_id]
        
        update_timing(project_data, seg_id, vi_id, clip["start"], clip["start"] + 5.0)
        with self.assertRaises(ValueError):
            update_timing(project_data, seg_id, vi_id, clip["start"], clip["start"] + 0.1)

    def test_mark_reviewed(self):
        project_data = self._get_clean_data()
        item = project_data.timeline["items"][0]
        seg_id = item["segment_id"]
        item["needs_review"] = True
        mark_reviewed(project_data, seg_id)
        self.assertFalse(item["needs_review"])
        self.assertTrue(item["user_edited"])

    # --- Storage Tests ---
    def test_save_and_backup_timeline(self):
        project_data = self._get_clean_data()
        
        timeline_file = os.path.join(LOCAL_TMP_DIR, "timeline.json")
        backup_file = os.path.join(LOCAL_TMP_DIR, "timeline.before_review.json")
        
        save_timeline(project_data.timeline, timeline_file)
        self.assertTrue(os.path.exists(timeline_file))
        
        with open(timeline_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["project_id"], "demo_01")
        self.assertIn("updated_at", saved_data)
        
        backup_timeline(project_data.timeline, backup_file)
        self.assertTrue(os.path.exists(backup_file))
        
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        self.assertEqual(backup_data["project_id"], "demo_01")

    # --- Media Tests ---
    def test_resolve_paths(self):
        project_data = self._get_clean_data()
        audio_path = resolve_audio_path(project_data)
        self.assertEqual(audio_path, "data/normalized/voiceover.wav")
        
        first_seg_id = project_data.timeline["items"][0]["segment_id"]
        vi_id = project_data.timeline["items"][0]["visual_items"][0]["timeline_item_id"]
        
        video_path = resolve_video_path(project_data, first_seg_id, vi_id)
        self.assertIsNotNone(video_path)
        self.assertTrue("data/normalized/" in video_path or "video_" in video_path)

if __name__ == "__main__":
    unittest.main()
