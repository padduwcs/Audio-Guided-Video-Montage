"""Scoring logic cho Matching Engine.

Tách riêng để dễ test và dễ thay đổi công thức.
Tham chiếu: stage spec §7.3 – §7.8.
"""

from __future__ import annotations

import os
import json
from .feedback_applier import get_feedback_override

def compute_semantic_score(cosine_similarity: float) -> float:
    """Chuyển cosine similarity [-1, 1] → semantic_score [0, 1].

    Công thức cải tiến: contrast-enhanced rescaling.
    CLIP cosine similarity giữa text và image thường nằm trong [0.15, 0.40].
    Linear map (cos+1)/2 nén khoảng này thành [0.575, 0.70] → mất phân biệt.

    Thay vào đó dùng clamp + rescale:
      - Clamp vào [low, high] = [0.15, 0.40]
      - Rescale linearly vào [0, 1]
    Giá trị ngoài khoảng bị clamp về 0 hoặc 1.
    """
    # Khoảng cosine similarity hữu ích cho CLIP text-image
    LOW = 0.15
    HIGH = 0.40
    if cosine_similarity <= LOW:
        return 0.0
    if cosine_similarity >= HIGH:
        return 1.0
    return (cosine_similarity - LOW) / (HIGH - LOW)


def aggregate_keyframe_scores(scores: list[float]) -> float:
    """Gộp keyframe-level score về clip-level.

    MVP dùng max — một keyframe khớp tốt đủ đại diện clip (§7.3).
    """
    if not scores:
        return 0.0
    return max(scores)


import unicodedata

def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def compute_ocr_score(segment_text: str, content_tags: list[str]) -> float:
    """Tinh diem OCR bang cach so khop tu khoa."""
    if not segment_text or not content_tags:
        return 0.0
    
    seg_clean = remove_accents(segment_text.lower())
    for tag in content_tags:
        tag_clean = remove_accents(tag.lower())
        if tag_clean in seg_clean:
            return 1.0
        # Tu khoa tung phan
        tag_words = set(tag_clean.split())
        seg_words = set(seg_clean.split())
        if len(tag_words) > 0 and len(tag_words.intersection(seg_words)) >= max(1, len(tag_words) - 1):
            return 1.0
    return 0.0

def compute_duration_fit_score(
    clip_duration: float, segment_duration: float
) -> float:
    """Tính duration_fit_score (§7.4).

    clip.duration >= segment.duration  →  1.0
    else                              →  clip.duration / segment.duration
    Clamp về [0.0, 1.0].
    """
    if segment_duration <= 0:
        return 1.0
    if clip_duration >= segment_duration:
        return 1.0
    score = clip_duration / segment_duration
    return max(0.0, min(1.0, score))


def compute_final_score(
    semantic_score: float,
    visual_quality_score: float | None,
    duration_fit_score: float,
    continuity_score: float | None,
    diversity_score: float | None,
    bad_clip_penalty: float,
    repetition_penalty: float,
    ocr_score: float = 0.0,
    *,
    w_semantic: float = 0.50,
    w_visual_quality: float = 0.15,
    w_duration_fit: float = 0.15,
    w_continuity: float = 0.05,
    w_diversity: float = 0.05,
    w_ocr: float = 0.10,
    clip_id: str = "",
    seg_id: str = "",
) -> float:
    """Tính final_score theo công thức §7.6.

    base_score =
        w_semantic       * semantic_score
      + w_visual_quality * visual_quality_score_effective
      + w_duration_fit   * duration_fit_score
      + w_continuity     * continuity_score_effective
      + w_diversity      * diversity_score_effective
      + w_ocr            * ocr_score

    final_score = base_score - repetition_penalty - bad_clip_penalty
    final_score = clamp(final_score, 0.0, 1.0)
    """
    
    # Kiem tra Agent 2 feedback
    override_clip_id = get_feedback_override(seg_id)
    if override_clip_id and clip_id == override_clip_id:
        return 1.0

    # Tính phần optional weight bị bỏ
    missing_weight = 0.0
    if visual_quality_score is None:
        missing_weight += w_visual_quality
    if continuity_score is None:
        missing_weight += w_continuity
    if diversity_score is None:
        missing_weight += w_diversity

    # Phân bổ lại missing weight: 70% cho semantic, 30% cho duration_fit
    effective_w_semantic = w_semantic + missing_weight * 0.70
    effective_w_duration_fit = w_duration_fit + missing_weight * 0.30

    base = effective_w_semantic * semantic_score + effective_w_duration_fit * duration_fit_score + w_ocr * ocr_score

    if visual_quality_score is not None:
        base += w_visual_quality * visual_quality_score

    if continuity_score is not None:
        base += w_continuity * continuity_score

    if diversity_score is not None:
        base += w_diversity * diversity_score

    # Neu co OCR score thi buff them rat nhieu vi no cuc ky chinh xac
    if ocr_score > 0:
        base += 0.3

    final = base - repetition_penalty - bad_clip_penalty
    return max(0.0, min(1.0, final))


