"""Core matching logic — orchestrate scoring, ranking, fallback.

Tham chiếu: stage spec §7.1 – §7.10.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from .config import Config
from .io_utils import InputError
from .scorer import (
    aggregate_keyframe_scores,
    compute_duration_fit_score,
    compute_final_score,
    compute_semantic_score,
    compute_ocr_score,
    map_confidence,
    solve_dp_assignment,
)


# ---------- FAISS index loading & search ----------


def _try_load_faiss(
    embedding_data: dict,
    log: dict,
) -> tuple[Any, list[dict]] | tuple[None, None]:
    """Load FAISS index + visual_embeddings list.

    Row i in the index corresponds to visual_embeddings[i] — this
    ordering invariant is set by embedding_indexer (indexer.py).
    Returns (index, visual_embeddings) or (None, None) on failure.
    """
    index_info = embedding_data.get("index", {})
    index_path = index_info.get("path", "")
    if not index_path:
        log["warnings"].append("embedding_metadata khong co index.path -> brute-force")
        return None, None

    visual_embs = embedding_data.get("visual_embeddings", [])
    if not visual_embs:
        return None, None

    # Try native FAISS index first, then .npy fallback
    if os.path.exists(index_path):
        try:
            import faiss

            index = faiss.read_index(index_path)
            if index.ntotal != len(visual_embs):
                log["warnings"].append(
                    f"FAISS index size ({index.ntotal}) != "
                    f"visual_embeddings ({len(visual_embs)}) -> brute-force"
                )
                return None, None
            return index, visual_embs
        except ImportError:
            log["warnings"].append("faiss-cpu chua cai -> brute-force")
            return None, None
        except Exception as e:
            log["warnings"].append(f"Loi load FAISS index: {e} -> brute-force")
            return None, None

    npy_path = index_path + ".npy"
    if os.path.exists(npy_path):
        try:
            import faiss

            matrix = np.load(npy_path).astype("float32")
            if matrix.shape[0] != len(visual_embs):
                log["warnings"].append(
                    f"NPY matrix rows ({matrix.shape[0]}) != "
                    f"visual_embeddings ({len(visual_embs)}) -> brute-force"
                )
                return None, None
            dim = matrix.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(matrix)
            return index, visual_embs
        except ImportError:
            log["warnings"].append("faiss-cpu chua cai -> brute-force")
            return None, None
        except Exception as e:
            log["warnings"].append(f"Loi load NPY fallback: {e} -> brute-force")
            return None, None

    log["warnings"].append(
        f"FAISS index khong ton tai: {index_path} -> brute-force"
    )
    return None, None


def _faiss_batch_search(
    index: Any,
    visual_embs: list[dict],
    text_vectors: dict[str, np.ndarray],
    pre_k: int,
) -> dict[str, dict[str, float]]:
    """Batch FAISS search for all text vectors at once.

    Returns: seg_id -> {clip_id: max_cosine_sim_across_keyframes}.
    IndexFlatIP on L2-normalized vectors = cosine similarity.
    """
    seg_ids = list(text_vectors.keys())
    if not seg_ids:
        return {}

    query_matrix = np.vstack(
        [text_vectors[sid] for sid in seg_ids]
    ).astype("float32")
    k = min(pre_k, index.ntotal)

    scores, indices = index.search(query_matrix, k)

    result: dict[str, dict[str, float]] = {}
    for i, seg_id in enumerate(seg_ids):
        clip_sims: dict[str, float] = {}
        for j in range(k):
            row_idx = int(indices[i, j])
            if row_idx < 0:
                continue
            sim = float(scores[i, j])
            clip_id = visual_embs[row_idx]["clip_id"]
            if clip_id not in clip_sims or sim > clip_sims[clip_id]:
                clip_sims[clip_id] = sim
        result[seg_id] = clip_sims

    return result


# ---------- Status filter (§4.3) ----------

MATCHABLE_STATUSES = {"usable", "low_quality"}
SKIP_STATUSES = {"too_short", "error"}


# ---------- Embedding loading (§7.1) ----------


def _load_vector(vector_path: str, dimension: int) -> np.ndarray | None:
    """Load 1-d vector từ .npy file. Trả None nếu lỗi."""
    if not vector_path or not os.path.exists(vector_path):
        return None
    try:
        vec = np.load(vector_path)
        if vec.ndim == 1 and vec.shape[0] == dimension:
            return vec
    except Exception:
        pass
    return None


def load_text_vectors(
    embedding_data: dict,
    dimension: int,
    log: dict,
) -> dict[str, np.ndarray]:
    """Map segment_id → text vector."""
    result: dict[str, np.ndarray] = {}
    for emb in embedding_data.get("text_embeddings", []):
        seg_id = emb.get("segment_id")
        if not seg_id:
            log["warnings"].append(
                f"Text embedding {emb.get('embedding_id')} thieu segment_id"
            )
            continue
        vec = _load_vector(emb.get("vector_path", ""), dimension)
        if vec is None:
            log["warnings"].append(
                f"Khong load duoc text vector cho segment {seg_id}: "
                f"{emb.get('vector_path')}"
            )
            continue
        result[seg_id] = vec
    return result


def load_visual_vectors(
    embedding_data: dict,
    dimension: int,
    log: dict,
) -> dict[str, list[tuple[str, np.ndarray]]]:
    """Map clip_id → [(keyframe_id, vector), ...].

    Một clip có thể có nhiều keyframe embedding.
    """
    result: dict[str, list[tuple[str, np.ndarray]]] = {}
    for emb in embedding_data.get("visual_embeddings", []):
        clip_id = emb.get("clip_id")
        kf_id = emb.get("keyframe_id", "")
        if not clip_id:
            log["warnings"].append(
                f"Visual embedding {emb.get('embedding_id')} thieu clip_id"
            )
            continue
        vec = _load_vector(emb.get("vector_path", ""), dimension)
        if vec is None:
            log["warnings"].append(
                f"Khong load duoc visual vector cho {clip_id}/{kf_id}: "
                f"{emb.get('vector_path')}"
            )
            continue
        result.setdefault(clip_id, []).append((kf_id, vec))
    return result


# ---------- Clip filtering (§7.2) ----------


def filter_matchable_clips(
    clip_data: dict,
    visual_vectors: dict[str, list],
    log: dict,
) -> dict[str, dict]:
    """Trả dict clip_id → clip metadata cho clip hợp lệ.

    Chỉ giữ clip status=usable/low_quality VÀ có visual embedding.
    """
    result: dict[str, dict] = {}
    for clip in clip_data.get("items", []):
        clip_id = clip.get("clip_id", "")
        status = clip.get("status")

        # Skip theo status
        if status in SKIP_STATUSES:
            log["skipped_clips"].append(
                {"clip_id": clip_id, "reason": f"status={status}"}
            )
            continue

        # Thiếu status → warning, xử lý như usable (§4.3)
        if status is None:
            log["warnings"].append(
                f"Clip {clip_id} thieu status -> xu ly nhu usable"
            )
        elif status not in MATCHABLE_STATUSES:
            log["warnings"].append(
                f"Clip {clip_id} status='{status}' khong nhan dien "
                f"-> xu ly nhu usable"
            )

        # Clip phải có visual embedding
        if clip_id not in visual_vectors:
            log["skipped_clips"].append(
                {"clip_id": clip_id, "reason": "khong co visual embedding"}
            )
            continue

        result[clip_id] = clip
    return result


# ---------- Scoring per segment (§7.3 – §7.7) ----------


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity giữa 2 vector đã normalize → dot product."""
    return float(np.dot(a, b))


