from __future__ import annotations

import json
import unittest
from pathlib import Path

from integration.contract_gate import DraftContractError, validate_draft_payloads


class DraftContractGateTests(unittest.TestCase):
    def setUp(self) -> None:
        samples = Path(__file__).resolve().parents[2] / "docs" / "samples"
        load = lambda name: json.loads(
            (samples / name).read_text(encoding="utf-8")
        )
        self.payloads = {
            "media_metadata": load("media_metadata_sample.json"),
            "audio_segments": load("audio_segments_sample.json"),
            "clip_metadata": load("clip_metadata_sample.json"),
            "embedding_metadata": load("embedding_metadata_sample.json"),
            "matching_candidates": load("matching_candidates_sample.json"),
            "timeline": load("timeline_sample.json"),
        }

    def test_complete_draft_passes(self) -> None:
        validate_draft_payloads(**self.payloads)

    def test_missing_text_embedding_is_rejected(self) -> None:
        self.payloads["embedding_metadata"]["text_embeddings"].pop()

        with self.assertRaisesRegex(DraftContractError, "text embedding coverage"):
            validate_draft_payloads(**self.payloads)

    def test_timeline_gap_is_rejected(self) -> None:
        self.payloads["timeline"]["items"][0]["audio_start"] = 0.2

        with self.assertRaisesRegex(DraftContractError, "draft handoff"):
            validate_draft_payloads(**self.payloads)


if __name__ == "__main__":
    unittest.main()
