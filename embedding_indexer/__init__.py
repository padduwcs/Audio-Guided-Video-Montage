"""Stage 4 — Embedding Indexer.

Đọc audio_segments.json + clip_metadata.json, tạo text/visual embedding
trong cùng embedding space (CLIP), lưu vector + FAISS index,
xuất embedding_metadata.json đúng Data Contract.
"""

__version__ = "1.0"