def map_confidence(
    final_score: float,
    fallback_used: bool,
    *,
    threshold_high: float = 0.75,
    threshold_medium: float = 0.50,
) -> str:
    """Map final_score → confidence level (§7.8).

    if fallback_used:
        confidence = low
    elif final_score >= threshold_high:
        confidence = high
    elif final_score >= threshold_medium:
        confidence = medium
    else:
        confidence = low
    """
    if fallback_used:
        return "low"
    if final_score >= threshold_high:
        return "high"
    if final_score >= threshold_medium:
        return "medium"
    return "low"


def solve_dp_assignment(
    base_scores: list[dict[str, float]],
    repetition_penalty: float,
    clip_metadata: dict[str, dict] | None = None,
    continuity_weight: float = 0.20,
) -> list[str | None]:
    """Quy hoạch động tìm phương án gán clip-segment tối ưu toàn cục.

    Thay vì greedy (chọn clip tốt nhất từng segment rồi phạt trùng
    segment kế), DP xét **toàn bộ** cách gán và tìm chuỗi clip có
    tổng score cao nhất, đã tính phạt trùng lặp giữa mọi cặp segment
    liên tiếp.
    """
    n = len(base_scores)
    if n == 0:
        return []

    # Thu thập tất cả clip_id duy nhất, giữ thứ tự
    all_clips: list[str] = []
    clip_set: set[str] = set()
    for seg_scores in base_scores:
        for cid in seg_scores:
            if cid not in clip_set:
                all_clips.append(cid)
                clip_set.add(cid)

    if not all_clips:
        return [None] * n

    m = len(all_clips)
    clip_to_idx = {cid: idx for idx, cid in enumerate(all_clips)}

    NEG_INF = float("-inf")

    # dp[i][j] = tổng score tốt nhất cho segments 0..i, segment i dùng clip j
    # parent[i][j] = index clip đã chọn ở segment i-1 trong path tối ưu
    dp = [[NEG_INF] * m for _ in range(n)]
    parent = [[-1] * m for _ in range(n)]

    # --- Base case: segment 0 ---
    for j, cid in enumerate(all_clips):
        score = base_scores[0].get(cid, NEG_INF)
        if score != NEG_INF:
            dp[0][j] = score

    # --- Fill DP table ---
    for i in range(1, n):
        for j, cid_j in enumerate(all_clips):
            score_j = base_scores[i].get(cid_j, NEG_INF)
            if score_j == NEG_INF:
                continue  # clip j không khả dụng cho segment i

            best_val = NEG_INF
            best_k = -1
            for k, cid_k in enumerate(all_clips):
                if dp[i - 1][k] == NEG_INF:
                    continue
                
                penalty = repetition_penalty if j == k else 0.0
                
                # Continuity Bonus: neu clip j ngay sau clip k => bonus
                continuity_bonus = 0.0
                if clip_metadata and cid_j in clip_metadata and cid_k in clip_metadata:
                    clip_j_info = clip_metadata[cid_j]
                    clip_k_info = clip_metadata[cid_k]
                    # Check if they are from same video
                    if clip_j_info.get("source_path") == clip_k_info.get("source_path"):
                        end_k = clip_k_info.get("end", 0)
                        start_j = clip_j_info.get("start", 0)
                        # Neu khoang cach giua clip_k end va clip_j start < 1 giay, tuc la lien tiep
                        if 0 <= start_j - end_k <= 1.0:
                            continuity_bonus = continuity_weight
                            
                val = dp[i - 1][k] + score_j - penalty + continuity_bonus
                if val > best_val:
                    best_val = val
                    best_k = k

            dp[i][j] = best_val
            parent[i][j] = best_k

    # --- Backtrack: tìm clip tối ưu segment cuối ---
    best_last = -1
    best_total = NEG_INF
    for j in range(m):
        if dp[n - 1][j] > best_total:
            best_total = dp[n - 1][j]
            best_last = j

    if best_last == -1:
        return [None] * n

    # Truy vết ngược
    assignment_idx = [0] * n
    assignment_idx[n - 1] = best_last
    for i in range(n - 2, -1, -1):
        assignment_idx[i] = parent[i + 1][assignment_idx[i + 1]]

    # Chuyển index → clip_id
    result: list[str | None] = []
    for i in range(n):
        idx = assignment_idx[i]
        if idx >= 0 and dp[i][idx] != NEG_INF:
            result.append(all_clips[idx])
        else:
            result.append(None)

    return result
