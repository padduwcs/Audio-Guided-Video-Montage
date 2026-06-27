"""Test Tang 1-3: cau truc, mapping, bat bien noi bo.
Chay duoc voi fake model -> nhanh, khong can torch.

    pytest embedding_indexer/tests/ -v
"""

import json
import os
import numpy as np
import pytest

from embedding_indexer.main import run
from embedding_indexer import io_utils as io


# ---------- TANG 1: CAU TRUC (output khop contract) ----------

def test_top_level_fields(result):
    meta = result["meta"]
    need = {"schema_version", "project_id", "model",
            "created_at", "text_embeddings", "visual_embeddings", "index"}
    assert need <= set(meta)


def test_model_object(result):
    assert {"name", "type", "dimension"} <= set(result["meta"]["model"])


def test_embeddings_not_empty(result):
    assert len(result["meta"]["text_embeddings"]) > 0
    assert len(result["meta"]["visual_embeddings"]) > 0


def test_embedding_ids_unique(result):
    meta = result["meta"]
    ids = [e["embedding_id"] for e in meta["text_embeddings"] + meta["visual_embeddings"]]
    assert len(ids) == len(set(ids))


def test_vector_paths_exist_and_right_dim(result):
    meta = result["meta"]
    dim = meta["model"]["dimension"]
    for e in meta["text_embeddings"] + meta["visual_embeddings"]:
        assert os.path.exists(e["vector_path"]), f"thieu {e['vector_path']}"
        assert np.load(e["vector_path"]).shape[0] == dim


def test_paths_are_relative(result):
    meta = result["meta"]
    for e in meta["text_embeddings"] + meta["visual_embeddings"]:
        assert not e["vector_path"].startswith("/"), "khong duoc absolute path"


def test_vector_not_in_json(result):
    """BAY 2: vector KHONG nam trong JSON, chi co path."""
    for e in result["meta"]["text_embeddings"]:
        assert "vector" not in e
        assert "vector_path" in e


# ---------- TANG 2: MAPPING (ID khop, loc dung) ----------

def test_text_maps_to_real_segments(result):
    seg = json.load(open(result["ws"]["audio"]))
    seg_ids = {s["segment_id"] for s in seg["items"]}
    for e in result["meta"]["text_embeddings"]:
        assert e["segment_id"] in seg_ids


def test_every_segment_covered(result):
    seg = json.load(open(result["ws"]["audio"]))
    seg_ids = {s["segment_id"] for s in seg["items"]}
    covered = {e["segment_id"] for e in result["meta"]["text_embeddings"]}
    assert seg_ids == covered, "co segment bi bo sot"


def test_visual_maps_to_real_keyframes(result):
    clip = json.load(open(result["ws"]["clip"]))
    kf_ids = {kf["keyframe_id"] for c in clip["items"] for kf in c["keyframes"]}
    for e in result["meta"]["visual_embeddings"]:
        assert e["keyframe_id"] in kf_ids


def test_error_clips_skipped(result):
    """Clip status=error KHONG duoc embed."""
    embedded = {e["clip_id"] for e in result["meta"]["visual_embeddings"]}
    assert "v02_c099" not in embedded, "clip error bi embed nham"


def test_low_quality_clips_included(result):
    """Clip low_quality VAN duoc embed."""
    embedded = {e["clip_id"] for e in result["meta"]["visual_embeddings"]}
    assert "v02_c001" in embedded


def test_visual_count_matches(result):
    """2 (v01_c001) + 1 (v02_c001) = 3 keyframe usable. v02_c099 bi bo."""
    assert len(result["meta"]["visual_embeddings"]) == 3


# ---------- TANG 3: BAT BIEN (4 bay) ----------

def test_trap1_same_dimension(result):
    """BAY 1: text & visual cung so chieu (dieu kien can de cung space)."""
    meta = result["meta"]
    dt = np.load(meta["text_embeddings"][0]["vector_path"]).shape[0]
    dv = np.load(meta["visual_embeddings"][0]["vector_path"]).shape[0]
    assert dt == dv


