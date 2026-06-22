from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from audio_analyzer.asr import FasterWhisperBackend, FasterWhisperBackendError


class RecordingModel:
    def __init__(self, segments) -> None:
        self.segments = segments
        self.calls: list[tuple[str, dict]] = []

    def transcribe(self, audio_path: str, **options):
        self.calls.append((audio_path, options))
        return iter(self.segments), SimpleNamespace(language=options.get("language"))


class FasterWhisperBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.audio_path = Path(self.temporary_directory.name) / "dynamic-name.wav"
        self.audio_path.write_bytes(b"audio-placeholder")

    def test_maps_segments_without_converting_avg_logprob_to_confidence(self) -> None:
        model = RecordingModel(
            [
                SimpleNamespace(
                    start=0.0,
                    end=2.5,
                    text=" Xin chào Việt Nam. ",
                    avg_logprob=-0.12,
                )
            ]
        )
        factory_calls = []

        def factory(model_name: str, **kwargs):
            factory_calls.append((model_name, kwargs))
            return model

        backend = FasterWhisperBackend(
            model="base",
            language="vi",
            device="cpu",
            compute_type="int8",
            model_factory=factory,
        )

        chunks = backend.transcribe(self.audio_path)

        self.assertEqual(factory_calls, [("base", {"device": "cpu", "compute_type": "int8"})])
        self.assertEqual(
            model.calls,
            [(str(self.audio_path), {"language": "vi", "task": "transcribe"})],
        )
        self.assertEqual(chunks[0].start, 0.0)
        self.assertEqual(chunks[0].end, 2.5)
        self.assertEqual(chunks[0].text, " Xin chào Việt Nam. ")
        self.assertIsNone(chunks[0].confidence)

    def test_model_is_loaded_lazily_and_reused(self) -> None:
        model = RecordingModel([SimpleNamespace(start=0.0, end=1.0, text="Một")])
        load_count = 0

        def factory(*args, **kwargs):
            nonlocal load_count
            load_count += 1
            return model

        backend = FasterWhisperBackend(model_factory=factory)
        self.assertEqual(load_count, 0)

        backend.transcribe(self.audio_path)
        backend.transcribe(self.audio_path)

        self.assertEqual(load_count, 1)

    def test_auto_maps_language_to_none_and_enables_multilingual(self) -> None:
        model = RecordingModel([SimpleNamespace(start=0.0, end=1.0, text="Code switch")])
        backend = FasterWhisperBackend(
            language="auto",
            model_factory=lambda *args, **kwargs: model,
        )

        backend.transcribe(self.audio_path)

        self.assertEqual(
            model.calls,
            [
                (
                    str(self.audio_path),
                    {
                        "language": None,
                        "task": "transcribe",
                        "multilingual": True,
                    },
                )
            ],
        )

    def test_forced_english_is_passed_without_translation(self) -> None:
        model = RecordingModel([SimpleNamespace(start=0.0, end=1.0, text="Hash table")])
        backend = FasterWhisperBackend(
            language="en",
            model_factory=lambda *args, **kwargs: model,
        )

        backend.transcribe(self.audio_path)

        self.assertEqual(
            model.calls,
            [(str(self.audio_path), {"language": "en", "task": "transcribe"})],
        )

    def test_model_loading_error_is_clear(self) -> None:
        def failing_factory(*args, **kwargs):
            raise RuntimeError("model unavailable")

        backend = FasterWhisperBackend(model_factory=failing_factory)

        with self.assertRaisesRegex(FasterWhisperBackendError, "failed to load.*model unavailable"):
            backend.transcribe(self.audio_path)

    def test_decode_or_inference_error_is_clear(self) -> None:
        class FailingModel:
            def transcribe(self, audio_path: str, **options):
                raise RuntimeError("cannot decode audio")

        backend = FasterWhisperBackend(model_factory=lambda *args, **kwargs: FailingModel())

        with self.assertRaisesRegex(
            FasterWhisperBackendError, "failed to decode or transcribe.*cannot decode audio"
        ):
            backend.transcribe(self.audio_path)

    def test_lazy_segment_iteration_error_is_clear(self) -> None:
        def failing_segments():
            raise RuntimeError("inference interrupted")
            yield

        model = RecordingModel([])
        model.segments = failing_segments()
        backend = FasterWhisperBackend(model_factory=lambda *args, **kwargs: model)

        with self.assertRaisesRegex(
            FasterWhisperBackendError, "failed to decode or transcribe.*inference interrupted"
        ):
            backend.transcribe(self.audio_path)

    def test_missing_audio_is_rejected_before_model_load(self) -> None:
        backend = FasterWhisperBackend(
            model_factory=lambda *args, **kwargs: self.fail("model must not load")
        )

        with self.assertRaisesRegex(FasterWhisperBackendError, "audio file does not exist"):
            backend.transcribe(self.audio_path.with_name("missing.wav"))


if __name__ == "__main__":
    unittest.main()
