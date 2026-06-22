from __future__ import annotations

import unittest

from audio_analyzer.models import ASRChunk
from audio_analyzer.timestamps import (
    TimestampAlignmentError,
    align_chunks_to_audio_duration,
)


class TimestampAlignmentTests(unittest.TestCase):
    def test_chunk_within_duration_is_unchanged(self) -> None:
        chunk = ASRChunk(0.0, 4.0, "Nội dung", None)

        result = align_chunks_to_audio_duration([chunk], audio_duration=4.5)

        self.assertEqual(result.chunks, (chunk,))
        self.assertEqual(result.adjustments, ())

    def test_small_end_overrun_is_clamped_and_marked_estimated(self) -> None:
        chunk = ASRChunk(0.0, 5.24, "Nội dung", None)

        result = align_chunks_to_audio_duration([chunk], audio_duration=4.908)

        self.assertEqual(result.chunks[0].end, 4.908)
        self.assertTrue(result.chunks[0].timestamp_estimated)
        self.assertAlmostEqual(result.adjustments[0]["overrun_seconds"], 0.332)

    def test_overrun_at_tolerance_boundary_is_accepted(self) -> None:
        chunk = ASRChunk(0.0, 5.5, "Nội dung", 0.8)

        result = align_chunks_to_audio_duration([chunk], audio_duration=5.0)

        self.assertEqual(result.chunks[0].end, 5.0)
        self.assertEqual(result.chunks[0].confidence, 0.8)

    def test_large_end_overrun_is_rejected(self) -> None:
        chunk = ASRChunk(0.0, 5.6, "Nội dung", None)

        with self.assertRaisesRegex(TimestampAlignmentError, "maximum safe overrun"):
            align_chunks_to_audio_duration([chunk], audio_duration=5.0)


if __name__ == "__main__":
    unittest.main()
