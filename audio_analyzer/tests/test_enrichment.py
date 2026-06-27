from __future__ import annotations

import re
import unittest

from audio_analyzer.enrichment import ALLOWED_SEGMENT_TYPES, enrich_segment
from audio_analyzer.models import ASRChunk, AudioSegment
from audio_analyzer.segmentation import create_segments


def make_segment(
    text: str = "Đây là khu vực trưng bày hiện vật.",
    *,
    start: float = 0.0,
    end: float = 4.0,
    confidence: float | None = 0.9,
    timestamp_estimated: bool = False,
) -> AudioSegment:
    return AudioSegment(
        segment_id="a001",
        start=start,
        end=end,
        duration=end - start,
        text=text,
        confidence=confidence,
        timestamp_estimated=timestamp_estimated,
    )


def words(text: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[^\W\d_]+", text)}


class EnrichmentTests(unittest.TestCase):
    def test_query_is_not_empty_and_adds_no_words(self) -> None:
        segment = make_segment("Đây là khu vực trưng bày nhiều hiện vật cổ.")

        enriched = enrich_segment(segment)

        self.assertTrue(enriched.query)
        self.assertLessEqual(words(enriched.query), words(segment.text))

    def test_keywords_add_no_words_outside_transcript(self) -> None:
        segment = make_segment("Khách tham quan khám phá khu trưng bày hiện vật.")

        enriched = enrich_segment(segment)

        transcript_words = words(segment.text)
        self.assertTrue(all(words(keyword) <= transcript_words for keyword in enriched.keywords))

    def test_translated_query_is_not_generated(self) -> None:
        enriched = enrich_segment(make_segment())

        self.assertIsNone(enriched.translated_query)

    def test_segment_type_is_always_allowed(self) -> None:
        texts = [
            "Đây là khu vực cổng chính.",
            "Khách tham quan khám phá khu trưng bày.",
            "Sau đó đoàn di chuyển sang khu tiếp theo.",
            "Chuyến đi để lại kỷ niệm đáng nhớ.",
            "Mèo xanh bàn ghế.",
        ]

        for text in texts:
            with self.subTest(text=text):
                self.assertIn(enrich_segment(make_segment(text)).segment_type, ALLOWED_SEGMENT_TYPES)

    def test_null_confidence_is_not_treated_as_low_confidence(self) -> None:
        enriched = enrich_segment(make_segment(confidence=None))

        self.assertEqual(enriched.segment_type, "description")
        self.assertFalse(enriched.needs_review)

    def test_confidence_below_threshold_needs_review(self) -> None:
        enriched = enrich_segment(make_segment(confidence=0.64))

        self.assertTrue(enriched.needs_review)

    def test_estimated_timestamp_needs_review(self) -> None:
        enriched = enrich_segment(make_segment(timestamp_estimated=True))

        self.assertTrue(enriched.needs_review)

    def test_punctuation_split_marks_real_segments_for_review(self) -> None:
        segments = create_segments(
            [ASRChunk(0.0, 12.0, "Đây là cổng chính. Bên trong là khu trưng bày.", 0.9)]
        )

        self.assertTrue(all(segment.timestamp_estimated for segment in segments))
        self.assertTrue(all(enrich_segment(segment).needs_review for segment in segments))

    def test_short_and_long_segments_need_review(self) -> None:
        cases = [
            make_segment(start=0.0, end=1.5),
            make_segment(start=0.0, end=9.0),
        ]

        for segment in cases:
            with self.subTest(duration=segment.duration):
                self.assertTrue(enrich_segment(segment).needs_review)

    def test_long_chunk_without_safe_boundary_is_kept_and_needs_review(self) -> None:
        text = "khách tham quan tiếp tục di chuyển qua khu vực trải nghiệm tiếp theo"
        segments = create_segments([ASRChunk(0.0, 10.0, text, None)])

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text, text)
        self.assertFalse(segments[0].timestamp_estimated)
        self.assertTrue(enrich_segment(segments[0]).needs_review)

    def test_abstract_and_unknown_segments_need_review(self) -> None:
        cases = [
            ("Chuyến đi để lại nhiều kỷ niệm đáng nhớ.", "abstract"),
            ("Mèo xanh bàn ghế.", "unknown"),
        ]

        for text, expected_type in cases:
            with self.subTest(text=text):
                enriched = enrich_segment(make_segment(text))
                self.assertEqual(enriched.segment_type, expected_type)
                self.assertTrue(enriched.needs_review)

    def test_non_visual_discourse_is_classified_for_downstream_fallback(self) -> None:
        cases = [
            ("Một trận đấu CP diễn ra như thế này.", "transition"),
            ("Đây là phần cân não nhất.", "abstract"),
            ("Vậy tại sao CP lại quan trọng với bạn?", "abstract"),
            ("Hẹn gặp lại ở phần sau.", "transition"),
        ]

        for text, expected_type in cases:
            with self.subTest(text=text):
                enriched = enrich_segment(make_segment(text))
                self.assertEqual(enriched.segment_type, expected_type)
                self.assertIn("generic_query", enriched.review_reasons)

    def test_leading_transition_does_not_hide_visual_action(self) -> None:
        enriched = enrich_segment(
            make_segment(
                "Tiếp theo, bạn thiết kế thuật toán mà máy tính sẽ thực thi."
            )
        )

        self.assertEqual(enriched.segment_type, "action")

    def test_uncertain_proper_name_or_place_needs_review(self) -> None:
        enriched = enrich_segment(
            make_segment("Đoàn tham quan di chuyển đến thành phố Huế.")
        )

        self.assertTrue(enriched.needs_review)

    def test_protected_technical_terms_are_not_uncertain_proper_names(self) -> None:
        enriched = enrich_segment(make_segment("Kết quả là Accepted và đủ nhanh."))

        self.assertNotIn("uncertain_proper_name_or_place", enriched.review_reasons)

    def test_technical_explanation_is_classified_as_description(self) -> None:
        enriched = enrich_segment(
            make_segment("Dữ liệu đầu vào được xử lý bằng thuật toán.")
        )

        self.assertEqual(enriched.segment_type, "description")

    def test_technical_acronym_inside_cta_is_not_a_proper_name(self) -> None:
        enriched = enrich_segment(
            make_segment("Nếu bạn muốn học CP, hãy follow kênh và bật thông báo.")
        )

        self.assertNotIn("uncertain_proper_name_or_place", enriched.review_reasons)

    def test_bilingual_technical_description_is_not_unknown(self) -> None:
        texts = [
            "Competitive Programming là một bộ môn thi đấu.",
            "Lập trình thông thường tạo ra sản phẩm phần mềm.",
            "Olympic Tin Học có vòng phỏng vấn kỹ thuật.",
        ]

        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(
                    enrich_segment(make_segment(text)).segment_type,
                    "description",
                )

    def test_same_input_produces_same_enrichment(self) -> None:
        segment = make_segment("Sau đó đoàn di chuyển sang khu trải nghiệm.")

        self.assertEqual(enrich_segment(segment), enrich_segment(segment))


if __name__ == "__main__":
    unittest.main()
