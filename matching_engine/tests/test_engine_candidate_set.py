from __future__ import annotations

from types import SimpleNamespace

from matching_engine.engine import build_candidate_set
from matching_engine.main import _validate_output


def _cfg(top_k: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        top_k=top_k,
        threshold_medium=0.4,
        threshold_high=0.75,
        fallback_enabled=True,
    )


def _candidate(clip_id: str, score: float) -> dict:
    return {
        "clip_id": clip_id,
        "final_score": score,
        "semantic_score": 0.8,
    }


def test_dp_selected_clip_is_kept_in_top_k_candidates() -> None:
    log: dict = {"warnings": []}
    candidates = [
        _candidate("clip_1", 0.90),
        _candidate("clip_2", 0.89),
        _candidate("clip_3", 0.88),
        _candidate("clip_4", 0.87),
        _candidate("clip_5", 0.86),
        _candidate("clip_6", 0.30),
    ]

    candidate_set = build_candidate_set(
        {"segment_id": "a001"},
        candidates,
        _cfg(top_k=5),
        log,
        dp_selected_clip_id="clip_6",
    )

    output_clip_ids = {
        candidate["clip_id"] for candidate in candidate_set["candidates"]
    }
    assert candidate_set["selected_clip_id"] == "clip_6"
    assert "clip_6" in output_clip_ids
    assert len(candidate_set["candidates"]) == 5


def test_output_validation_requires_one_candidate_set_per_segment() -> None:
    output = {"top_k": 1, "items": []}
    audio = {"items": [{"segment_id": "a001"}]}
    clips = {"items": [{"clip_id": "clip_1"}]}
    log = {"errors": []}

    _validate_output(output, audio, clips, log)

    assert any("a001" in error for error in log["errors"])


def test_output_validation_accepts_complete_ranked_candidates() -> None:
    output = {
        "top_k": 1,
        "items": [
            {
                "candidate_set_id": "cs_001",
                "audio_segment_id": "a001",
                "selected_clip_id": "clip_1",
                "confidence": "high",
                "candidates": [
                    {"rank": 1, "clip_id": "clip_1", "final_score": 0.9}
                ],
            }
        ],
    }
    audio = {"items": [{"segment_id": "a001"}]}
    clips = {"items": [{"clip_id": "clip_1"}]}
    log = {"errors": []}

    _validate_output(output, audio, clips, log)

    assert log["errors"] == []

