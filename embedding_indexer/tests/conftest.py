"""Fixtures dung chung: dung dataset nho + chay pipeline (fake model) 1 lan."""

import json
import os
import sys
import numpy as np
import pytest
from PIL import Image

# Cho phep import embedding_indexer khi chay pytest tu bat ky dau
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from embedding_indexer.main import run
from embedding_indexer import io_utils as io


AUDIO_SEGMENTS = {
    "schema_version": "1.0",
    "project_id": "test_pr",
    "audio_id": "audio_01",
    "language": "vi",
    "items": [
        {"segment_id": "a001", "start": 0.0, "end": 5.0, "duration": 5.0,
         "text": "cong chinh", "query": "cong chinh khu tham quan",
         "translated_query": "main entrance of tourist area"},
        {"segment_id": "a002", "start": 5.0, "end": 10.0, "duration": 5.0,
         "text": "khu trung bay", "query": "khu trung bay hien vat",
         "translated_query": "exhibition area with artifacts"},
    ],
}

CLIP_METADATA = {
    "schema_version": "1.0",
    "project_id": "test_pr",
    "items": [
        # usable, 2 keyframe
        {"clip_id": "v01_c001", "video_id": "video_01", "status": "usable",
         "keyframes": [
             {"keyframe_id": "v01_c001_k01", "path": "kf/v01_c001_k01.jpg"},
             {"keyframe_id": "v01_c001_k02", "path": "kf/v01_c001_k02.jpg"},
         ]},
        # low_quality van embed
        {"clip_id": "v02_c001", "video_id": "video_02", "status": "low_quality",
         "keyframes": [{"keyframe_id": "v02_c001_k01", "path": "kf/v02_c001_k01.jpg"}]},
        # error -> phai bi bo qua
        {"clip_id": "v02_c099", "video_id": "video_02", "status": "error",
         "keyframes": [{"keyframe_id": "v02_c099_k01", "path": "kf/v02_c099_k01.jpg"}]},
    ],
}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Tao thu muc lam viec tam + input + keyframe gia, chuyen cwd vao do."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("in", exist_ok=True)
    os.makedirs("kf", exist_ok=True)

    # Tao keyframe gia cho moi keyframe duoc tham chieu
    for c in CLIP_METADATA["items"]:
        for kf in c["keyframes"]:
            Image.new("RGB", (32, 32), (120, 120, 120)).save(kf["path"])

    audio_path = "in/audio_segments.json"
    clip_path = "in/clip_metadata.json"
    json.dump(AUDIO_SEGMENTS, open(audio_path, "w"))
    json.dump(CLIP_METADATA, open(clip_path, "w"))

    return {"audio": audio_path, "clip": clip_path, "root": str(tmp_path)}


@pytest.fixture
def result(workspace):
    """Chay pipeline 1 lan voi fake model, tra ve metadata da load."""
    meta_path = run(
        audio_segments_path=workspace["audio"],
        clip_metadata_path=workspace["clip"],
        output_dir="out",
        embedding_dir="out/embeddings",
        index_dir="out/index",
        use_fake=True,
    )
    return {"meta_path": meta_path, "meta": json.load(open(meta_path)), "ws": workspace}
