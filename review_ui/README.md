# Review UI (Stage 7)

Module Stage 7 — review và chỉnh timeline trước khi render.

## Trách nhiệm

- Hiển thị segment, transcript, clip đang chọn, score, confidence và top-k candidate.
- Cho phép đổi clip và chỉnh tham số timeline được phép.
- Ghi đè `timeline.json` (cập nhật `updated_at`).
- Không render video, không sửa schema timeline.
- Không sửa `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json`.
- Không chạy lại ASR, video analysis, embedding hoặc matching.

## Cấu trúc thư mục/module

```
review_ui/
├── __init__.py
├── cli.py                # CLI entrypoint
├── loader.py             # Load & index 5 JSON, fail-fast validation
├── validator.py          # Validate schema, cross-file, renderer-readiness
├── editor.py             # Transaction chỉnh timeline (replace clip, timing, mark reviewed)
├── storage.py            # Atomic save, backup, log
├── media.py              # Resolve preview path
└── tests/
    ├── test_loader.py
    ├── test_validator.py
    ├── test_editor.py
    ├── test_storage.py
    └── test_media.py
```

## Dữ liệu vào

```
data/intermediate/timeline.json
data/intermediate/matching_candidates.json
data/intermediate/clip_metadata.json
data/intermediate/audio_segments.json
data/intermediate/media_metadata.json
```

Media preview: voice-over từ `media_metadata.audio.normalized_path`; video từ `visual_items[].source_path`.

## Dữ liệu ra

```
data/intermediate/timeline.json
data/intermediate/review_ui_log.json          (optional)
data/intermediate/timeline.before_review.json (backup, optional)
```

MVP ghi đè `timeline.json` tại cùng path.

## Hướng dẫn chạy CLI

```
python -m review_ui.cli \
  --project-id demo_01 \
  --timeline data/intermediate/timeline.json \
  --matching-candidates data/intermediate/matching_candidates.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --audio-segments data/intermediate/audio_segments.json \
  --media-metadata data/intermediate/media_metadata.json \
  --host 127.0.0.1 \
  --port 7860
```

- Tham số `--readonly` để mở ở chế độ chỉ xem.
- Tham số `--no-backup` để không tạo backup timeline.before_review.json.
- Tham số `--log-path` để ghi log review_ui_log.json nếu cần.

## Hướng dẫn test

- Chạy toàn bộ test:
  ```
  pytest review_ui/tests/
  ```
- Dummy test đã có cho từng module, bổ sung test thực tế khi phát triển.

## Validate timeline sau chỉnh

- Sử dụng script validate:
  ```
  python scripts/validate_json.py --input-dir data/intermediate
  ```

## Tài liệu tham chiếu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/09_stage_7_review_ui.md`
- Schema: `docs/schemas/timeline.schema.md`
- Mẫu: `docs/samples/timeline_sample.json` và các sample liên quan trong `docs/samples/`

## Nguyên tắc tuân thủ

- Chỉ chỉnh các field cho phép trong timeline.json, preserve optional fields không hiểu.
- Không sửa upstream file: matching_candidates, clip_metadata, audio_segments, media_metadata.
- Save timeline phải atomic, cập nhật updated_at, backup nếu cần.
- Không đổi schema, không đổi project_id/audio_id/created_at/schema_version.
- Validate fail-fast khi load, chặn save nếu có error contract.
- UI chỉ là review/chỉnh timeline, không phải editor phim đầy đủ.

## TODO & phạm vi MVP

- [x] Skeleton code, test dummy cho từng module
- [ ] Implement loader, validator, editor, storage, media logic
- [ ] Implement CLI argument parsing, app startup
- [ ] Implement UI MVP (segment list, candidate list, preview, inspector)
- [ ] Implement validation, dirty state, readonly mode
- [ ] Manual test T01–T12 theo stage spec

## Ranh giới

- Không render video, không sửa schema timeline.
- Không sửa `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json`.
- Không chạy lại ASR, video analysis, embedding hoặc matching.