def score_segment(
    segment: dict,
    text_vec: np.ndarray,
    matchable_clips: dict[str, dict],
    visual_vectors: dict[str, list[tuple[str, np.ndarray]]],
    cfg: Config,
    prev_selected_clip_id: str | None,
    *,
    faiss_cosine: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Tính score và trả danh sách candidate cho 1 segment.

    Args:
        faiss_cosine: If provided (from FAISS batch search), maps
            clip_id → max cosine similarity across keyframes.
            Skips brute-force cosine computation.

    Returns list of candidate dicts (chưa cắt top-k).
    """
    seg_duration = segment.get("duration", 0.0)
    seg_text = segment.get("text", "")
    candidates: list[dict[str, Any]] = []

    for clip_id, clip in matchable_clips.items():
        # §7.3: Semantic score — FAISS path or brute-force
        if faiss_cosine is not None:
            if clip_id not in faiss_cosine:
                continue
            semantic_score = compute_semantic_score(faiss_cosine[clip_id])
        else:
            kf_vectors = visual_vectors.get(clip_id, [])
            if not kf_vectors:
                continue
            kf_scores = []
            for _kf_id, vis_vec in kf_vectors:
                cos_sim = _cosine_similarity(text_vec, vis_vec)
                kf_scores.append(compute_semantic_score(cos_sim))
            semantic_score = aggregate_keyframe_scores(kf_scores)
            
        content_tags = clip.get("content_tags", [])
        ocr_score = compute_ocr_score(seg_text, content_tags)

        # §7.4: Duration fit
        clip_duration = clip.get("duration", 0.0)
        duration_fit_score = compute_duration_fit_score(
            clip_duration, seg_duration
        )

        # §7.4: Visual quality — lấy trực tiếp từ clip_metadata
        raw_quality = clip.get("quality_score")
        visual_quality_score: float | None = None
        if raw_quality is not None:
            visual_quality_score = float(raw_quality)
        # §7.4: Continuity/diversity — chưa triển khai MVP
        continuity_score: float | None = None
        diversity_score: float | None = None

        # §7.5: Penalties
        status = clip.get("status", "usable")
        bad_clip_penalty = 0.0
        if status == "low_quality":
            bad_clip_penalty = cfg.penalty_low_quality

        repetition_penalty = 0.0
        if prev_selected_clip_id and clip_id == prev_selected_clip_id:
            repetition_penalty = cfg.penalty_recent_repetition

        # §7.6: Final score
        final_score = compute_final_score(
            semantic_score=semantic_score,
            visual_quality_score=visual_quality_score,
            duration_fit_score=duration_fit_score,
            continuity_score=continuity_score,
            diversity_score=diversity_score,
            bad_clip_penalty=bad_clip_penalty,
            repetition_penalty=repetition_penalty,
            ocr_score=ocr_score,
            w_semantic=cfg.weight_semantic,
            w_visual_quality=cfg.weight_visual_quality,
            w_duration_fit=cfg.weight_duration_fit,
            w_continuity=cfg.weight_continuity,
            w_diversity=cfg.weight_diversity,
            clip_id=clip_id,
            seg_id=segment["segment_id"],
        )

        candidate: dict[str, Any] = {
            "clip_id": clip_id,
            "final_score": round(final_score, 4),
            "semantic_score": round(semantic_score, 4),
            "visual_quality_score": (
                round(visual_quality_score, 4)
                if visual_quality_score is not None
                else None
            ),
            "duration_fit_score": round(duration_fit_score, 4),
            "continuity_score": continuity_score,
            "diversity_score": diversity_score,
            "ocr_score": round(ocr_score, 4),
            "repetition_penalty": round(repetition_penalty, 4),
            "bad_clip_penalty": round(bad_clip_penalty, 4),
        }

        # Ghi reason nếu có penalty
        reasons: list[str] = []
        if bad_clip_penalty > 0:
            reasons.append(f"low_quality penalty -{bad_clip_penalty}")
        if repetition_penalty > 0:
            reasons.append(f"repetition penalty -{repetition_penalty}")
        if ocr_score > 0:
            reasons.append(f"OCR match bonus!")
        if reasons:
            candidate["reason"] = "; ".join(reasons)

        candidates.append(candidate)

    return candidates


# ---------- Top-k, selected_clip, confidence, fallback (§7.7 – §7.9) ---


def build_candidate_set(
    segment: dict,
    candidates: list[dict[str, Any]],
    cfg: Config,
    log: dict,
    *,
    dp_selected_clip_id: str | None = None,
) -> dict[str, Any]:
    """Xây dựng candidate set cho 1 segment.

    Bao gồm: sort, top-k, chọn clip mặc định, confidence, fallback.
    Nếu dp_selected_clip_id được cung cấp, dùng clip do DP chọn thay
    vì luôn chọn rank 1 (tối ưu toàn cục thay vì cục bộ).
    """
    seg_id = segment["segment_id"]

    # §7.7: Sort final_score giảm dần → loại trùng clip_id → top-k
    # (clip_id đã unique vì score_segment tính theo clip, không keyframe)
    candidates.sort(key=lambda c: c["final_score"], reverse=True)
    top_k_candidates = candidates[: cfg.top_k]

    # Gán rank
    for i, c in enumerate(top_k_candidates, start=1):
        c["rank"] = i

    # §7.7 + §7.9: selected_clip_id và fallback
    fallback_used = False
    selected_clip_id: str | None = None
    reason = ""

    if top_k_candidates:
        best = top_k_candidates[0]
        # Nếu semantic_score quá thấp (< threshold_medium) → fallback
        best_semantic = best.get("semantic_score", 0.0)
        if best_semantic < cfg.threshold_medium and cfg.fallback_enabled:
            fallback_used = True
            selected_clip_id = (
                dp_selected_clip_id
                if dp_selected_clip_id is not None
                else best["clip_id"]
            )
            reason = (
                f"Fallback: best semantic_score={best_semantic:.2f} "
                f"< {cfg.threshold_medium}. "
                f"Chon clip tot nhat (DP global)."
            )
        elif dp_selected_clip_id is not None:
            # DP đã chọn clip tối ưu toàn cục
            selected_clip_id = dp_selected_clip_id
            # Tìm score của clip DP chọn
            dp_score = next(
                (
                    c["final_score"]
                    for c in top_k_candidates
                    if c["clip_id"] == dp_selected_clip_id
                ),
                best["final_score"],
            )
            reason = (
                f"DP optimal: clip {dp_selected_clip_id} "
                f"voi final_score={dp_score:.2f} "
                f"(toi uu toan cuc)."
            )
        else:
            selected_clip_id = best["clip_id"]
            reason = (
                f"Clip rank 1 voi final_score={best['final_score']:.2f}."
            )
    else:
        # Không có candidate nào → §7.9
        fallback_used = True
        reason = "Khong co clip hop le cho segment nay."

    # §7.8: Confidence mapping — dùng score của clip được chọn (DP hoặc rank 1)
    if selected_clip_id and top_k_candidates:
        selected_final_score = next(
            (
                c["final_score"]
                for c in top_k_candidates
                if c["clip_id"] == selected_clip_id
            ),
            top_k_candidates[0]["final_score"],
        )
    else:
        selected_final_score = (
            top_k_candidates[0]["final_score"]
            if top_k_candidates
            else 0.0
        )

    # needs_review -> có thể giảm confidence (§7.8)
    needs_review = segment.get("needs_review", False)

    confidence = map_confidence(
        selected_final_score,
        fallback_used,
        threshold_high=cfg.threshold_high,
        threshold_medium=cfg.threshold_medium,
    )

    # Nếu segment needs_review VÀ confidence != low → giảm 1 mức
    if needs_review and confidence != "low":
        if confidence == "high":
            confidence = "medium"
        elif confidence == "medium":
            confidence = "low"
        reason += " Segment needs_review=true -> giam confidence."

    candidate_set: dict[str, Any] = {
        "candidate_set_id": f"candidates_{seg_id}",
        "audio_segment_id": seg_id,
        "selected_clip_id": selected_clip_id,
        "confidence": confidence,
        "reason": reason,
        "fallback_used": fallback_used,
        "candidates": top_k_candidates,
    }

    # Log stats
    log.setdefault("segment_stats", []).append(
        {
            "segment_id": seg_id,
            "total_scored": len(candidates),
            "top_k_returned": len(top_k_candidates),
            "selected_clip_id": selected_clip_id,
            "confidence": confidence,
            "fallback_used": fallback_used,
        }
    )

    return candidate_set


# ---------- Main pipeline — Dynamic Programming (§7.1 – §7.10) ----------


def run_matching(
    audio_data: dict,
    clip_data: dict,
    embedding_data: dict,
    cfg: Config,
    log: dict,
) -> list[dict[str, Any]]:
    """Chạy matching pipeline bằng Quy hoạch động (DP).

    Thay vì greedy (chọn clip tốt nhất từng segment rồi phạt trùng
    segment kế), thuật toán gồm 3 phase:

    Phase 1: Tính base score cho TẤT CẢ cặp (segment, clip) — KHÔNG
             có repetition_penalty.
    Phase 2: Chạy DP tìm chuỗi clip tối ưu toàn cục, tối đa tổng
             score và phạt trùng lặp giữa segment liên tiếp.
    Phase 3: Áp repetition_penalty theo path DP, re-rank candidate,
             build output.

    DP đảm bảo tối ưu toàn cục — greedy có thể chọn clip tốt nhất
    cho segment hiện tại nhưng gây trùng lặp ở các segment sau.
    """
    dimension = embedding_data["model"]["dimension"]

    # §7.1: Load text embeddings (always needed)
    text_vectors = load_text_vectors(embedding_data, dimension, log)
    if not text_vectors:
        raise InputError("Khong load duoc text vector nao")

    # §7.1b: Try FAISS index — skip loading individual .npy if available
    faiss_index, faiss_visual_embs = _try_load_faiss(embedding_data, log)
    faiss_cosine_map: dict[str, dict[str, float]] | None = None

    if faiss_index is not None:
        faiss_cosine_map = _faiss_batch_search(
            faiss_index, faiss_visual_embs, text_vectors, cfg.faiss_pre_k,
        )
        clips_with_embeddings: dict[str, list] = {
            emb["clip_id"]: [] for emb in faiss_visual_embs
        }
        visual_vectors: dict[str, list[tuple[str, np.ndarray]]] = {}
        log["search_method"] = "faiss"
        log["faiss_info"] = {
            "index_size": faiss_index.ntotal,
            "pre_k": cfg.faiss_pre_k,
        }
    else:
        visual_vectors = load_visual_vectors(embedding_data, dimension, log)
        clips_with_embeddings = visual_vectors
        log["search_method"] = "brute_force"

    # §7.2: Filter clips
    matchable_clips = filter_matchable_clips(
        clip_data, clips_with_embeddings, log,
    )

    if not matchable_clips:
        log["warnings"].append(
            "Khong co clip nao hop le (matchable) -> moi segment se fallback"
        )

    segments = audio_data["items"]

    # ================================================================
    # PHASE 1: Tính base score cho tất cả cặp (segment, clip)
    #          KHÔNG repetition_penalty — dùng làm input cho DP.
    # ================================================================
    all_base_candidates: list[list[dict[str, Any]] | None] = []
    dp_segment_indices: list[int] = []   # chỉ mục segment tham gia DP
    fallback_indices: set[int] = set()   # segment phải fallback

    for i, segment in enumerate(segments):
        seg_id = segment["segment_id"]
        text_vec = text_vectors.get(seg_id)

        if text_vec is None:
            # Segment thiếu text embedding → fallback, không tham gia DP
            log["warnings"].append(
                f"Segment {seg_id} thieu text embedding -> fallback"
            )
            all_base_candidates.append(None)
            fallback_indices.add(i)
            continue

        # Tính score KHÔNG repetition_penalty (prev_selected=None)
        seg_faiss = (
            faiss_cosine_map.get(seg_id) if faiss_cosine_map else None
        )
        candidates = score_segment(
            segment,
            text_vec,
            matchable_clips,
            visual_vectors,
            cfg,
            prev_selected_clip_id=None,
            faiss_cosine=seg_faiss,
        )
        all_base_candidates.append(candidates)
        dp_segment_indices.append(i)

    # ================================================================
    # PHASE 2: Chạy DP tìm phương án gán clip tối ưu toàn cục.
    # ================================================================
    dp_selected_map: dict[int, str | None] = {}  # seg_index → clip_id

    if dp_segment_indices:
        # Xây score matrix cho DP: mỗi phần tử là dict {clip_id: base_score}
        score_matrix: list[dict[str, float]] = []
        for seg_idx in dp_segment_indices:
            candidates = all_base_candidates[seg_idx]
            assert candidates is not None
            seg_scores = {
                c["clip_id"]: c["final_score"] for c in candidates
            }
            score_matrix.append(seg_scores)

        # Giải DP
        dp_result = solve_dp_assignment(
            score_matrix,
            cfg.penalty_recent_repetition,
            clip_metadata=matchable_clips,
            continuity_weight=cfg.weight_continuity,
        )

        # Map kết quả DP về chỉ mục segment gốc
        for dp_idx, seg_idx in enumerate(dp_segment_indices):
            dp_selected_map[seg_idx] = (
                dp_result[dp_idx]
                if dp_idx < len(dp_result)
                else None
            )

        log["dp_info"] = {
            "algorithm": "dynamic_programming",
            "segments_in_dp": len(dp_segment_indices),
            "total_clips": len(matchable_clips),
            "dp_assignment": [
                {
                    "segment_id": segments[si]["segment_id"],
                    "selected_clip_id": dp_selected_map.get(si),
                }
                for si in dp_segment_indices
            ],
        }

    # ================================================================
    # PHASE 3: Áp repetition_penalty theo DP path → re-rank → output.
    # ================================================================
    candidate_sets: list[dict[str, Any]] = []

    for i, segment in enumerate(segments):
        # --- Fallback segment ---
        if i in fallback_indices:
            cs = _build_fallback_set(segment, matchable_clips, cfg, log)
            candidate_sets.append(cs)
            continue

        # --- Tìm clip DP-selected ở segment trước ---
        prev_dp_clip: str | None = None
        # Duyệt ngược tìm segment liền trước có DP selection
        for prev_i in range(i - 1, -1, -1):
            if prev_i in dp_selected_map:
                prev_dp_clip = dp_selected_map[prev_i]
                break
            if prev_i in fallback_indices and candidate_sets:
                # Fallback segment — lấy clip nó đã chọn
                prev_dp_clip = candidate_sets[prev_i].get(
                    "selected_clip_id"
                )
                break

        # --- Áp repetition_penalty theo DP path ---
        candidates = all_base_candidates[i]
        assert candidates is not None

        for c in candidates:
            if prev_dp_clip and c["clip_id"] == prev_dp_clip:
                pen = cfg.penalty_recent_repetition
                c["repetition_penalty"] = round(pen, 4)
                # Trừ penalty khỏi final_score
                c["final_score"] = round(
                    max(0.0, min(1.0, c["final_score"] - pen)), 4
                )
                existing_reason = c.get("reason", "")
                penalty_reason = f"repetition penalty -{pen}"
                c["reason"] = (
                    f"{existing_reason}; {penalty_reason}"
                    if existing_reason
                    else penalty_reason
                )

        # --- Re-sort theo adjusted final_score ---
        candidates.sort(key=lambda c: c["final_score"], reverse=True)
        top_k = candidates[: cfg.top_k]
        for rank, c in enumerate(top_k, start=1):
            c["rank"] = rank

        # --- Build candidate set với DP-selected clip ---
        dp_clip = dp_selected_map.get(i)
        cs = build_candidate_set(
            segment, candidates, cfg, log,
            dp_selected_clip_id=dp_clip,
        )
        candidate_sets.append(cs)

    return candidate_sets


def _build_fallback_set(
    segment: dict,
    matchable_clips: dict[str, dict],
    cfg: Config,
    log: dict,
) -> dict[str, Any]:
    """Tạo candidate set fallback khi không tính score được."""
    seg_id = segment["segment_id"]

    if not matchable_clips:
        # Không có clip nào → candidate rỗng (§7.9)
        return {
            "candidate_set_id": f"candidates_{seg_id}",
            "audio_segment_id": seg_id,
            "selected_clip_id": None,
            "confidence": "low",
            "reason": "Khong co clip hop le. Fallback khong tim duoc clip.",
            "fallback_used": True,
            "candidates": [],
        }

    # Chọn clip usable quality cao nhất (§7.9)
    sorted_clips = sorted(
        matchable_clips.values(),
        key=lambda c: c.get("quality_score") or 0.0,
        reverse=True,
    )

    # Lọc: ưu tiên usable, chỉ dùng low_quality nếu config cho phép
    best_clip = None
    for clip in sorted_clips:
        status = clip.get("status", "usable")
        if status == "usable":
            best_clip = clip
            break
        if status == "low_quality" and cfg.fallback_allow_low_quality:
            best_clip = clip
            break

    if best_clip is None:
        best_clip = sorted_clips[0]  # cuối cùng chọn cái tốt nhất

    clip_id = best_clip["clip_id"]
    quality = best_clip.get("quality_score")

    candidate = {
        "rank": 1,
        "clip_id": clip_id,
        "final_score": round(quality or 0.5, 4),
        "semantic_score": 0.0,
        "visual_quality_score": quality,
        "duration_fit_score": round(
            compute_duration_fit_score(
                best_clip.get("duration", 0),
                segment.get("duration", 0),
            ),
            4,
        ),
        "continuity_score": None,
        "diversity_score": None,
        "repetition_penalty": 0.0,
        "bad_clip_penalty": 0.0,
        "reason": "Fallback: thieu text embedding cho segment.",
    }

    log.setdefault("segment_stats", []).append(
        {
            "segment_id": seg_id,
            "total_scored": 0,
            "top_k_returned": 1,
            "selected_clip_id": clip_id,
            "confidence": "low",
            "fallback_used": True,
        }
    )

    return {
        "candidate_set_id": f"candidates_{seg_id}",
        "audio_segment_id": seg_id,
        "selected_clip_id": clip_id,
        "confidence": "low",
        "reason": (
            f"Fallback: thieu text embedding. "
            f"Chon clip {clip_id} (quality={quality})."
        ),
        "fallback_used": True,
        "candidates": [candidate],
    }