def test_trap3_all_normalized(result):
    """BAY 3: moi vector da L2-normalize (norm = 1)."""
    meta = result["meta"]
    for e in meta["text_embeddings"] + meta["visual_embeddings"]:
        norm = float(np.linalg.norm(np.load(e["vector_path"])))
        assert abs(norm - 1.0) < 1e-4, f"{e['embedding_id']} norm={norm}"


def test_trap4_index_order_matches(result):
    """BAY 4: thu tu row trong index == thu tu visual_embeddings[]."""
    meta = result["meta"]
    idx_path = meta["index"]["path"]
    # fake/no-faiss luu .npy; faiss that luu .index
    mat_path = idx_path + ".npy" if os.path.exists(idx_path + ".npy") else None
    if mat_path is None:
        pytest.skip("faiss index nhi phan - bo qua kiem thu tu o test nay")
    mat = np.load(mat_path)
    assert mat.shape[0] == len(meta["visual_embeddings"])
    for i, e in enumerate(meta["visual_embeddings"]):
        assert np.allclose(mat[i], np.load(e["vector_path"])), f"sai thu tu row {i}"


# ---------- DETERMINISM ----------

def test_deterministic(workspace):
    """Cung input -> cung vector (chay 2 lan, so sanh)."""
    run(workspace["audio"], workspace["clip"], "o1", "o1/emb", "o1/idx", use_fake=True)
    run(workspace["audio"], workspace["clip"], "o2", "o2/emb", "o2/idx", use_fake=True)
    m1 = json.load(open("o1/embedding_metadata.json"))
    m2 = json.load(open("o2/embedding_metadata.json"))
    for e1, e2 in zip(m1["text_embeddings"], m2["text_embeddings"]):
        assert np.allclose(np.load(e1["vector_path"]), np.load(e2["vector_path"]))


# ---------- EDGE CASES (fail-fast) ----------

def test_project_id_mismatch_fails(workspace):
    """project_id 2 file khac nhau -> dung."""
    clip = json.load(open(workspace["clip"]))
    clip["project_id"] = "khac_hoan_toan"
    json.dump(clip, open(workspace["clip"], "w"))
    with pytest.raises(io.InputError, match="project_id"):
        run(workspace["audio"], workspace["clip"], "o", "o/e", "o/i", use_fake=True)


def test_rerun_without_overwrite_fails(workspace):
    """Chay lai khong --overwrite -> dung an toan."""
    run(workspace["audio"], workspace["clip"], "out", "out/e", "out/i", use_fake=True)
    with pytest.raises(io.InputError, match="da ton tai"):
        run(workspace["audio"], workspace["clip"], "out", "out/e", "out/i", use_fake=True)


def test_overwrite_succeeds(workspace):
    """Co --overwrite -> ghi de OK."""
    run(workspace["audio"], workspace["clip"], "out", "out/e", "out/i", use_fake=True)
    p = run(workspace["audio"], workspace["clip"], "out", "out/e", "out/i",
            use_fake=True, overwrite=True)
    assert os.path.exists(p)


def test_missing_query_fails(workspace):
    """Segment thieu query -> dung (validate input)."""
    seg = json.load(open(workspace["audio"]))
    del seg["items"][0]["query"]
    json.dump(seg, open(workspace["audio"], "w"))
    with pytest.raises(io.InputError, match="query"):
        run(workspace["audio"], workspace["clip"], "o", "o/e", "o/i", use_fake=True)


def test_prefer_translated_query(result):
    """source_text dung translated_query (tieng Anh) khi co."""
    a001 = next(e for e in result["meta"]["text_embeddings"]
                if e["segment_id"] == "a001")
    assert a001["source_text"] == "main entrance of tourist area"
