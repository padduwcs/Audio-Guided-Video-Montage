from __future__ import annotations

import unittest
from pathlib import Path

from audio_analyzer.models import ASRChunk
from audio_analyzer.tests.fakes import FakeASRBackend


class ASRChunkTests(unittest.TestCase):
    def test_valid_chunk(self) -> None:
        chunk = ASRChunk(start=0, end=1.5, text="Xin chào", confidence=0.92)

        self.assertEqual(chunk.start, 0.0)
        self.assertEqual(chunk.end, 1.5)
        self.assertEqual(chunk.text, "Xin chào")
        self.assertEqual(chunk.confidence, 0.92)

    def test_null_confidence_is_preserved(self) -> None:
        chunk = ASRChunk(start=0.0, end=1.0, text="Nội dung", confidence=None)

        self.assertIsNone(chunk.confidence)

    def test_invalid_timestamps_are_rejected(self) -> None:
        invalid_ranges = [(-0.1, 1.0), (1.0, 1.0), (2.0, 1.0)]

        for start, end in invalid_ranges:
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    ASRChunk(start=start, end=end, text="Nội dung")

    def test_fake_backend_returns_chunks_and_records_call(self) -> None:
        expected = ASRChunk(0.0, 1.0, "Đây là cổng chính.", None)
        backend = FakeASRBackend([expected])
        audio_path = Path("data/normalized/voiceover.wav")

        result = tuple(backend.transcribe(audio_path))

        self.assertEqual(result, (expected,))
        self.assertEqual(backend.calls, [audio_path])


if __name__ == "__main__":
    unittest.main()

