"""Tang 4 - Kiem tra NGU NGHIA cua embedding (chay voi CLIP that).

Y tuong: voi moi audio segment, clip dung nghia phai co similarity cao hon
clip sai nghia. Neu thu tu nay dung -> embedding space hoat dong.

Day la kiem tra QUAN TRONG NHAT cua Stage 4 - cau truc dung khong dam bao
ngu nghia dung. Chi co the kiem bang CLIP that, KHONG dung --fake.

Cach dung:
    python validate_semantic.py \
        --metadata data/intermediate/embedding_metadata.json \
        --audio-segments data/intermediate/audio_segments.json \
        --clip-metadata data/intermediate/clip_metadata.json
"""

from __future__ import annotations
import argparse
import json
import numpy as np


def load_vec(path: str) -> np.ndarray:
    return np.load(path)


def build_clip_matrix(metadata: dict, clip_ids: list[str]) -> dict[str, np.ndarray]:
    clip_vecs: dict[str, list[np.ndarray]] = {}
    for e in metadata["visual_embeddings"]:
        cid = e["clip_id"]
        if cid not in clip_vecs:
            clip_vecs[cid] = []
        clip_vecs[cid].append(load_vec(e["vector_path"]))
    return {cid: np.vstack(vs) for cid, vs in clip_vecs.items() if vs}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--metadata", required=True)
    p.add_argument("--audio-segments", required=True)
    p.add_argument("--clip-metadata", required=True)
    args = p.parse_args()

    meta = json.load(open(args.metadata, encoding="utf-8"))
    seg = json.load(open(args.audio_segments, encoding="utf-8"))
    clip = json.load(open(args.clip_metadata, encoding="utf-8"))

    text_vec = {e["segment_id"]: load_vec(e["vector_path"])
                for e in meta["text_embeddings"]}

    caption = {c["clip_id"]: c.get("caption", "") for c in clip["items"]}
    all_clip_ids = [c["clip_id"] for c in clip["items"]]

    clip_matrices = build_clip_matrix(meta, all_clip_ids)
    valid_clip_ids = [cid for cid in all_clip_ids if cid in clip_matrices]

    print("=== KIEM TRA NGU NGHIA: moi segment xep hang cac clip theo similarity ===\n")
    for s in seg["items"]:
        sid = s["segment_id"]
        if sid not in text_vec:
            continue
        tv = text_vec[sid]
        scored = []
        for cid in valid_clip_ids:
            sim = float(np.max(clip_matrices[cid] @ tv))
            scored.append((sim, cid))
        scored.sort(reverse=True)

        print(f"[{sid}] query: {s.get('query')}")
        for rank, (sim, cid) in enumerate(scored, 1):
            mark = "  <-- TOP" if rank == 1 else ""
            print(f"   {rank}. {sim:+.3f}  {cid:12s} \"{caption[cid]}\"{mark}")
        print()

    print("DANH GIA: nhin TOP cua moi segment - clip co caption dung nghia")
    print("phai dung dau. Neu loan -> embedding space co van de.")


if __name__ == "__main__":
    main()
