from __future__ import annotations

import unittest

from audio_analyzer.models import ASRChunk
from audio_analyzer.timestamps import align_chunks_to_audio_duration


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
        chunk = ASRChunk(0.0, 7.0, "Nội dung", 0.8)

        result = align_chunks_to_audio_duration([chunk], audio_duration=5.0)

        self.assertEqual(result.chunks[0].end, 5.0)
        self.assertEqual(result.chunks[0].confidence, 0.8)

    def test_common_whisper_end_overrun_is_clamped(self) -> None:
        chunk = ASRChunk(3.0, 6.014, "Nội dung", None)

        result = align_chunks_to_audio_duration([chunk], audio_duration=5.0)

        self.assertEqual(result.chunks[0].end, 5.0)
        self.assertTrue(result.chunks[0].timestamp_estimated)
        self.assertAlmostEqual(result.adjustments[0]["overrun_seconds"], 1.014)

    def test_large_end_overrun_is_clamped(self) -> None:
        chunk = ASRChunk(0.0, 7.001, "Nội dung", None)

        result = align_chunks_to_audio_duration([chunk], audio_duration=5.0)

        self.assertEqual(result.chunks[0].end, 5.0)
        self.assertAlmostEqual(result.adjustments[0]["overrun_seconds"], 2.001)

    def test_chunk_fully_outside_audio_is_discarded(self) -> None:
        chunk = ASRChunk(5.0, 8.0, "Nội dung", None)

        result = align_chunks_to_audio_duration([chunk], audio_duration=5.0)

        self.assertEqual(result.chunks, ())
        self.assertEqual(
            result.adjustments[0]["reason"],
            "chunk_outside_audio_discarded",
        )

    def test_overlapping_chunks_are_split_at_overlap_midpoint(self) -> None:
        chunks = [
            ASRChunk(0.0, 5.0, "Một", None),
            ASRChunk(4.0, 8.0, "Hai", None),
        ]

        result = align_chunks_to_audio_duration(chunks, audio_duration=10.0)

        self.assertEqual(result.chunks[0].end, 4.5)
        self.assertEqual(result.chunks[1].start, 4.5)
        self.assertTrue(result.chunks[0].timestamp_estimated)
        self.assertTrue(result.chunks[1].timestamp_estimated)
        self.assertEqual(
            result.adjustments[0]["reason"],
            "overlap_split_at_midpoint",
        )

    def test_nested_chunks_are_partitioned_without_dropping_text(self) -> None:
        chunks = [
            ASRChunk(0.0, 10.0, "Một", None),
            ASRChunk(1.0, 2.0, "Hai", None),
        ]

        result = align_chunks_to_audio_duration(chunks, audio_duration=10.0)

        self.assertEqual([chunk.text for chunk in result.chunks], ["Một", "Hai"])
        self.assertEqual(result.chunks[0].end, result.chunks[1].start)

    def test_out_of_order_chunks_are_sorted(self) -> None:
        chunks = [
            ASRChunk(3.0, 4.0, "Hai", None),
            ASRChunk(0.0, 2.0, "Một", None),
        ]

        result = align_chunks_to_audio_duration(chunks, audio_duration=5.0)

        self.assertEqual([chunk.text for chunk in result.chunks], ["Một", "Hai"])
        self.assertEqual(
            result.adjustments[0]["reason"],
            "chunks_reordered_by_timestamp",
        )


if __name__ == "__main__":
    unittest.main()
