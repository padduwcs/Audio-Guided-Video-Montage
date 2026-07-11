from __future__ import annotations

import unittest

from shared.timeline_contract import timeline_contract_errors


def valid_timeline() -> dict:
    return {
        "schema_version": "1.0",
        "project_id": "test",
        "audio_id": "audio_01",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "render_settings": {},
        "items": [
            {
                "segment_id": "a001",
                "audio_start": 0.0,
                "audio_end": 2.0,
                "duration": 2.0,
                "visual_items": [
                    {
                        "timeline_item_id": "t001_i01",
                        "source_path": "data/normalized/video.mp4",
                        "clip_start": 0.0,
                        "clip_end": 2.0,
                        "timeline_start": 0.0,
                        "timeline_end": 2.0,
                        "speed": 1.0,
                    }
                ],
            }
        ],
    }


class TimelineContractTests(unittest.TestCase):
    def test_complete_timeline_is_valid(self) -> None:
        self.assertEqual(
            timeline_contract_errors(valid_timeline(), audio_duration=2.0),
            [],
        )

    def test_audio_gap_is_rejected(self) -> None:
        timeline = valid_timeline()
        timeline["items"][0]["audio_start"] = 0.5

        errors = timeline_contract_errors(timeline, audio_duration=2.0)

        self.assertTrue(any("not contiguous" in error for error in errors))

    def test_partial_visual_coverage_is_rejected(self) -> None:
        timeline = valid_timeline()
        timeline["items"][0]["visual_items"][0]["timeline_end"] = 1.5

        errors = timeline_contract_errors(timeline, audio_duration=2.0)

        self.assertTrue(any("do not cover" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
