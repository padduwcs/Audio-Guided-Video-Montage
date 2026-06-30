# Embedding Indexer

Stage 4 tao embedding text/visual trong cung khong gian vector va xuat metadata
cho Matching Engine.

## Input

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/keyframes/*.jpg
```

## Output

```text
data/intermediate/embedding_metadata.json
data/intermediate/embedding_indexing_log.json
data/intermediate/embeddings/*.npy
data/intermediate/index/*
```

## Chay Doc Lap

Fake backend, phu hop smoke test nhanh:

```powershell
python -m embedding_indexer.main --audio-segments data/intermediate/audio_segments.json --clip-metadata data/intermediate/clip_metadata.json --output-dir data/intermediate --embedding-dir data/intermediate/embeddings --index-dir data/intermediate/index --fake --overwrite
```

Backend CLIP that:

```powershell
python -m embedding_indexer.main --audio-segments data/intermediate/audio_segments.json --clip-metadata data/intermediate/clip_metadata.json --output-dir data/intermediate --embedding-dir data/intermediate/embeddings --index-dir data/intermediate/index --overwrite
```

## Ghi Chu

- Fake backend khong can `torch`/`transformers` va du de test pipeline.
- CLIP that can dependency trong `requirements.txt` hoac `requirements-dev.txt`.
- Text source uu tien `translated_query` neu co, fallback ve `query`.
- Chi embed clip co status `usable` hoac `low_quality`.

## Test / Validation

```powershell
python -m integration.run_pipeline --from-stage 4 --to-stage 4 --fake-embeddings --overwrite
python scripts/validate_json.py --input-dir data/intermediate
```

## Tai Lieu

- `docs/details/06_stage_4_embedding_indexing.md`
- `docs/details/02_data_contract.md`
- `docs/schemas/embedding_metadata.schema.md`
- `docs/samples/embedding_metadata_sample.json`
