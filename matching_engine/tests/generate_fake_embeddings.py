"""Generate fake embedding .npy files for testing the matching engine.

Creates text and visual embedding vectors that simulate meaningful
cosine similarity patterns matching the sample data.
"""

import os
import numpy as np

np.random.seed(42)

DIM = 512
EMB_DIR = "data/intermediate/embeddings"
IDX_DIR = "data/intermediate/index"

os.makedirs(EMB_DIR, exist_ok=True)
os.makedirs(IDX_DIR, exist_ok=True)


def make_unit(seed: int) -> np.ndarray:
    """Make a deterministic unit vector."""
    rng = np.random.RandomState(seed)
    v = rng.randn(DIM).astype(np.float32)
    v /= np.linalg.norm(v)
    return v


def make_similar(base: np.ndarray, similarity: float) -> np.ndarray:
    """Make a vector with target cosine similarity to base."""
    rng = np.random.RandomState(int(abs(similarity * 1000)))
    noise = rng.randn(DIM).astype(np.float32)
    noise -= noise.dot(base) * base  # orthogonalize
    noise /= np.linalg.norm(noise)
    # v = similarity * base + sqrt(1 - sim^2) * noise
    v = similarity * base + np.sqrt(max(0, 1 - similarity ** 2)) * noise
    v /= np.linalg.norm(v)
    return v


# Text embeddings for 3 segments
# a001: "main entrance of tourist area"
# a002: "exhibition area with notable artifacts"
# a003: "visitors moving to the next experience area"
text_a001 = make_unit(1001)
text_a002 = make_unit(2002)
text_a003 = make_unit(3003)

np.save(os.path.join(EMB_DIR, "emb_text_a001.npy"), text_a001)
np.save(os.path.join(EMB_DIR, "emb_text_a002.npy"), text_a002)
np.save(os.path.join(EMB_DIR, "emb_text_a003.npy"), text_a003)

# Visual embeddings - designed to produce meaningful matching
# v01_c003: entrance scene -> high sim with a001
v01_c003_k01 = make_similar(text_a001, 0.78)
v01_c003_k02 = make_similar(text_a001, 0.82)
np.save(os.path.join(EMB_DIR, "emb_visual_v01_c003_k01.npy"), v01_c003_k01)
np.save(os.path.join(EMB_DIR, "emb_visual_v01_c003_k02.npy"), v01_c003_k02)

# v01_c004: exhibition/artifact -> high sim with a002
v01_c004_k01 = make_similar(text_a002, 0.75)
np.save(os.path.join(EMB_DIR, "emb_visual_v01_c004_k01.npy"), v01_c004_k01)

# v01_c005: visitors walking -> moderate sim with a003
v01_c005_k01 = make_similar(text_a003, 0.55)
np.save(os.path.join(EMB_DIR, "emb_visual_v01_c005_k01.npy"), v01_c005_k01)

# v02_c001: wide exhibition room -> moderate sim with a002
v02_c001_k01 = make_similar(text_a002, 0.70)
np.save(os.path.join(EMB_DIR, "emb_visual_v02_c001_k01.npy"), v02_c001_k01)

# v02_c002: experience area visitors -> moderate sim with a003
v02_c002_k01 = make_similar(text_a003, 0.50)
np.save(os.path.join(EMB_DIR, "emb_visual_v02_c002_k01.npy"), v02_c002_k01)

# v02_c003: crowd motion (low quality) -> low sim with all
v02_c003_k01 = make_similar(text_a003, 0.35)
np.save(os.path.join(EMB_DIR, "emb_visual_v02_c003_k01.npy"), v02_c003_k01)

# Build FAISS index — row order MUST match visual_embeddings[] in
# embedding_metadata_sample.json (same order as vectors below).
visual_vectors_ordered = [
    v01_c003_k01,
    v01_c003_k02,
    v01_c004_k01,
    v01_c005_k01,
    v02_c001_k01,
    v02_c002_k01,
    v02_c003_k01,
]

import faiss

matrix = np.vstack(visual_vectors_ordered).astype("float32")
index = faiss.IndexFlatIP(DIM)
index.add(matrix)
index_path = os.path.join(IDX_DIR, "visual.index")
faiss.write_index(index, index_path)

print(f"[ok] Generated fake embeddings in {EMB_DIR}/")
print(f"  - 3 text embeddings (a001, a002, a003)")
print(f"  - 7 visual embeddings (v01_c003 x2, v01_c004, v01_c005, v02_c001, v02_c002, v02_c003)")
print(f"  - FAISS index at {index_path} ({index.ntotal} vectors)")
