"""FAISS visual index.

BAY 4 (quan trong nhat): thu tu insert vao index PHAI khop thu tu
visual_embeddings[] trong metadata. Row i cua index <-> visual_embeddings[i].
Stage 5 search ra row id -> tra visual_embeddings[id] -> clip_id.
Sai thu tu = Stage 5 tra SAI clip ma khong co loi nao bao ra.

Vector da L2-normalize -> dung IndexFlatIP (inner product) = cosine similarity.
"""

from __future__ import annotations
import os
import numpy as np


def build_and_save_index(vectors: list[np.ndarray], dimension: int, index_path: str) -> str:
    """vectors PHAI cung thu tu voi visual_embeddings[]. Tra ve index_path."""
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    matrix = np.vstack(vectors).astype("float32")  # shape [N, dim]
    assert matrix.shape[1] == dimension, f"dim mismatch {matrix.shape[1]} != {dimension}"

    try:
        import faiss
        index = faiss.IndexFlatIP(dimension)  # inner product; vector da normalize -> = cosine
        index.add(matrix)                     # row i = vectors[i] (giu nguyen thu tu)
        faiss.write_index(index, index_path)
    except ImportError:
        # Fallback: luu raw matrix .npy de Stage 5 tu tinh (vector_path van la nguon chinh)
        np.save(index_path + ".npy", matrix)
        print(f"[warn] faiss chua cai -> luu matrix tai {index_path}.npy thay the")
    return index_path
