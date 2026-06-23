from __future__ import annotations

import re
import unittest

from audio_analyzer.bilingual_keywords import BilingualKeywordExtractor
from audio_analyzer.bilingual_query import BilingualQueryBuilder


class BilingualKeywordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = BilingualKeywordExtractor()
        self.query_builder = BilingualQueryBuilder()

    def assert_query_uses_only_transcript_words(self, query: str, text: str) -> None:
        words = lambda value: {
            word.casefold() for word in re.findall(r"[^\W\d_]+", value)
        }
        self.assertLessEqual(words(query), words(text))

    def test_preserves_english_multiword_terms_in_vietnamese_text(self) -> None:
        text = (
            "Kết quả có thể là Wrong Answer khi lời giải sai hoặc "
            "Time Limit Exceeded khi chạy quá chậm."
        )

        result = self.extractor.extract(text)

        self.assertIn("Wrong Answer", result.keywords)
        self.assertIn("Time Limit Exceeded", result.keywords)

    def test_preserves_acronyms_and_title_terms(self) -> None:
        text = "Competitive Programming hay CP được sử dụng trong kỳ thi IOI."

        result = self.extractor.extract(text)

        self.assertIn("Competitive Programming", result.keywords)
        self.assertIn("CP", result.keywords)
        self.assertIn("IOI", result.keywords)

    def test_selects_important_phrase_at_end_instead_of_first_five_words(self) -> None:
        text = (
            "Sau đó, bạn cốt lời giải và nột bài lên hệ thống chấm tự động, "
            "gọi là Online Judge."
        )

        result = self.extractor.extract(text)

        self.assertIn("Online Judge", result.keywords)
        self.assertIn("hệ thống chấm tự động", result.keywords)

    def test_keywords_are_exact_transcript_spans(self) -> None:
        text = "CP là bệ phóng đến Olympic Tin Học và phỏng vấn kỹ thuật."

        result = self.extractor.extract(text)

        self.assertTrue(all(keyword in text for keyword in result.keywords))

    def test_call_to_action_can_have_empty_keywords(self) -> None:
        text = "Hãy follow kênh và bật thông báo để không bỏ lỡ video tiếp theo."

        result = self.extractor.extract(text)

        self.assertEqual(result.keywords, ())
        self.assertTrue(result.is_generic)

    def test_query_preserves_complete_meaning_and_technical_terms(self) -> None:
        text = (
            "Kết quả trả về Wrong Answer khi lời giải sai hoặc "
            "Time Limit Exceeded khi chương trình quá chậm."
        )
        extraction = self.extractor.extract(text)

        query, is_generic = self.query_builder.build(text, extraction)

        self.assertIn("Wrong Answer", query)
        self.assertIn("Time Limit Exceeded", query)
        self.assert_query_uses_only_transcript_words(query, text)
        self.assertFalse(is_generic)

    def test_query_uses_positive_side_of_explicit_contrast(self) -> None:
        text = "Trong CP, vũ khí không phải bóng hay vợt mà là trí tuệ và thuật toán."

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("trí tuệ", query)
        self.assertIn("thuật toán", query)
        self.assertNotIn("bóng", query)
        self.assertNotIn("vợt", query)
        self.assert_query_uses_only_transcript_words(query, text)

    def test_query_shortens_one_sentence_using_a_contiguous_span(self) -> None:
        text = (
            "Tiếp theo, bạn thiết kế thuật toán, tức là vạch ra từng bước "
            "logic mà máy tính sẽ thực thi."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertNotEqual(query, text)
        self.assertIn("thiết kế thuật toán", query)
        self.assert_query_uses_only_transcript_words(query, text)

    def test_semantic_query_excludes_negated_and_metaphorical_terms(self) -> None:
        text = (
            "CP là một môn thể thao trí tuệ, nhưng vũ khí không phải bóng, "
            "mà là thuật toán."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("CP", query)
        self.assertIn("thuật toán", query)
        self.assertNotIn("vũ khí", query)
        self.assertNotIn("bóng", query)
        self.assert_query_uses_only_transcript_words(query, text)

    def test_semantic_query_excludes_negated_action(self) -> None:
        text = (
            "CP không xây dựng sản phẩm, bạn giải toán dưới áp lực đồng hồ."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("CP", query)
        self.assertIn("giải toán", query)
        self.assertNotIn("xây dựng", query)

    def test_abstract_query_prioritizes_retrievable_concepts(self) -> None:
        text = (
            "Mỗi bài toán là một lần não bộ được rèn giũa, "
            "phản xạ logic nhanh hơn, tư duy hệ thống sâu hơn."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("phản xạ logic nhanh hơn", query)
        self.assertIn("tư duy hệ thống sâu hơn", query)
        self.assertNotIn("rèn giũa", query)

    def test_short_query_keeps_topic_and_description(self) -> None:
        text = "CP là một bộ môn thi đấu."

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("CP", query)
        self.assertIn("bộ môn thi đấu", query)
        self.assert_query_uses_only_transcript_words(query, text)

    def test_query_rejects_alias_only_span(self) -> None:
        text = (
            "Competitive Programming, hay CP, là bộ môn thi đấu bằng cách "
            "giải bài toán logic."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertNotEqual(query, "Competitive Programming, hay CP")

    def test_query_keeps_context_for_named_system(self) -> None:
        text = (
            "Bạn nộp lời giải lên hệ thống chấm tự động, gọi là Online Judge."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("hệ thống chấm tự động", query)
        self.assertIn("Online Judge", query)

    def test_query_keeps_related_error_statuses_together(self) -> None:
        text = (
            "Kết quả có thể là Accepted, hoặc Wrong Answer, lời giải sai, "
            "hoặc Time Limit Exceeded, chương trình quá chậm."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("Wrong Answer", query)
        self.assertIn("Time Limit Exceeded", query)

    def test_query_only_removes_unambiguous_leading_filler(self) -> None:
        text = "Ừm, dữ liệu đầu vào quyết định kết quả của thuật toán."

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertEqual(query, "dữ liệu đầu vào quyết định kết quả của thuật toán.")

    def test_query_selects_one_complete_content_clause(self) -> None:
        text = (
            "Tìm ra quy luật ẩn bên dưới con số. "
            "Tiếp theo, bạn thiết kế thuật toán."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertEqual(query, "bạn thiết kế thuật toán.")

    def test_query_does_not_isolate_dependent_contrast_clause(self) -> None:
        text = (
            "Lập trình thông thường tạo ra sản phẩm, app, web, phần mềm. "
            "Còn CP thì khác."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertEqual(
            query,
            "Lập trình thông thường tạo ra sản phẩm, app, web, phần mềm.",
        )

    def test_vague_transition_uses_source_fallback_and_is_generic(self) -> None:
        text = "Một trận đấu CP diễn ra như thế này."
        extraction = self.extractor.extract(text)

        decision = self.query_builder.build_many_detailed([text], [extraction])[0]

        self.assertEqual(decision.query, text)
        self.assertTrue(decision.is_generic)
        self.assertEqual(decision.fallback_reason, "no_visual_query")
        self.assertEqual(decision.visual_suitability, 0.0)

    def test_outro_is_not_treated_as_a_visual_query(self) -> None:
        text = "Hẹn gặp lại ở phần sau."
        extraction = self.extractor.extract(text)

        decision = self.query_builder.build_many_detailed([text], [extraction])[0]

        self.assertTrue(decision.is_generic)
        self.assertEqual(decision.fallback_reason, "no_visual_query")

    def test_long_technical_query_keeps_multiple_retrieval_intents(self) -> None:
        text = (
            "CP dẫn đến kỳ thi học sinh giỏi quốc gia, Olympic Tin Học Quốc tế "
            "IOI, và vòng phỏng vấn kỹ thuật tại công ty công nghệ."
        )

        query, _ = self.query_builder.build(text, self.extractor.extract(text))

        self.assertIn("IOI", query)
        self.assertIn("vòng phỏng vấn kỹ thuật", query)
        self.assert_query_uses_only_transcript_words(query, text)

    def test_short_factual_sentence_is_not_over_compressed(self) -> None:
        text = "Lập trình thông thường tạo ra sản phẩm, app, web, phần mềm."

        decision = self.query_builder.build_many_detailed(
            [text],
            [self.extractor.extract(text)],
        )[0]

        self.assertEqual(decision.query, text)
        self.assertEqual(decision.fallback_reason, "source_already_concise")

    def test_invalid_minimum_source_words_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            BilingualQueryBuilder(min_source_words_for_reduction=0)

    def test_keywords_keep_complete_vietnamese_phrase(self) -> None:
        result = self.extractor.extract(
            "Hệ thống nhận dữ liệu đầu vào và tạo ra kết quả đầu ra cụ thể."
        )

        self.assertIn("dữ liệu đầu vào", result.keywords)

    def test_keywords_keep_single_english_status(self) -> None:
        result = self.extractor.extract(
            "Nếu cốt đúng và đủ nhanh, kết quả trả về là Accepted ngay lập tức."
        )

        self.assertIn("Accepted", result.keywords)

    def test_keywords_keep_complete_mixed_case_proper_name(self) -> None:
        result = self.extractor.extract(
            "CP là bệ phóng đến Olympic Tin Học Quốc tế và kỳ thi IOI."
        )

        self.assertIn("Olympic Tin Học Quốc tế", result.keywords)

    def test_keywords_keep_long_complete_noun_phrases(self) -> None:
        texts = [
            "CP dẫn đến kỳ thi học sinh giỏi quốc gia.",
            "Đây là tư duy hệ thống sâu hơn.",
            "Ứng viên phỏng vấn tại công ty công nghệ lớn nhất thế giới.",
        ]

        first, second, third = self.extractor.extract_many(texts)

        self.assertIn("kỳ thi học sinh giỏi quốc gia", first.keywords)
        self.assertIn("tư duy hệ thống sâu hơn", second.keywords)
        self.assertIn("công ty công nghệ lớn nhất thế giới", third.keywords)

    def test_call_to_action_is_handled_per_sentence(self) -> None:
        text = "Đừng bỏ lỡ video tiếp theo. Tại sao CP lại quan trọng?"

        result = self.extractor.extract(text)

        self.assertIn("CP", result.keywords)
        self.assertFalse(result.is_generic)

    def test_generic_single_words_are_not_keywords(self) -> None:
        result = self.extractor.extract(
            "Bước đầu tiên, hệ thống chạy hàng chục bộ test trong vài giây."
        )

        self.assertNotIn("Bước", result.keywords)
        self.assertNotIn("đầu tiên", result.keywords)
        self.assertNotIn("hàng chục", result.keywords)
        self.assertNotIn("vài giây", result.keywords)
        self.assertFalse(
            any(keyword.casefold().startswith("bước đầu") for keyword in result.keywords)
        )

    def test_procedural_keyword_keeps_its_meaningful_start(self) -> None:
        result = self.extractor.extract(
            "Đọc hiểu đề và xác định bài toán thuộc dạng gì."
        )

        self.assertIn("xác định bài toán thuộc dạng gì", result.keywords)

    def test_keywords_exclude_unsafe_fragment_that_loses_negation(self) -> None:
        result = self.extractor.extract(
            "Vũ khí không phải bóng hay vợt mà là trí tuệ và thuật toán."
        )

        self.assertNotIn("phải bóng", result.keywords)

    def test_same_corpus_produces_same_results(self) -> None:
        texts = [
            "Competitive Programming hay CP là một bộ môn thi đấu.",
            "Hệ thống chấm tự động được gọi là Online Judge.",
        ]

        self.assertEqual(self.extractor.extract_many(texts), self.extractor.extract_many(texts))


if __name__ == "__main__":
    unittest.main()
