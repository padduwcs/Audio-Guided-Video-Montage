# embedding_indexer/ — Stage 4: Embedding Indexing

Biến **text** (audio segment query) và **ảnh** (clip keyframe) thành **vector trong cùng
embedding space** (CLIP), lưu vector + FAISS index, xuất `embedding_metadata.json` cho Stage 5.

## Cài đặt

```bash
# Production (CLIP thật):
pip install torch transformers pillow numpy faiss-cpu

# Tối thiểu (test bằng fake model, không cần torch):
pip install numpy pillow
```

## Chạy

```bash
# Thật:
python -m embedding_indexer.main \
  --audio-segments data/intermediate/audio_segments.json \
  --clip-metadata  data/intermediate/clip_metadata.json \
  --output-dir     data/intermediate \
  --embedding-dir  data/intermediate/embeddings \
  --index-dir      data/intermediate/index

# Test pipeline không cần GPU/torch:
python -m embedding_indexer.main ... --fake

# Chạy lại (ghi đè):
python -m embedding_indexer.main ... --overwrite
```

## Input / Output

| | File |
|---|---|
| Đọc | `audio_segments.json` (Stage 2), `clip_metadata.json` (Stage 3), ảnh keyframe |
| Ghi | `embedding_metadata.json`, `embeddings/*.npy`, `index/visual.index`, log |


## Quy tắc chọn `source_text`

- Có `translated_query` và `prefer_translated_query=true` → dùng bản tiếng Anh (CLIP gốc mạnh tiếng Anh).
- Không có → fallback `query`.
- Không bao giờ tự bịa text.

## Chỉ embed clip `usable` / `low_quality`. Bỏ `too_short` / `error`.

## File

| File | Vai trò |
|---|---|
| `main.py` | Orchestrate 11 bước + CLI |
| `config.py` | Config + default MVP |
| `io_utils.py` | Load/validate input, chọn source_text, ghi output |
| `model.py` | Wrap CLIP (+ FakeBackend để test) |
| `indexer.py` | Build FAISS index |
