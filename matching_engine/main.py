"""Stage 5 entry point.

Luong (theo stage spec §7):
  1. Load + validate 3 input files, check project_id khop
  2. Load text/visual embeddings
  3. Loc clip candidate theo status
  4. Tinh semantic score, sub-scores, penalties
  5. Top-k, selected_clip_id, confidence, fallback
  6. Ghi matching_candidates.json + matching_engine_log.json
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from . import io_utils as io
from .config import load_config
from .engine import run_matching


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(
    audio_segments_path: str,
    clip_metadata_path: str,
    embedding_metadata_path: str,
    output_dir: str,
    config_path: str | None = None,
    top_k: int | None = None,
    overwrite: bool = False,
) -> str:
    """Chạy Matching Engine pipeline.

    Returns path tới matching_candidates.json.
    """
    cfg = load_config(
        config_path,
        audio_segments_path=audio_segments_path,
        clip_metadata_path=clip_metadata_path,
        embedding_metadata_path=embedding_metadata_path,
        output_dir=output_dir,
    )

    # Override top_k from CLI nếu có
    if top_k is not None:
        cfg.raw["top_k"] = top_k

    candidates_path = os.path.join(output_dir, "matching_candidates.json")
    log_path = os.path.join(output_dir, "matching_engine_log.json")

    # Re-run guard (§8.4)
    if os.path.exists(candidates_path) and not overwrite:
        raise io.InputError(
            f"Output da ton tai: {candidates_path}. "
            f"Dung --overwrite de ghi de."
        )

    log: dict = {
        "warnings": [],
        "skipped_clips": [],
        "errors": [],
    }

    # --- Bước 1: Load + validate ---
    audio_data = io.load_audio_segments(audio_segments_path)
    clip_data = io.load_clip_metadata(clip_metadata_path)
    embedding_data = io.load_embedding_metadata(embedding_metadata_path)
    project_id = io.check_project_id(audio_data, clip_data, embedding_data)

    # --- Bước 2–9: Run matching engine ---
    candidate_sets = run_matching(
        audio_data, clip_data, embedding_data, cfg, log
    )

    # --- Bước 10: Ghi output ---
    output = {
        "schema_version": "1.0",
        "project_id": project_id,
        "top_k": cfg.top_k,
        "created_at": _now_iso(),
        "items": candidate_sets,
    }

    # Validate trước khi ghi
    _validate_output(output, audio_data, clip_data, log)

    log["config"] = {
        "top_k": cfg.top_k,
        "score_weights": cfg.raw["score_weights"],
        "penalties": cfg.raw["penalties"],
        "confidence_thresholds": cfg.raw["confidence_thresholds"],
    }
    if log["errors"]:
        io.write_json(log_path, log)
        raise io.InputError(
            "Matching output khong hop le: " + "; ".join(log["errors"])
        )

    io.write_json(candidates_path, output)

    # Ghi log phụ
    log["summary"] = {
        "total_segments": len(audio_data["items"]),
        "total_candidate_sets": len(candidate_sets),
        "fallback_count": sum(
            1 for cs in candidate_sets if cs.get("fallback_used")
        ),
        "confidence_distribution": {
            level: sum(
                1 for cs in candidate_sets if cs.get("confidence") == level
            )
            for level in ("high", "medium", "low")
        },
    }
    io.write_json(log_path, log)

    print(f"[ok] {len(candidate_sets)} candidate sets, top_k={cfg.top_k}")
    print(f"[ok] {candidates_path}")
    return candidates_path


def _validate_output(
    output: dict,
    audio_data: dict,
    clip_data: dict,
    log: dict,
) -> None:
    """Validate output trước khi ghi (§7.10)."""
    valid_seg_ids = {
        seg["segment_id"] for seg in audio_data["items"]
    }
    valid_clip_ids = {
        clip["clip_id"] for clip in clip_data["items"]
    }
    allowed_confidence = {"high", "medium", "low"}

    seen_set_ids: set[str] = set()
    seen_segment_ids: set[str] = set()

    for cs in output.get("items", []):
        set_id = cs.get("candidate_set_id", "")
        if set_id in seen_set_ids:
            log["errors"].append(f"candidate_set_id trung: {set_id}")
        seen_set_ids.add(set_id)

        seg_id = cs.get("audio_segment_id")
        if seg_id not in valid_seg_ids:
            log["errors"].append(
                f"audio_segment_id '{seg_id}' khong ton tai "
                f"trong audio_segments"
            )
        elif seg_id in seen_segment_ids:
            log["errors"].append(
                f"audio_segment_id '{seg_id}' co nhieu candidate set"
            )
        else:
            seen_segment_ids.add(seg_id)

        confidence = cs.get("confidence")
        if confidence not in allowed_confidence:
            log["errors"].append(
                f"confidence '{confidence}' khong hop le trong set {set_id}"
            )

        selected = cs.get("selected_clip_id")
        candidates = cs.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            log["errors"].append(f"candidate set {set_id} khong co candidates")
            continue
        if len(candidates) > output.get("top_k", 0):
            log["errors"].append(f"candidate set {set_id} vuot qua top_k")

        ranks = [candidate.get("rank") for candidate in candidates]
        if ranks != list(range(1, len(candidates) + 1)):
            log["errors"].append(
                f"candidate set {set_id} co rank khong lien tuc tu 1"
            )

        # selected_clip_id phải khớp candidates hoặc null
        if selected is not None:
            cand_clip_ids = [c["clip_id"] for c in candidates]
            if selected not in cand_clip_ids:
                log["errors"].append(
                    f"selected_clip_id '{selected}' khong khop "
                    f"candidates trong set {set_id}"
                )

        # Validate từng candidate
        seen_clips_in_set: set[str] = set()
        for cand in candidates:
            cid = cand.get("clip_id", "")
            if cid in seen_clips_in_set:
                log["errors"].append(
                    f"clip_id '{cid}' trung trong set {set_id}"
                )
            seen_clips_in_set.add(cid)

            if cid not in valid_clip_ids:
                log["errors"].append(
                    f"clip_id '{cid}' khong ton tai trong clip_metadata"
                )

            fs = cand.get("final_score", -1)
            if not (0.0 <= fs <= 1.0):
                log["errors"].append(
                    f"final_score={fs} ngoai [0,1] cho clip {cid} "
                    f"trong set {set_id}"
                )

    missing_segments = valid_seg_ids - seen_segment_ids
    if missing_segments:
        log["errors"].append(
            "thieu candidate set cho segment: " + ", ".join(sorted(missing_segments))
        )


def main():
    p = argparse.ArgumentParser(
        description="Stage 5 — Matching Engine"
    )
    p.add_argument(
        "--audio-segments",
        required=True,
        help="Path toi audio_segments.json",
    )
    p.add_argument(
        "--clip-metadata",
        required=True,
        help="Path toi clip_metadata.json",
    )
    p.add_argument(
        "--embedding-metadata",
        required=True,
        help="Path toi embedding_metadata.json",
    )
    p.add_argument(
        "--output-dir",
        default="data/intermediate",
        help="Thu muc output (default: data/intermediate)",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="So luong candidate toi da (default: 5 tu config)",
    )
    p.add_argument(
        "--config",
        default=None,
        help="Path toi file config JSON (optional)",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Ghi de output neu da ton tai",
    )
    args = p.parse_args()

    try:
        run(
            audio_segments_path=args.audio_segments,
            clip_metadata_path=args.clip_metadata,
            embedding_metadata_path=args.embedding_metadata,
            output_dir=args.output_dir,
            config_path=args.config,
            top_k=args.top_k,
            overwrite=args.overwrite,
        )
    except io.InputError as e:
        print(f"[INPUT ERROR] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
