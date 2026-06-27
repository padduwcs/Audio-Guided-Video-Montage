"""Test tuong duong batch: encode batch PHAI cho CUNG ket qua nhu encode tung cai.
Bat loi xao thu tu / logic sai trong batch implementation.
Chay duoc voi fake model — khong can torch/GPU.
"""

import numpy as np
import pytest
from PIL import Image

from embedding_indexer.model import load_backend


@pytest.fixture
def backend():
    return load_backend("clip-vit-base-patch32", 512, use_fake=True)


def test_batch_text_equals_loop(backend):
    texts = ["cong chinh", "khu trung bay", "khach tham quan"]
    one_by_one = [backend.encode_text(t) for t in texts]
    batched = backend.encode_texts(texts)

    assert len(batched) == len(one_by_one)
    for i, (b, o) in enumerate(zip(batched, one_by_one)):
        assert np.allclose(b, o, atol=1e-5), f"text batch khac loop tai index {i}"


def test_batch_image_equals_loop(tmp_path, backend):
    paths = []
    for i in range(3):
        p = str(tmp_path / f"img{i}.jpg")
        Image.new("RGB", (32, 32), (i * 40, 100, 150)).save(p)
        paths.append(p)

    one_by_one = [backend.encode_image(p) for p in paths]
    batched = backend.encode_images(paths)

    assert len(batched) == len(one_by_one)
    for i, (b, o) in enumerate(zip(batched, one_by_one)):
        assert np.allclose(b, o, atol=1e-5), f"image batch khac loop tai index {i}"


def test_batch_text_empty(backend):
    assert backend.encode_texts([]) == []


def test_batch_image_empty(backend):
    assert backend.encode_images([]) == []


def test_batch_text_single(backend):
    text = "test single"
    single = backend.encode_text(text)
    batched = backend.encode_texts([text])
    assert len(batched) == 1
    assert np.allclose(batched[0], single, atol=1e-5)


def test_batch_preserves_order(backend):
    texts = [f"text_{i}" for i in range(10)]
    one_by_one = [backend.encode_text(t) for t in texts]
    batched = backend.encode_texts(texts)
    for i in range(len(texts)):
        assert np.allclose(batched[i], one_by_one[i], atol=1e-5), f"order wrong at {i}"
