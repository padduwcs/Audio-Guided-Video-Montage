from __future__ import annotations

import unittest

from audio_analyzer.models import ASRChunk
from audio_analyzer.transcript import clean_transcript_chunks, normalize_whitespace


class TranscriptCleaningTests(unittest.TestCase):
    def test_empty_and_whitespace_only_chunks_are_removed(self) -> None:
        chunks = [
            ASRChunk(0.0, 1.0, "", None),
            ASRChunk(1.0, 2.0, " \t\n ", 0.5),
            ASRChunk(2.0, 3.0, "Có nội dung", 0.8),
        ]

        result = clean_transcript_chunks(chunks)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Có nội dung")

    def test_extra_whitespace_is_normalized(self) -> None:
        text = "  Đây   là\n khu vực\t cổng chính.  "

        self.assertEqual(
            normalize_whitespace(text),
            "Đây là khu vực cổng chính.",
        )

    def test_vietnamese_content_is_preserved(self) -> None:
        original = "  Khách tham quan di chuyển sang khu trải nghiệm tiếp theo.  "
        chunk = ASRChunk(3.25, 7.5, original, None)

        result = clean_transcript_chunks([chunk])

        self.assertEqual(
            result[0].text,
            "Khách tham quan di chuyển sang khu trải nghiệm tiếp theo.",
        )
        self.assertEqual(result[0].start, 3.25)
        self.assertEqual(result[0].end, 7.5)
        self.assertIsNone(result[0].confidence)

    def test_cleanup_does_not_invent_confidence(self) -> None:
        chunk = ASRChunk(0.0, 1.0, "  Nội dung  ", None)

        result = clean_transcript_chunks([chunk])

        self.assertIsNone(result[0].confidence)


if __name__ == "__main__":
    unittest.main()
