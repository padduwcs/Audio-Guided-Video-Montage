from __future__ import annotations

import unittest

from timeline_planner.planner import build_timeline


class TimelinePlannerTests(unittest.TestCase):
    def test_reuses_valid_candidate_to_cover_long_segment(self) -> None:
        media = {
            "project_id": "test",
            "audio": {"audio_id": "audio_01", "duration": 10.0},
            "videos": [
                {
                    "video_id": "video_01",
                    "normalized_path": "data/normalized/video.mp4",
                }
            ],
        }
        audio = {
            "project_id": "test",
            "items": [
                {
                    "segment_id": "a001",
                    "start": 0.0,
                    "end": 10.0,
                    "duration": 10.0,
                    "text": "Nội dung.",
                }
            ],
        }
        clips = {
            "project_id": "test",
            "items": [
                {
                    "clip_id": "clip_01",
                    "video_id": "video_01",
                    "start": 0.0,
                    "end": 2.0,
                    "duration": 2.0,
                    "status": "usable",
                    "source_path": "data/normalized/video.mp4",
                }
            ],
        }
        matching = {
            "project_id": "test",
            "items": [
                {
                    "candidate_set_id": "cs_001",
                    "audio_segment_id": "a001",
                    "selected_clip_id": "clip_01",
                    "confidence": "high",
                    "fallback_used": False,
                    "candidates": [
                        {"rank": 1, "clip_id": "clip_01", "final_score": 0.9}
                    ],
                }
            ],
        }

        timeline, log = build_timeline(media, audio, clips, matching)

        item = timeline["items"][0]
        self.assertEqual(item["visual_items"][0]["timeline_start"], 0.0)
        self.assertEqual(item["visual_items"][-1]["timeline_end"], 10.0)
        self.assertTrue(item["needs_review"])
        self.assertTrue(
            any("reused ranked clips" in warning for warning in log["items"][0]["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
