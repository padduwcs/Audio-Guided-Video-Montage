from __future__ import annotations

import unittest
from pathlib import Path

from audio_analyzer.models import ASRChunk, AudioSegment
from audio_analyzer.segmentation import (
    SegmentationConfig,
    cover_audio_duration,
    create_segments,
    create_segments_with_report,
)
from audio_analyzer.tests.fakes import FakeASRBackend
from audio_analyzer.transcript import clean_transcript_chunks


class SegmentationTests(unittest.TestCase):
    def test_normal_chunk_creates_one_segment(self) -> None:
        segments = create_segments(
            [ASRChunk(0.0, 4.0, "Đây là khu vực cổng chính.", 0.9)]
        )

        self.assertEqual(
            segments,
            [
                AudioSegment(
                    segment_id="a001",
                    start=0.0,
                    end=4.0,
                    duration=4.0,
                    text="Đây là khu vực cổng chính.",
                    confidence=0.9,
                )
            ],
        )

    def test_short_chunk_is_merged_with_adjacent_chunk(self) -> None:
        chunks = [
            ASRChunk(0.0, 1.0, "Sau đó,", 0.8),
            ASRChunk(1.2, 4.5, "đoàn đi vào khu trưng bày.", 0.9),
        ]

        segments = create_segments(chunks)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].start, 0.0)
        self.assertEqual(segments[0].end, 4.5)
        self.assertEqual(segments[0].text, "Sau đó, đoàn đi vào khu trưng bày.")

    def test_sentence_is_reassembled_across_normal_length_asr_chunks(self) -> None:
        chunks = [
            ASRChunk(0.0, 4.0, "Competitive Programming dùng code để giải", None),
            ASRChunk(4.0, 7.0, "các bài toán trong thời gian giới hạn.", None),
        ]

        result = create_segments_with_report(chunks)

        self.assertEqual(len(result.segments), 1)
        self.assertEqual(
            result.segments[0].text,
            "Competitive Programming dùng code để giải các bài toán trong thời gian giới hạn.",
        )
        self.assertTrue(
            any(
                event.get("reason") == "sentence_continuation"
                for event in result.events
            )
        )

    def test_complete_sentence_is_not_merged_with_next_sentence(self) -> None:
        chunks = [
            ASRChunk(0.0, 3.0, "Câu thứ nhất đã hoàn chỉnh.", None),
            ASRChunk(3.0, 6.0, "Câu thứ hai cũng hoàn chỉnh.", None),
        ]

        segments = create_segments(chunks)

        self.assertEqual(len(segments), 2)

    def test_short_complete_sentence_stays_separate(self) -> None:
        chunks = [
            ASRChunk(0.0, 1.0, "Xin chào.", None),
            ASRChunk(1.0, 4.0, "Đây là một câu hoàn chỉnh khác.", None),
        ]

        segments = create_segments(chunks)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "Xin chào.")

    def test_incomplete_chunks_are_not_merged_across_large_silence(self) -> None:
        chunks = [
            ASRChunk(0.0, 3.0, "Nội dung thứ nhất chưa kết thúc", None),
            ASRChunk(4.0, 7.0, "nội dung tiếp theo.", None),
        ]

        result = create_segments_with_report(
            chunks,
            SegmentationConfig(max_merge_gap=0.75),
        )

        self.assertEqual(len(result.segments), 2)
        self.assertTrue(
            any(
                event.get("reason") == "large_gap_before_sentence_completion"
                for event in result.events
            )
        )

    def test_long_complete_sentence_is_kept_for_review_instead_of_word_split(self) -> None:
        chunks = [
            ASRChunk(0.0, 5.0, "Đây là phần đầu của một câu dài", 0.8),
            ASRChunk(5.1, 11.0, "và đây là phần cuối của cùng câu.", 0.7),
        ]

        result = create_segments_with_report(chunks)

        self.assertEqual(len(result.segments), 1)
        self.assertGreater(result.segments[0].duration, 8.0)
        self.assertEqual(result.segments[0].confidence, 0.7)
        self.assertFalse(result.segments[0].timestamp_estimated)
        self.assertTrue(
            any(
                event["type"] == "retained_long_no_safe_boundary"
                for event in result.events
            )
        )

    def test_reassembled_multiple_sentences_split_only_at_full_stops(self) -> None:
        chunks = [
            ASRChunk(0.0, 4.0, "Câu thứ nhất còn tiếp", None),
            ASRChunk(4.0, 8.0, "và kết thúc tại đây. Câu thứ hai", None),
            ASRChunk(8.0, 12.0, "cũng kết thúc tại đây.", None),
        ]

        segments = create_segments(chunks)

        self.assertEqual(len(segments), 2)
        self.assertEqual(
            [segment.text for segment in segments],
            [
                "Câu thứ nhất còn tiếp và kết thúc tại đây.",
                "Câu thứ hai cũng kết thúc tại đây.",
            ],
        )
        self.assertTrue(all(segment.timestamp_estimated for segment in segments))

    def test_long_chunk_is_split_only_at_punctuation(self) -> None:
        text = (
            "Đây là khu vực cổng chính của khu tham quan. "
            "Bên trong là khu trưng bày nhiều hiện vật."
        )

        segments = create_segments([ASRChunk(0.0, 12.0, text, None)])

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "Đây là khu vực cổng chính của khu tham quan.")
        self.assertEqual(segments[1].text, "Bên trong là khu trưng bày nhiều hiện vật.")
        self.assertEqual(" ".join(segment.text for segment in segments), text)
        self.assertTrue(all(segment.timestamp_estimated for segment in segments))
        self.assertTrue(all(segment.confidence is None for segment in segments))

    def test_long_chunk_without_punctuation_is_not_split_into_words(self) -> None:
        text = "khách tham quan tiếp tục di chuyển qua khu vực trải nghiệm tiếp theo"

        segments = create_segments([ASRChunk(0.0, 10.0, text, None)])

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text, text)
        self.assertFalse(segments[0].timestamp_estimated)

    def test_split_preserves_source_confidence(self) -> None:
        text = "Đây là khu vực cổng chính. Bên trong là khu trưng bày."

        segments = create_segments([ASRChunk(0.0, 12.0, text, 0.72)])

        self.assertEqual([segment.confidence for segment in segments], [0.72, 0.72])

    def test_timestamps_are_increasing_non_overlapping_and_duration_is_exact(self) -> None:
        chunks = [
            ASRChunk(0.0, 3.25, "Đoạn thứ nhất.", None),
            ASRChunk(3.5, 7.75, "Đoạn thứ hai.", None),
        ]

        segments = create_segments(chunks)

        self.assertLessEqual(segments[0].end, segments[1].start)
        for segment in segments:
            self.assertAlmostEqual(segment.duration, segment.end - segment.start)

    def test_ids_are_sequential(self) -> None:
        chunks = [
            ASRChunk(0.0, 2.5, "Một.", None),
            ASRChunk(3.5, 6.0, "Hai.", None),
            ASRChunk(7.0, 9.5, "Ba.", None),
        ]

        segments = create_segments(chunks)

        self.assertEqual([segment.segment_id for segment in segments], ["a001", "a002", "a003"])

    def test_empty_chunk_is_discarded_before_segmentation(self) -> None:
        chunks = [
            ASRChunk(0.0, 1.0, "  \n ", None),
            ASRChunk(1.0, 4.0, "Nội dung hợp lệ.", None),
        ]

        segments = create_segments(chunks)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text, "Nội dung hợp lệ.")

    def test_invalid_chunk_timestamp_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ASRChunk(start=2.0, end=1.0, text="Timestamp sai")

    def test_overlapping_and_out_of_order_chunks_are_rejected(self) -> None:
        invalid_inputs = [
            [ASRChunk(0.0, 3.0, "Một", None), ASRChunk(2.0, 4.0, "Hai", None)],
            [ASRChunk(3.0, 4.0, "Hai", None), ASRChunk(0.0, 2.0, "Một", None)],
        ]

        for chunks in invalid_inputs:
            with self.subTest(chunks=chunks):
                with self.assertRaises(ValueError):
                    create_segments(chunks)

    def test_same_fake_backend_input_produces_same_output(self) -> None:
        chunks = [
            ASRChunk(0.0, 1.0, "Sau đó,", None),
            ASRChunk(1.1, 4.0, "đoàn tiếp tục tham quan.", 0.75),
            ASRChunk(5.0, 8.0, "Đây là khu trải nghiệm.", 0.8),
        ]
        backend = FakeASRBackend(chunks)
        audio_path = Path("data/normalized/voiceover.wav")

        first = create_segments(clean_transcript_chunks(backend.transcribe(audio_path)))
        second = create_segments(clean_transcript_chunks(backend.transcribe(audio_path)))

        self.assertEqual(first, second)

    def test_audio_coverage_partitions_leading_internal_and_trailing_gaps(self) -> None:
        segments = [
            AudioSegment("a001", 1.0, 3.0, 2.0, "Một.", None),
            AudioSegment("a002", 5.0, 7.0, 2.0, "Hai.", None),
        ]

        result = cover_audio_duration(segments, audio_duration=10.0)

        self.assertEqual(result.segments[0].start, 0.0)
        self.assertEqual(result.segments[0].end, 4.0)
        self.assertEqual(result.segments[1].start, 4.0)
        self.assertEqual(result.segments[1].end, 10.0)
        self.assertTrue(result.events)

    def test_audio_coverage_rejects_overlapping_segments(self) -> None:
        segments = [
            AudioSegment("a001", 0.0, 3.0, 3.0, "Một.", None),
            AudioSegment("a002", 2.0, 4.0, 2.0, "Hai.", None),
        ]

        with self.assertRaisesRegex(ValueError, "must not overlap"):
            cover_audio_duration(segments, audio_duration=5.0)


if __name__ == "__main__":
    unittest.main()
