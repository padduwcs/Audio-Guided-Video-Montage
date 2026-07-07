"""Stage 4 entry point.

Luong (theo stage spec §7):
  1. Load + validate input, check project_id khop
  2. Chon source_text moi segment
  3. Loc clip/keyframe hop le
  4. Load model multimodal
  5. Tao text embedding
  6. Tao visual embedding (theo keyframe)
  7. Luu vector files (.npy)
  8. Build FAISS index (thu tu = visual_embeddings[])
  9. (normalize da lam trong model)
  10. Sinh embedding_id on dinh
  11. Ghi embedding_metadata.json + log
"""

from __future__ import annotations
import argparse
import os
from datetime import datetime, timezone

import numpy as np

from . import io_utils as io
from .config import load_config
from .model import load_backend
from .indexer import build_and_save_index


def _try_load_cached(vec_path: str, dim: int) -> np.ndarray | None:
    if not os.path.exists(vec_path):
        return None
    try:
        vec = np.load(vec_path)
        if vec.shape == (dim,):
            return vec
    except Exception:
        pass
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(
    audio_segments_path: str,
    clip_metadata_path: str,
    output_dir: str,
    embedding_dir: str,
    index_dir: str,
    config_path: str | None = None,
    overwrite: bool = False,
    use_fake: bool = False,
    device: str = "cpu",
) -> str:
    cfg = load_config(
        config_path,
        audio_segments_path=audio_segments_path,
        clip_metadata_path=clip_metadata_path,
        output_dir=output_dir,
        embedding_dir=embedding_dir,
        index_dir=index_dir,
    )

    metadata_path = os.path.join(output_dir, "embedding_metadata.json")
    log_path = os.path.join(output_dir, "embedding_indexing_log.json")

    # Re-run guard (§8.4)
    if os.path.exists(metadata_path) and not overwrite:
        raise io.InputError(
            f"Output da ton tai: {metadata_path}. Dung --overwrite de ghi de."
        )

    log: dict = {"warnings": [], "skipped_clips": [], "errors": []}

    # --- Buoc 1: load + validate ---
    audio = io.load_audio_segments(audio_segments_path)
    clip = io.load_clip_metadata(clip_metadata_path)
    project_id = io.check_project_id(audio, clip)

    # --- Buoc 4: load model (lam som de fail-fast neu model loi) ---
    backend = load_backend(cfg.model_name, cfg.dimension, use_fake=use_fake, device=device)
    dim = backend.dimension

    os.makedirs(embedding_dir, exist_ok=True)
    os.makedirs(index_dir, exist_ok=True)

    def rel(path: str) -> str:
        return os.path.relpath(path, start=os.getcwd())

    # --- Buoc 2 + 5: text embeddings (A1: batch, D3: dedup, C1: cache) ---
    text_embeddings = []
    seg_texts: list[tuple[str, str]] = []
    for seg in audio["items"]:
        seg_id = seg["segment_id"]
        source_text = io.select_source_text(
            seg, cfg.prefer_translated, cfg.fallback_to_query
        )
        seg_texts.append((seg_id, source_text))

    unique_texts = list(dict.fromkeys(t for _, t in seg_texts))
    _text_vec: dict[str, np.ndarray] = {}
    texts_to_encode: list[str] = []
    text_to_first_seg: dict[str, str] = {}
    for seg_id, source_text in seg_texts:
        if source_text not in text_to_first_seg:
            text_to_first_seg[source_text] = seg_id
    for t in unique_texts:
        vec_path = os.path.join(embedding_dir, f"emb_text_{text_to_first_seg[t]}.npy")
        cached = _try_load_cached(vec_path, dim) if overwrite else None
        if cached is not None:
            _text_vec[t] = cached
        else:
            texts_to_encode.append(t)
    if texts_to_encode:
        encoded = backend.encode_texts(texts_to_encode)
        for t, v in zip(texts_to_encode, encoded):
            _text_vec[t] = v

    for seg_id, source_text in seg_texts:
        vec = _text_vec[source_text]
        if vec.shape[0] != dim:
            log["errors"].append(f"Text {seg_id} sai dimension")
            continue
        vec_path = os.path.join(embedding_dir, f"emb_text_{seg_id}.npy")
        np.save(vec_path, vec)
        text_embeddings.append({
            "embedding_id": f"emb_text_{seg_id}",
            "segment_id": seg_id,
            "source_text": source_text,
            "vector_path": rel(vec_path),
        })

    if not text_embeddings:
        raise io.InputError("Khong tao duoc text embedding nao")

    # --- Buoc 3 + 6: visual embeddings (A1: batch, D3: dedup, C1: cache) ---
    visual_embeddings = []
    visual_vectors = []

    kf_items: list[tuple[str, dict]] = []
    for clip_id, kf in io.iter_embeddable_keyframes(clip, log):
        kf_items.append((clip_id, kf))

    unique_paths = list(dict.fromkeys(kf["path"] for _, kf in kf_items))
    _img_vec: dict[str, np.ndarray | None] = {}
    paths_to_encode: list[str] = []
    path_to_first_kf: dict[str, str] = {}
    for _, kf in kf_items:
        p = kf["path"]
        if p not in path_to_first_kf:
            path_to_first_kf[p] = kf["keyframe_id"]
    for p in unique_paths:
        vec_path = os.path.join(embedding_dir, f"emb_visual_{path_to_first_kf[p]}.npy")
        cached = _try_load_cached(vec_path, dim) if overwrite else None
        if cached is not None:
            _img_vec[p] = cached
        else:
            paths_to_encode.append(p)
    if paths_to_encode:
        try:
            encoded = backend.encode_images(paths_to_encode)
            for p, v in zip(paths_to_encode, encoded):
                _img_vec[p] = v
        except Exception as e:
            log["errors"].append(f"Batch encode images loi: {e}")
            for p in paths_to_encode:
                try:
                    _img_vec[p] = backend.encode_image(p)
                except Exception as e2:
                    log["errors"].append(f"Encode loi keyframe path {p}: {e2}")
                    _img_vec[p] = None

    for clip_id, kf in kf_items:
        kf_id = kf["keyframe_id"]
        vec = _img_vec.get(kf["path"])
        if vec is None:
            log["errors"].append(f"Encode loi keyframe {kf_id}")
            continue
        if vec.shape[0] != dim:
            log["errors"].append(f"Visual {kf_id} sai dimension")
            continue
        vec_path = os.path.join(embedding_dir, f"emb_visual_{kf_id}.npy")
        np.save(vec_path, vec)
        visual_embeddings.append({
            "embedding_id": f"emb_visual_{kf_id}",
            "clip_id": clip_id,
            "keyframe_id": kf_id,
            "vector_path": rel(vec_path),
        })
        visual_vectors.append(vec)

    if not visual_embeddings:
        raise io.InputError("Khong tao duoc visual embedding nao -> matching khong chay")

    # --- Buoc 8: build index (thu tu khop visual_embeddings[]) ---
    index_obj: dict = {}
    if cfg.index_enabled:
        index_path = os.path.join(index_dir, "visual.index")
        build_and_save_index(visual_vectors, dim, index_path)
        index_obj = {"type": cfg.raw["index"]["type"], "path": rel(index_path)}

    # --- Buoc 11: ghi metadata ---
    metadata = {
        "schema_version": "1.0",
        "project_id": project_id,
        "model": {
            "name": cfg.model_name,
            "type": cfg.raw["model"]["type"],
            "dimension": dim,            # dimension THAT
        },
        "created_at": _now_iso(),
        "text_embeddings": text_embeddings,
        "visual_embeddings": visual_embeddings,
        "index": index_obj,
    }
    io.write_json(metadata_path, metadata)

    log["summary"] = {
        "text_count": len(text_embeddings),
        "visual_count": len(visual_embeddings),
        "model": cfg.model_name,
        "dimension": dim,
        "normalized": cfg.normalize,
        "index_type": index_obj.get("type"),
    }
    io.write_json(log_path, log)

    print(f"[ok] {len(text_embeddings)} text + {len(visual_embeddings)} visual embeddings")
    print(f"[ok] {metadata_path}")
    return metadata_path


def main():
    p = argparse.ArgumentParser(description="Stage 4 — Embedding Indexer")
    p.add_argument("--audio-segments", required=True)
    p.add_argument("--clip-metadata", required=True)
    p.add_argument("--output-dir", default="data/intermediate")
    p.add_argument("--embedding-dir", default="data/intermediate/embeddings")
    p.add_argument("--index-dir", default="data/intermediate/index")
    p.add_argument("--config", default=None)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--fake", action="store_true", help="Dung fake model de test pipeline")
    p.add_argument("--device", default="cpu", help="Embedding device for real CLIP backend: cpu, cuda, or auto")
    args = p.parse_args()

    try:
        run(
            audio_segments_path=args.audio_segments,
            clip_metadata_path=args.clip_metadata,
            output_dir=args.output_dir,
            embedding_dir=args.embedding_dir,
            index_dir=args.index_dir,
            config_path=args.config,
            overwrite=args.overwrite,
            use_fake=args.fake,
            device=args.device,
        )
    except io.InputError as e:
        print(f"[INPUT ERROR] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
