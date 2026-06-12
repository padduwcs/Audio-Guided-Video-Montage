# 06. Stage 4 — Embedding Indexing

| Module | `embedding_indexer/` |
| Core docs | [00](00_project_scope.md) · [01](01_system_architecture.md) · [02](02_data_contract.md) |
| Schema/Sample | [docs/schemas/embedding_metadata.schema.md](../schemas/embedding_metadata.schema.md) · [docs/samples/embedding_metadata_sample.json](../samples/embedding_metadata_sample.json) |

## 1. Mục tiêu stage

Stage 4 — Embedding Indexing tạo embedding cho audio segment và clip/keyframe, lưu vector hoặc index tìm kiếm, đồng thời tạo `embedding_metadata.json` để Matching Engine biết cách map giữa segment, clip, keyframe và embedding tương ứng.

Stage này là cầu nối giữa dữ liệu text và hình ảnh. Audio Analyzer tạo `query` cho từng audio segment; Video Analyzer tạo clip candidate và keyframe. Embedding Indexer biến các dữ liệu đó thành vector trong cùng embedding space để Matching Engine so sánh mức độ gần nghĩa.

Mục tiêu chính:

* Đọc `audio_segments.json` và `clip_metadata.json`.
* Đọc keyframe image files từ `clip_metadata.json`.
* Chọn `source_text` để tạo text embedding cho từng audio segment.
* Tạo text embedding và visual embedding (theo keyframe trong MVP).
* Lưu vector ra file riêng hoặc index riêng — không nhét vector lớn trực tiếp vào JSON.
* Tạo visual index (FAISS hoặc tương đương) nếu config bật.
* Sinh `embedding_id` ổn định.
* Xuất `embedding_metadata.json` đúng Data Contract hiện hành.
* Xuất log phụ để debug model, vector, index và mapping nếu cần.

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① ──► ② ─┐
           ├──► ④ ──► ⑤ ──► ⑥ ──► ⑦ ──► ⑧
       ③ ─┘
           ▲
      Stage này (hợp nhất ② + ③)

  ── Chi tiết Stage ④ ─────────────────────────────────────

  ② Audio Analyzer          ③ Video Analyzer
        │                         │
        │ audio_segments.json     │ clip_metadata.json
        │                         │ keyframes/*.jpg
        └───────────┬─────────────┘
                    ▼
         ┌─────────────────────────────┐
         │  ④ Embedding Indexer        │  ◄── bạn ở đây
         └─────────────┬───────────────┘
                       │ ghi
                       ├─ embedding_metadata.json
                       ├─ embeddings/*.npy
                       ├─ index/visual.index
                       └─ embedding_indexing_log.json
                       │
                       ▼
                 ⑤ Matching Engine
```

| | |
|---|---|
| **Đọc (IN)** | `audio_segments.json`, `clip_metadata.json`, keyframe images |
| **Ghi (OUT)** | `embedding_metadata.json`, vector files, visual index, log |
| **Downstream** | Stage ⑤ đọc embedding metadata + vector/index |

Cần **cả** output Stage ② và ③ — không chạy khi thiếu một trong hai. Chi tiết: [01 §4.4](01_system_architecture.md#44-embedding-indexer).

## 3. Trách nhiệm

### 3.1. Làm

1. Đọc `audio_segments.json` và `clip_metadata.json`.
2. Validate `project_id` khớp giữa hai file.
3. Validate segment có `segment_id` và text/query hợp lệ.
4. Validate clip/keyframe có `clip_id`, `keyframe_id`, `path` hợp lệ.
5. Lọc clip theo `status` trước khi tạo visual embedding.
6. Chọn `source_text` và tạo text embedding cho từng audio segment hợp lệ.
7. Tạo visual embedding cho từng keyframe hợp lệ.
8. Lưu vector files; tạo visual index nếu config yêu cầu.
9. Sinh `embedding_id` ổn định; ghi mapping vào `embedding_metadata.json`.
10. Xuất `embedding_indexing_log.json` để debug nếu cần.

### 3.2. Không làm

* Không chạy ASR, không sửa transcript, không tạo audio segment.
* Không detect scene/shot, không trích keyframe mới nếu keyframe thiếu.
* Không tính quality score cho clip, không chọn top-k, không tính matching score.
* Không tạo `matching_candidates.json`, `timeline.json`; không render video cuối.

Nếu keyframe thiếu hoặc lỗi, Stage 4 chỉ báo lỗi hoặc bỏ qua item theo rule rõ ràng — không tự phân tích lại video thay cho Stage 3.

## 4. Input cần đọc

### 4.1. Files

| File | Nguồn | Mục đích |
| ---- | ----- | -------- |
| `data/intermediate/audio_segments.json` | Stage 2 | `segment_id`, `query`, `translated_query` |
| `data/intermediate/clip_metadata.json` | Stage 3 | `clip_id`, `status`, `keyframes[*].path` |
| Keyframe images | `clip_metadata.json → items[*].keyframes[*].path` | Visual embedding input |

Không hard-code keyframe path ngoài metadata. Quy ước path: [02 §2.6](02_data_contract.md#26-path).

### 4.2. Fail-fast

**`audio_segments.json`:** parse được; có `schema_version`, `project_id`, `items` không rỗng; mỗi segment có `segment_id`, `query` không rỗng; nếu dùng `translated_query`, field là string không rỗng hoặc `null`.

**`clip_metadata.json`:** parse được; có `schema_version`, `project_id`, `items` không rỗng; mỗi clip có `clip_id`; clip usable có ≥ 1 keyframe; mỗi keyframe có `keyframe_id`, `timestamp`, `path`; file keyframe tồn tại.

**`project_id`** trong hai file phải giống nhau — không khớp → dừng pipeline.

### 4.3. Clip được tạo embedding

Trong MVP, tạo visual embedding cho clip có:

```text
status = usable
status = low_quality
```

Không tạo embedding cho:

```text
status = too_short
status = error
```

| `status` | Lý do |
| -------- | ----- |
| `usable` | Clip chính để matching |
| `low_quality` | Vẫn có thể dùng nếu thiếu footage; Matching Engine áp dụng penalty |
| `too_short` | Khó dùng trong timeline MVP |
| `error` | Không đủ tin cậy để đưa vào matching |

Nếu `status` thiếu (dữ liệu cũ): clip có keyframe hợp lệ + timestamp hợp lệ → xử lý như usable tạm thời; ghi warning trong log; nên yêu cầu Stage 3 cập nhật `status`.

### 4.4. Config nội bộ

Cấu hình module, không phải Data Contract giữa các stage:

```json
{
  "project_id": "demo_01",
  "audio_segments_path": "data/intermediate/audio_segments.json",
  "clip_metadata_path": "data/intermediate/clip_metadata.json",
  "output_dir": "data/intermediate",
  "embedding_dir": "data/intermediate/embeddings",
  "index_dir": "data/intermediate/index",
  "model": {
    "name": "clip-vit-base-patch32",
    "type": "multimodal",
    "dimension": 512
  },
  "text": {
    "prefer_translated_query": true,
    "fallback_to_query": true
  },
  "visual": {
    "embedding_level": "keyframe",
    "aggregate_clip_embedding": false
  },
  "index": {
    "enabled": true,
    "type": "faiss"
  }
}
```

| Tham số | Giá trị đề xuất MVP |
| ------- | ------------------- |
| `model.type` | `multimodal` |
| `model.dimension` | Khớp vector thật (ví dụ `512`) |
| `text.prefer_translated_query` | `true` nếu model mạnh hơn với tiếng Anh |
| `text.fallback_to_query` | `true` |
| `visual.embedding_level` | `keyframe` |
| `visual.aggregate_clip_embedding` | `false` trong MVP đầu |
| `index.enabled` | `true` nếu Matching Engine truy vấn index |
| `index.type` | `faiss` nếu nhóm dùng FAISS |

Ghi chú: MVP nên dùng **một model multimodal chung** cho text và image để vector nằm cùng embedding space. Text model A + image model B không cùng không gian → Matching Engine không so sánh trực tiếp được. Nếu chưa dùng index, vẫn lưu vector và metadata đủ để Matching Engine load thủ công.

## 5. Output cần tạo

| Output | Path | Contract? |
| ------ | ---- | --------- |
| Embedding metadata | `data/intermediate/embedding_metadata.json` | **Có** — stage chính |
| Text vectors | `data/intermediate/embeddings/emb_text_{segment_id}.npy` | Dữ liệu vector — path ghi trong metadata |
| Visual vectors | `data/intermediate/embeddings/emb_visual_{keyframe_id}.npy` | Dữ liệu vector — path ghi trong metadata |
| Visual index | `data/intermediate/index/visual.index` | Tăng tốc search — path ghi trong `index.path` |
| Indexing log | `data/intermediate/embedding_indexing_log.json` | Không — debug only |

Ví dụ layout:

```text
data/intermediate/
├── embedding_metadata.json
├── embeddings/
│   ├── emb_text_a001.npy
│   └── emb_visual_v01_c003_k01.npy
└── index/
    └── visual.index
```

Các module sau chỉ phụ thuộc `embedding_metadata.json`, vector/index paths trong file này và các file vector/index tương ứng. Nếu mâu thuẫn với log, ưu tiên `embedding_metadata.json`.

## 6. Contract fields stage trực tiếp dùng

### 6.1. Đọc từ `audio_segments.json`

→ [02 §5](02_data_contract.md#5-audio_segmentsjson) · schema: [audio_segments.schema.md](../schemas/audio_segments.schema.md) · sample: [audio_segments_sample.json](../samples/audio_segments_sample.json)

| Field đọc | Quy tắc stage |
| --------- | ------------- |
| `project_id` | Phải khớp `clip_metadata.json` |
| `items[*].segment_id` | Map text embedding |
| `items[*].query` | Fallback `source_text` |
| `items[*].translated_query` | Ưu tiên `source_text` nếu config bật |
| `items[*].needs_review` | Không chặn embedding — cảnh báo cho stage sau |

### 6.2. Đọc từ `clip_metadata.json`

→ [02 §6](02_data_contract.md#6-clip_metadatajson) · schema: [clip_metadata.schema.md](../schemas/clip_metadata.schema.md) · sample: [clip_metadata_sample.json](../samples/clip_metadata_sample.json)

| Field đọc | Quy tắc stage |
| --------- | ------------- |
| `project_id` | Phải khớp `audio_segments.json` |
| `items[*].clip_id` | Map visual embedding |
| `items[*].status` | Chỉ embed `usable` / `low_quality` |
| `items[*].keyframes[*].keyframe_id` | ID visual embedding |
| `items[*].keyframes[*].path` | Input ảnh; file phải tồn tại |

### 6.3. Ghi `embedding_metadata.json`

→ [02 §7](02_data_contract.md#7-embedding_metadatajson) · schema: [embedding_metadata.schema.md](../schemas/embedding_metadata.schema.md) · sample: [embedding_metadata_sample.json](../samples/embedding_metadata_sample.json)

**Top-level ghi:** `schema_version`, `project_id`, `model`, `created_at`, `text_embeddings`, `visual_embeddings`, `index`.

**`model` object — quy tắc stage:**

| Field | Quy tắc |
| ----- | ------- |
| `name` | Tên model thật đã load |
| `type` | MVP nên `multimodal` |
| `dimension` | Khớp vector thật — không ghi sai để khớp config |

**Text embedding item — quy tắc stage:**

| Field | Quy tắc |
| ----- | ------- |
| `embedding_id` | `emb_text_{segment_id}` — ví dụ `emb_text_a001` |
| `segment_id` | Phải tồn tại trong `audio_segments.json` |
| `source_text` | Text thật đưa vào model — xem §7.2 |
| `vector_path` | Relative path; MVP nên khác `null` cho mọi embedding |

**Visual embedding item — quy tắc stage:**

| Field | Quy tắc |
| ----- | ------- |
| `embedding_id` | `emb_visual_{keyframe_id}` — ví dụ `emb_visual_v01_c003_k01` |
| `clip_id` | Phải tồn tại trong `clip_metadata.json` |
| `keyframe_id` | Keyframe tương ứng; `null` nếu clip-level (không dùng MVP) |
| `vector_path` | Relative path; MVP nên khác `null` kể cả khi có index |

**`index` object — quy tắc stage:**

| Field | Quy tắc |
| ----- | ------- |
| `type` | Ví dụ `faiss` nếu dùng FAISS |
| `path` | Relative path; file phải tồn tại nếu ghi |
| Thứ tự row | Index row `i` ↔ `visual_embeddings[i]` — hoặc mapping phụ thống nhất với Matching Engine |

Chưa dùng index → `index = {}`; Matching Engine đọc vector files trực tiếp.

**MVP:** `text_embeddings` không rỗng nếu có segment hợp lệ; `visual_embeddings` không rỗng nếu có clip/keyframe usable; `embedding_id` không trùng; không lưu vector lớn trực tiếp trong JSON.

## 7. Quy trình xử lý riêng

### 7.1. Bước 1 — Đọc và validate input

Đọc hai file metadata; kiểm tra parse, `project_id` khớp, segment có `query`, clip/keyframe có path hợp lệ.

### 7.2. Bước 2 — Chọn `source_text`

`source_text` là text thật sự đưa vào model để tạo text embedding.

Quy tắc:

1. Nếu `translated_query` có giá trị **và** `text.prefer_translated_query = true` (model mạnh hơn với tiếng Anh) → dùng `translated_query`.
2. Nếu không có `translated_query` → dùng `query` (khi `text.fallback_to_query = true`).
3. Nếu `query` rỗng hoặc thiếu → lỗi input Stage 2; **không tự bịa text thay thế**.

Ví dụ segment:

```text
segment_id: a001
query: "khu vực cổng chính khu tham quan"
translated_query: "main entrance of tourist area"
```

| Model | `source_text` ghi trong metadata |
| ----- | -------------------------------- |
| CLIP tiếng Anh | `"main entrance of tourist area"` |
| Model hỗ trợ tiếng Việt tốt | `"khu vực cổng chính khu tham quan"` |

**Ràng buộc:** `source_text` phải khớp text thực tế đã encode — không ghi khác. Stage 4 **không sửa query**; query yếu → Matching Engine xử lý bằng score thấp. Segment `needs_review = true` vẫn tạo embedding.

### 7.3. Bước 3 — Lọc clip/keyframe hợp lệ

Clip hợp lệ: `status = usable` hoặc `low_quality`; ≥ 1 keyframe; keyframe path tồn tại; file đọc được.

Không embed: `too_short`, `error`. Thiếu `status` → rule thận trọng §4.3.

### 7.4. Bước 4 — Load model embedding

Load model theo config. Yêu cầu: text và image cùng embedding space; dimension output = `model.dimension`. Model load thất bại → dừng, báo lỗi rõ. MVP ưu tiên model multimodal có sẵn.

### 7.5. Bước 5 — Tạo text embedding

Với mỗi segment hợp lệ:

1. Chọn `source_text`.
2. Encode → vector.
3. Validate vector không rỗng; dimension = `model.dimension`.
4. Lưu vector file nếu dùng file storage.
5. Thêm item vào `text_embeddings`.

Segment thiếu text hợp lệ → bỏ qua; ghi error/warning trong log. Thiếu quá nhiều → integration có thể xem lỗi chặn.

### 7.6. Bước 6 — Tạo visual embedding

MVP: embedding **theo keyframe** (`visual.embedding_level = keyframe`).

Với mỗi keyframe hợp lệ:

1. Đọc ảnh keyframe; tiền xử lý theo model.
2. Encode → vector; validate dimension.
3. Lưu vector file.
4. Thêm item vào `visual_embeddings`.

Clip nhiều keyframe → embedding riêng từng keyframe. Matching Engine gộp score keyframe về clip (thường `max`).

**Clip-level embedding** (`aggregate_clip_embedding = true`): có thể average keyframe vectors; `keyframe_id = null` — ngoài MVP mặc định; cần thống nhất với Matching Engine.

**Clip `low_quality`:** vẫn tạo embedding — penalty ở Matching Engine.

### 7.7. Bước 7 — Layout vector files

Vector lưu tại `data/intermediate/embeddings/` (hoặc `embedding_dir` trong config):

```text
emb_text_a001.npy
emb_visual_v01_c003_k01.npy
emb_visual_v01_c003_k02.npy
```

Quy tắc layout:

| Quy tắc | Chi tiết |
| ------- | -------- |
| Path trong JSON | Relative path |
| Format | Thống nhất, ví dụ `.npy` |
| Không nhét vào JSON | Vector lớn chỉ ở file riêng |
| `vector_path` | File phải tồn tại nếu khác `null` |
| MVP | Lưu vector file cho mọi embedding, kể cả khi có index |

Index là lớp tăng tốc — không phải nơi duy nhất giữ vector. Chỉ `vector_path = null` nếu đã thống nhất cơ chế truy xuất khác với Matching Engine.

### 7.8. Bước 8 — Tạo visual index

Khi `index.enabled = true`:

* Chỉ index visual embeddings hợp lệ.
* **Thứ tự insert:** row `i` ↔ `visual_embeddings[i]`.
* Matching Engine dùng index result id → `visual_embeddings[result_id]` → `clip_id`, `keyframe_id`.
* Ghi `index.type` và `index.path` trong metadata; file index phải tồn tại.

Nếu không dùng quy tắc thứ tự trên → cần file mapping phụ (ví dụ `visual_index_mapping.json`) thống nhất với Matching Engine — không phải contract MVP.

Chưa dùng index → `index = {}`.

### 7.9. Bước 9 — Normalize vector (nếu cần)

Nếu Matching Engine dùng cosine similarity, vector nên normalize L2 trước khi lưu hoặc trước search.

* Thống nhất giữa Embedding Indexer và Matching Engine.
* Ghi normalize status trong `embedding_indexing_log.json` (contract chưa có field riêng).

### 7.10. Bước 10 — Sinh `embedding_id`

| Loại | Pattern | Ví dụ |
| ---- | ------- | ----- |
| Text | `emb_text_{segment_id}` | `emb_text_a001` |
| Visual (keyframe) | `emb_visual_{keyframe_id}` | `emb_visual_v01_c003_k01` |
| Visual (clip-level) | `emb_visual_{clip_id}` | `emb_visual_v01_c003` |

Cùng input + model + config → ID giữ ổn định. Không dùng timestamp/hash ngẫu nhiên làm ID chính MVP.

### 7.11. Bước 11 — Ghi output

Trước khi ghi `embedding_metadata.json`:

* Top-level fields đủ; `model` có `name`, `type`, `dimension`.
* `text_embeddings` / `visual_embeddings` không rỗng (nếu có input hợp lệ).
* `embedding_id` không trùng; mapping `segment_id` / `clip_id` / `keyframe_id` hợp lệ.
* `vector_path` relative; file tồn tại; `index.path` hợp lệ nếu có.

**Log phụ:** model name/type/dimension, số embedding tạo/bỏ qua, normalize status, index type/path, warnings/errors, thời gian chạy. Cấu trúc đề xuất — không phải inter-module schema.

## 8. Error / fallback / re-run behavior

### 8.1. Lỗi chặn pipeline

| Tình huống | Hành vi |
| ---------- | ------- |
| `project_id` không khớp | Dừng; không tạo metadata giả |
| Model load thất bại | Dừng; báo lỗi rõ |
| Vector sai dimension hàng loạt | Dừng hoặc báo lỗi chặn |
| Không còn visual embedding hợp lệ | Báo lỗi; matching không chạy bình thường |

### 8.2. Cảnh báo không chặn

| Tình huống | Hành vi |
| ---------- | ------- |
| Segment `needs_review = true` | Vẫn tạo embedding |
| Clip thiếu `status` | Xử lý như usable tạm; warning |
| Một số keyframe path thiếu | Bỏ qua keyframe đó; ghi warning/error |
| Clip `low_quality` | Vẫn embed; penalty ở Matching Engine |

### 8.3. Ràng buộc stage

* Không sửa `audio_segments.json`, `clip_metadata.json`, keyframe files.
* Không nhét vector lớn vào JSON; không bịa `vector_path`.
* Text và visual vector phải cùng embedding space (model multimodal).
* Các module sau không phụ thuộc `embedding_indexing_log.json`.

Quy ước score, ID, path chung: [02 §2](02_data_contract.md#2-quy-ước-chung).

### 8.4. Re-run

* Cùng `project_id` + input/model/config không đổi → `embedding_id` ổn định.
* Đổi model/dimension/source text rule → vector có thể thay đổi; ID mapping vẫn nên ổn định theo segment/clip/keyframe.
* Không `--overwrite` → báo output đã tồn tại, dừng an toàn.
* Có `--overwrite` → ghi đè metadata, vector files, index, log.
* Nếu đã có `matching_candidates.json` từ embedding cũ → chạy lại Matching Engine.

## 9. Handoff condition

Stage 4 bàn giao `embedding_metadata.json` + vector/index files cho Matching Engine khi:

```text
embedding_metadata.json parse được
có đủ top-level required fields
model có name, type, dimension
text_embeddings không rỗng (nếu có segment hợp lệ)
visual_embeddings không rỗng (nếu có clip/keyframe usable)
embedding_id không trùng
mỗi text embedding map tới segment_id hợp lệ
mỗi visual embedding map tới clip_id hợp lệ
keyframe_id nếu có map đúng keyframe của clip
vector_path relative; file tồn tại nếu khác null
index.path hợp lệ; file tồn tại nếu ghi
index row map được về visual_embeddings
```

Consumer: Matching Engine (`text_embeddings`, `visual_embeddings`, `index`, vector files); Evaluation (coverage embedding). Chi tiết: [01 §4.4](01_system_architecture.md#44-embedding-indexer) và [02 §13](02_data_contract.md#13-quy-tắc-mapping-giữa-các-file).

Thiếu text embedding cho segment → Matching Engine không matching đầy đủ; integration nên review nếu segment không bỏ qua được. Thiếu visual embedding → clip đó không xuất hiện trong search.

## 10. Test cases

| # | Test | Input / điều kiện | Kỳ vọng |
| - | ---- | ----------------- | ------- |
| 1 | Input hợp lệ | `audio_segments.json` + `clip_metadata.json` + keyframes | `embedding_metadata.json`; text + visual embeddings; model object đủ fields |
| 2 | `project_id` không khớp | Hai file khác `project_id` | Dừng; không metadata giả |
| 3 | Chọn `source_text` | Có `translated_query` + prefer=true | `source_text` = `translated_query`; không có → fallback `query`; không bịa text |
| 4 | Segment `needs_review` | `needs_review = true` | Vẫn tạo embedding |
| 5 | Clip `low_quality` | Status low_quality + keyframe OK | Tạo visual embedding |
| 6 | Clip `too_short` / `error` | Status không embed | Không tạo visual embedding; không đưa vào index |
| 7 | Keyframe path thiếu | Path không tồn tại | Không `vector_path` giả; warning/error trong log |
| 8 | Vector dimension | Output vectors | Dimension = `model.dimension`; sai → không ghi hợp lệ |
| 9 | `vector_path` | Mọi embedding MVP | Relative path; file tồn tại; không vector trong JSON |
| 10 | Index | `index.enabled = true` | Index file tạo được; row `i` ↔ `visual_embeddings[i]` |
| 11 | `embedding_id` | Output | Không trùng; map đúng segment/clip/keyframe |
| 12 | Chạy lại module | Output đã tồn tại | Không `--overwrite` → dừng; có → ghi đè; ID ổn định nếu input không đổi |

CLI tối thiểu: `python -m embedding_indexer.main --audio-segments data/intermediate/audio_segments.json --clip-metadata data/intermediate/clip_metadata.json --output-dir data/intermediate --embedding-dir data/intermediate/embeddings --index-dir data/intermediate/index`.

## 11. Acceptance criteria

Module Embedding Indexer đạt yêu cầu MVP khi:

1. Đọc được `audio_segments.json` và `clip_metadata.json`; validate `project_id` khớp.
2. Chọn đúng `source_text` theo rule §7.2; không sửa query tại Stage 4.
3. Tạo text embedding cho segment hợp lệ; visual embedding cho keyframe hợp lệ.
4. Chỉ embed clip `usable` / `low_quality`; không embed `too_short` / `error`.
5. Dùng model multimodal; `model.dimension` khớp vector thật.
6. Lưu vector files; không nhét vector lớn vào JSON.
7. `embedding_metadata.json` đúng schema; `embedding_id` ổn định, không trùng.
8. Mapping `segment_id`, `clip_id`, `keyframe_id` đúng input.
9. Tạo visual index nếu config yêu cầu; index row map về `visual_embeddings`.
10. Tạo `embedding_indexing_log.json` hỗ trợ debug.
11. Matching Engine load metadata + vector/index để chạy tiếp.
12. Có quy tắc rõ khi chạy lại cùng `project_id`.

## 12. Checklist

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc schema/sample embedding_metadata
[ ] Đọc được audio_segments.json và clip_metadata.json
[ ] Kiểm tra project_id hai file khớp nhau
[ ] Chọn source_text đúng rule (translated_query / query)
[ ] Không sửa query ở Stage 4
[ ] Load được model embedding multimodal
[ ] Model text/image nằm cùng embedding space
[ ] Lọc clip theo status usable/low_quality
[ ] Không embed clip too_short/error trong MVP
[ ] Tạo được text embedding và visual embedding từ keyframe
[ ] Vector có dimension đúng model.dimension
[ ] Lưu vector file; vector_path relative, file tồn tại
[ ] Không nhét vector lớn trực tiếp vào JSON
[ ] Tạo index nếu config yêu cầu; thứ tự row khớp visual_embeddings
[ ] Sinh embedding_id ổn định
[ ] Ghi đúng embedding_metadata.json
[ ] Ghi được embedding_indexing_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Output có thể đưa cho Matching Engine chạy tiếp
```
