from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from audio_analyzer.models import ASRChunk
from audio_analyzer.pipeline import PipelineError, run_pipeline
from audio_analyzer.query_reranker import QueryReranker, QueryRerankerError
from audio_analyzer.tests.fakes import FakeASRBackend


EXPECTED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "project_id",
    "audio_id",
    "language",
    "created_at",
    "items",
}
EXPECTED_ITEM_FIELDS = {
    "segment_id",
    "start",
    "end",
    "duration",
    "text",
    "query",
    "translated_query",
    "keywords",
    "segment_type",
    "asr_confidence",
    "needs_review",
}


class FailingQueryReranker(QueryReranker):
    @property
    def backend_name(self) -> str:
        return "failing-reranker"

    @property
    def model_name(self) -> str:
        return "unavailable-model"

    def select_many(self, source_texts, candidate_groups):
        raise QueryRerankerError("simulated query model failure")


class PipelineIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.output_dir = self.root / "data" / "intermediate"
        self.metadata_path = self.output_dir / "media_metadata.json"
        self.audio_path = self.root / "data" / "normalized" / "voiceover.wav"
        self.output_dir.mkdir(parents=True)
        self.audio_path.parent.mkdir(parents=True)
        self.audio_path.write_bytes(b"test-audio-placeholder")
        self.fixed_time = datetime(2026, 6, 21, 8, 30, tzinfo=timezone.utc)

    def write_metadata(self, status: str = "ready", duration: float = 14.0) -> None:
        document = {
            "schema_version": "1.0",
            "project_id": "integration_test",
            "audio": {
                "audio_id": "audio_test",
                "normalized_path": "data/normalized/voiceover.wav",
                "duration": duration,
                "status": status,
            },
        }
        self.metadata_path.write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )

    def backend_with_merge_split_and_review(self) -> FakeASRBackend:
        return FakeASRBackend(
            [
                ASRChunk(0.0, 1.0, "Sau đó,", 0.9),
                ASRChunk(1.1, 4.0, "đoàn đi vào khu trưng bày.", 0.6),
                ASRChunk(
                    4.5,
                    14.0,
                    "Đây là khu vực cổng chính. Bên trong là khu trưng bày hiện vật.",
                    0.9,
                ),
            ],
            backend_name="fake-asr",
            model_name="fixed-fixture",
        )

    def run_pipeline_case(
        self,
        backend: FakeASRBackend,
        *,
        overwrite: bool = False,
        query_reranker: QueryReranker | None = None,
    ):
        return run_pipeline(
            media_metadata_path=self.metadata_path,
            output_dir=self.output_dir,
            asr_backend=backend,
            overwrite=overwrite,
            query_reranker=query_reranker,
            project_root=self.root,
            clock=lambda: self.fixed_time,
        )

    def read_json(self, name: str) -> dict:
        return json.loads((self.output_dir / name).read_text(encoding="utf-8"))

    def test_ready_pipeline_writes_parseable_contract_output(self) -> None:
        self.write_metadata()

        result = self.run_pipeline_case(self.backend_with_merge_split_and_review())
        output = self.read_json("audio_segments.json")

        self.assertEqual(result.segment_count, len(output["items"]))
        self.assertEqual(set(output), EXPECTED_TOP_LEVEL_FIELDS)
        self.assertEqual(output["schema_version"], "1.0")
        self.assertEqual(output["project_id"], "integration_test")
        self.assertEqual(output["audio_id"], "audio_test")
        self.assertEqual(output["language"], "vi")
        datetime.fromisoformat(output["created_at"].replace("Z", "+00:00"))
        self.assertTrue(output["items"])
        self.assertTrue(all(set(item) == EXPECTED_ITEM_FIELDS for item in output["items"]))

    def test_output_segments_do_not_overlap_and_have_exact_duration(self) -> None:
        self.write_metadata()
        self.run_pipeline_case(self.backend_with_merge_split_and_review())
        items = self.read_json("audio_segments.json")["items"]

        for previous, current in zip(items, items[1:]):
            self.assertLessEqual(previous["end"], current["start"])
        for item in items:
            self.assertAlmostEqual(item["duration"], item["end"] - item["start"])

    def test_output_excludes_internal_fields_and_translation(self) -> None:
        self.write_metadata()
        self.run_pipeline_case(self.backend_with_merge_split_and_review())
        items = self.read_json("audio_segments.json")["items"]

        for item in items:
            self.assertNotIn("timestamp_estimated", item)
            self.assertNotIn("review_reasons", item)
            self.assertNotIn("confidence", item)
            self.assertIsNone(item["translated_query"])

    def test_analysis_log_contains_backend_raw_chunks_events_and_review_reasons(self) -> None:
        self.write_metadata()
        self.run_pipeline_case(self.backend_with_merge_split_and_review())
        log = self.read_json("audio_analysis_log.json")

        self.assertEqual(log["status"], "success")
        self.assertEqual(log["asr"], {"backend": "fake-asr", "model": "fixed-fixture"})
        self.assertEqual(log["query_generation"]["backend"], "rules")
        self.assertEqual(
            len(log["query_generation"]["segments"]),
            len(self.read_json("audio_segments.json")["items"]),
        )
        decision = log["query_generation"]["segments"][0]
        self.assertEqual(
            set(decision),
            {
                "segment_id",
                "selected",
                "candidates",
                "strategy",
                "fallback_reason",
                "visual_suitability",
                "candidate_evaluations",
            },
        )
        self.assertTrue(decision["selected"])
        self.assertIn(decision["selected"], decision["candidates"])
        self.assertEqual(len(log["raw_asr_chunks"]), 3)
        event_types = {event["type"] for event in log["segmentation_events"]}
        self.assertIn("merge", event_types)
        self.assertIn("split", event_types)
        self.assertTrue(
            any(event.get("timestamp_estimated") for event in log["segmentation_events"])
        )
        reasons = {
            reason
            for segment in log["review_segments"]
            for reason in segment["reasons"]
        }
        self.assertIn("low_asr_confidence", reasons)
        self.assertIn("estimated_timestamp", reasons)

    def test_query_reranker_failure_falls_back_to_rules_and_is_logged(self) -> None:
        self.write_metadata()

        self.run_pipeline_case(
            self.backend_with_merge_split_and_review(),
            query_reranker=FailingQueryReranker(),
        )
        output = self.read_json("audio_segments.json")
        log = self.read_json("audio_analysis_log.json")

        self.assertTrue(all(item["query"] for item in output["items"]))
        self.assertTrue(log["query_generation"]["fallback_used"])
        self.assertTrue(
            any("query reranker failed" in warning for warning in log["warnings"])
        )

    def test_warning_metadata_continues_and_is_logged(self) -> None:
        self.write_metadata(status="warning")

        self.run_pipeline_case(self.backend_with_merge_split_and_review())
        log = self.read_json("audio_analysis_log.json")

        self.assertEqual(log["status"], "success")
        self.assertTrue(any("warning" in warning for warning in log["warnings"]))

    def test_error_metadata_is_rejected(self) -> None:
        self.write_metadata(status="error")

        with self.assertRaisesRegex(PipelineError, "audio.status is 'error'"):
            self.run_pipeline_case(self.backend_with_merge_split_and_review())

        self.assertFalse((self.output_dir / "audio_segments.json").exists())
        self.assertEqual(self.read_json("audio_analysis_log.json")["status"], "failed")

    def test_existing_output_is_not_overwritten_without_flag(self) -> None:
        self.write_metadata()
        self.run_pipeline_case(self.backend_with_merge_split_and_review())
        output_path = self.output_dir / "audio_segments.json"
        original = output_path.read_bytes()

        with self.assertRaisesRegex(PipelineError, "output already exists"):
            self.run_pipeline_case(self.backend_with_merge_split_and_review())

        self.assertEqual(output_path.read_bytes(), original)

    def test_existing_output_is_overwritten_with_flag(self) -> None:
        self.write_metadata()
        self.run_pipeline_case(self.backend_with_merge_split_and_review())
        replacement = FakeASRBackend(
            [ASRChunk(0.0, 14.0, "Đây là khu vực trưng bày hiện vật lịch sử", None)]
        )

        self.run_pipeline_case(replacement, overwrite=True)
        output = self.read_json("audio_segments.json")

        self.assertEqual(len(output["items"]), 1)
        self.assertEqual(
            output["items"][0]["text"],
            "Đây là khu vực trưng bày hiện vật lịch sử",
        )

    def test_backend_failure_leaves_no_partial_segments_file(self) -> None:
        self.write_metadata()
        backend = FakeASRBackend([], error=RuntimeError("simulated backend failure"))

        with self.assertRaisesRegex(PipelineError, "simulated backend failure"):
            self.run_pipeline_case(backend)

        self.assertFalse((self.output_dir / "audio_segments.json").exists())
        self.assertFalse(list(self.output_dir.glob(".audio_segments.json.*.tmp")))
        log = self.read_json("audio_analysis_log.json")
        self.assertEqual(log["status"], "failed")
        self.assertTrue(any("simulated backend failure" in error for error in log["errors"]))

    def test_invalid_overlapping_chunks_leave_no_segments_file(self) -> None:
        self.write_metadata()
        backend = FakeASRBackend(
            [
                ASRChunk(0.0, 5.0, "Đây là khu vực thứ nhất.", 0.9),
                ASRChunk(4.0, 8.0, "Đây là khu vực thứ hai.", 0.9),
            ]
        )

        with self.assertRaisesRegex(PipelineError, "must not overlap"):
            self.run_pipeline_case(backend)

        self.assertFalse((self.output_dir / "audio_segments.json").exists())

    def test_small_timestamp_overrun_is_clamped_logged_and_reviewed(self) -> None:
        self.write_metadata(duration=4.908)
        backend = FakeASRBackend(
            [ASRChunk(0.0, 5.24, "Đây là khu vực trưng bày.", None)]
        )

        self.run_pipeline_case(backend)
        output = self.read_json("audio_segments.json")
        log = self.read_json("audio_analysis_log.json")

        self.assertEqual(output["items"][-1]["end"], 4.908)
        self.assertAlmostEqual(output["items"][-1]["duration"], 4.908)
        self.assertEqual(len(log["timestamp_adjustments"]), 1)
        self.assertTrue(any("clamped ASR chunk" in warning for warning in log["warnings"]))
        self.assertIn(
            "estimated_timestamp",
            log["review_segments"][-1]["reasons"],
        )

    def test_large_timestamp_overrun_still_fails_without_partial_output(self) -> None:
        self.write_metadata(duration=4.0)
        backend = FakeASRBackend(
            [ASRChunk(0.0, 5.0, "Đây là khu vực trưng bày.", None)]
        )

        with self.assertRaisesRegex(PipelineError, "maximum safe overrun"):
            self.run_pipeline_case(backend)

        self.assertFalse((self.output_dir / "audio_segments.json").exists())


if __name__ == "__main__":
    unittest.main()
