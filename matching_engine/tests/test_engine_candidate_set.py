from __future__ import annotations

from types import SimpleNamespace

from matching_engine.engine import build_candidate_set


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

