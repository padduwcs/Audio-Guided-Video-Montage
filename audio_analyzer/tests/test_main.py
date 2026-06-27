from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from audio_analyzer.main import build_parser, main
from audio_analyzer.metadata import MetadataValidationError, load_audio_input
from audio_analyzer.models import ASRChunk
from audio_analyzer.tests.fakes import FakeASRBackend


class AudioAnalyzerPhaseOneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.metadata_path = self.root / "data" / "intermediate" / "media_metadata.json"
        self.audio_path = self.root / "data" / "normalized" / "voiceover.wav"
        self.metadata_path.parent.mkdir(parents=True)
        self.audio_path.parent.mkdir(parents=True)
        self.audio_path.write_bytes(b"phase-one-audio-placeholder")

    def write_metadata(
        self,
        *,
        status: object = "ready",
        normalized_path: object = "data/normalized/voiceover.wav",
        duration: object = 4.25,
    ) -> None:
        payload = {
            "schema_version": "1.0",
            "project_id": "test_project",
            "audio": {
                "audio_id": "audio_01",
                "normalized_path": normalized_path,
                "duration": duration,
                "status": status,
            },
        }
        self.metadata_path.write_text(json.dumps(payload), encoding="utf-8")

    def run_cli(self, *extra_arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        arguments = [
            "--media-metadata",
            str(self.metadata_path),
            "--output-dir",
            str(self.root / "data" / "intermediate"),
            *extra_arguments,
        ]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                arguments,
                project_root=self.root,
                asr_backend=FakeASRBackend(
                    [ASRChunk(0.0, 4.25, "Đây là khu vực trưng bày.", None)]
                ),
            )
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_ready_audio_runs_injected_backend_and_creates_output(self) -> None:
        self.write_metadata()

        exit_code, stdout, stderr = self.run_cli()

        self.assertEqual(exit_code, 0)
        self.assertIn("Created", stdout)
        self.assertEqual(stderr, "")
        self.assertTrue(
            (self.root / "data" / "intermediate" / "audio_segments.json").exists()
        )

    def test_cli_language_defaults_to_auto(self) -> None:
        arguments = build_parser().parse_args(
            [
                "--media-metadata",
                str(self.metadata_path),
                "--output-dir",
                str(self.metadata_path.parent),
            ]
        )

        self.assertEqual(arguments.language, "auto")

    def test_warning_audio_is_accepted_and_reported(self) -> None:
        self.write_metadata(status="warning")

        exit_code, stdout, stderr = self.run_cli("--overwrite")

        self.assertEqual(exit_code, 0)
        self.assertIn("Created", stdout)
        self.assertEqual(stderr, "")
        log = json.loads(
            (self.root / "data" / "intermediate" / "audio_analysis_log.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(any("warning" in warning for warning in log["warnings"]))

    def test_error_audio_stops_with_clear_message(self) -> None:
        self.write_metadata(status="error")

        exit_code, stdout, stderr = self.run_cli()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("audio.status is 'error'", stderr)

    def test_unsupported_status_is_rejected(self) -> None:
        self.write_metadata(status="pending")

        with self.assertRaisesRegex(MetadataValidationError, "ready.*warning"):
            load_audio_input(self.metadata_path, self.root)

    def test_missing_normalized_path_is_rejected(self) -> None:
        self.write_metadata(normalized_path="")

        with self.assertRaisesRegex(MetadataValidationError, "normalized_path"):
            load_audio_input(self.metadata_path, self.root)

    def test_absolute_normalized_path_is_rejected(self) -> None:
        self.write_metadata(normalized_path=str(self.audio_path.resolve()))

        with self.assertRaisesRegex(MetadataValidationError, "must be relative"):
            load_audio_input(self.metadata_path, self.root)

    def test_normalized_path_outside_project_is_rejected(self) -> None:
        self.write_metadata(normalized_path="../voiceover.wav")

        with self.assertRaisesRegex(MetadataValidationError, "inside the project root"):
            load_audio_input(self.metadata_path, self.root)

    def test_non_positive_duration_is_rejected(self) -> None:
        self.write_metadata(duration=0)

        with self.assertRaisesRegex(MetadataValidationError, "duration"):
            load_audio_input(self.metadata_path, self.root)

    def test_boolean_duration_is_rejected(self) -> None:
        self.write_metadata(duration=True)

        with self.assertRaisesRegex(MetadataValidationError, "duration"):
            load_audio_input(self.metadata_path, self.root)

    def test_missing_audio_file_is_rejected(self) -> None:
        self.write_metadata()
        self.audio_path.unlink()

        exit_code, stdout, stderr = self.run_cli()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("does not exist", stderr)

    def test_invalid_json_is_rejected(self) -> None:
        self.metadata_path.write_text("{not-json", encoding="utf-8")

        exit_code, _, stderr = self.run_cli()

        self.assertEqual(exit_code, 1)
        self.assertIn("invalid JSON", stderr)


if __name__ == "__main__":
    unittest.main()
