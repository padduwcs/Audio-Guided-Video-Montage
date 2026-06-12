# 06. Stage 4 - Embedding Indexing

## 1. Mục tiêu của stage

Stage 4 - Embedding Indexing có nhiệm vụ tạo embedding cho audio segment và clip/keyframe, lưu vector hoặc index tìm kiếm, đồng thời tạo `embedding_metadata.json` để Matching Engine biết cách map giữa segment, clip, keyframe và embedding tương ứng.

Stage này là cầu nối giữa dữ liệu dạng text và dữ liệu dạng hình ảnh. Audio Analyzer tạo `query` cho từng audio segment. Video Analyzer tạo clip candidate và keyframe. Embedding Indexer biến các dữ liệu đó thành vector để Matching Engine có thể so sánh mức độ gần nghĩa.

Mục tiêu chính:

* Đọc `audio_segments.json`.
* Đọc `clip_metadata.json`.
* Đọc keyframe image files từ `clip_metadata.json`.
* Chọn text dùng để embedding cho từng audio segment.
* Tạo text embedding cho từng audio segment.
* Tạo visual embedding cho keyframe hoặc clip.
* Lưu vector ra file riêng hoặc index riêng, không nhét vector lớn trực tiếp vào JSON.
* Tạo index tìm kiếm visual embedding nếu cần.
* Sinh `embedding_id` ổn định.
* Xuất `embedding_metadata.json` đúng Data Contract hiện hành.
* Xuất log phụ để debug model, vector, index và mapping nếu cần.

## 2. Vị trí trong pipeline

Stage này nằm sau Audio Analyzer và Video Analyzer:

```text
Audio Analyzer                    Video Analyzer
        |                                 |
        |-- audio_segments.json           |-- clip_metadata.json
        |                                 |-- keyframe image files
        └──────────────────┬──────────────┘
                           v
                  Embedding Indexer
                           |
                           |-- embedding_metadata.json
                           |-- vector files
                           |-- visual index files
                           |-- embedding_indexing_log.json
                           |
                           v
                    Matching Engine
```

Embedding Indexer cần cả nhánh audio và nhánh video. Stage này không nên chạy trước khi `audio_segments.json` và `clip_metadata.json` đã sẵn sàng.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Embedding Indexer cần xử lý các phần sau:

1. Đọc `audio_segments.json`.
2. Đọc `clip_metadata.json`.
3. Validate audio segments có `segment_id` và text/query hợp lệ.
4. Validate clip/keyframe có `clip_id`, `keyframe_id`, `path` hợp lệ.
5. Chọn `source_text` để tạo text embedding.
6. Tạo text embedding cho từng audio segment.
7. Tạo visual embedding cho từng keyframe hoặc từng clip.
8. Lưu vector ra file riêng nếu cần.
9. Tạo visual index nếu cần truy vấn nhanh.
10. Sinh `embedding_id` ổn định.
11. Ghi mapping giữa segment/clip/keyframe và vector/index.
12. Xuất `embedding_metadata.json`.
13. Xuất `embedding_indexing_log.json` để debug nếu cần.

### 3.2. Stage này không làm

Embedding Indexer không chịu trách nhiệm cho các phần sau:

* Không chạy ASR.
* Không sửa transcript.
* Không tạo audio segment.
* Không detect scene/shot.
* Không trích keyframe mới nếu keyframe đã thiếu.
* Không tính quality score cho clip.
* Không chọn top-k clip cho audio segment.
* Không tính final matching score.
* Không tạo `matching_candidates.json`.
* Không tạo `timeline.json`.
* Không render video cuối.

Nếu keyframe thiếu hoặc lỗi, Stage 4 chỉ báo lỗi hoặc bỏ qua item đó theo rule rõ ràng. Không tự phân tích lại video để tạo keyframe thay cho Stage 3.

## 4. Input

### 4.1. Input chính

Embedding Indexer đọc:

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/keyframes/*.jpg
```

Trong đó:

* Text input lấy từ `audio_segments.json`.
* Visual input lấy từ `clip_metadata.json -> items[*].keyframes[*].path`.
* Không hard-code keyframe path ngoài metadata.

### 4.2. Điều kiện input hợp lệ

`audio_segments.json` phải thỏa:

* Parse được JSON.
* Có `schema_version`.
* Có `project_id`.
* Có `items`.
* `items` không rỗng.
* Mỗi segment có `segment_id`.
* Mỗi segment có `query` không rỗng.
* Nếu dùng `translated_query`, field này phải là string không rỗng hoặc `null`.

`clip_metadata.json` phải thỏa:

* Parse được JSON.
* Có `schema_version`.
* Có `project_id`.
* Có `items`.
* `items` không rỗng.
* Mỗi clip có `clip_id`.
* Mỗi clip usable có ít nhất một keyframe.
* Mỗi keyframe có `keyframe_id`, `timestamp`, `path`.
* File keyframe trong `path` tồn tại.

`project_id` trong hai file phải giống nhau. Nếu không giống, module phải dừng vì không thể đảm bảo dữ liệu thuộc cùng một project.

### 4.3. Clip nào được tạo embedding

Trong MVP, nên tạo visual embedding cho clip có:

```text
status = usable
status = low_quality
```

Không nên tạo embedding cho clip có:

```text
status = too_short
status = error
```

Lý do:

* `usable`: clip chính để matching.
* `low_quality`: vẫn có thể dùng nếu thiếu footage, nhưng Matching Engine sẽ áp dụng penalty.
* `too_short`: thường khó dùng trong timeline MVP.
* `error`: không đủ tin cậy để đưa vào matching.

Nếu `status` bị thiếu do dữ liệu cũ, MVP nên xử lý thận trọng:

* Nếu clip có keyframe hợp lệ và timestamp hợp lệ, có thể xem như usable tạm thời.
* Ghi warning vào `embedding_indexing_log.json`.
* Nên yêu cầu Stage 3 cập nhật lại để có `status` rõ ràng.

### 4.4. Cấu hình chạy module

Cấu hình dưới đây là cấu hình nội bộ của Embedding Indexer, không phải Data Contract bắt buộc giữa các module.

Ví dụ cấu hình:

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

Trong MVP, các giá trị đề xuất:

| Tham số | Giá trị đề xuất |
| ------- | --------------- |
| `model.type` | `multimodal` |
| `text.prefer_translated_query` | `true` nếu model mạnh hơn với tiếng Anh |
| `text.fallback_to_query` | `true` |
| `visual.embedding_level` | `keyframe` |
| `visual.aggregate_clip_embedding` | `false` trong MVP đầu |
| `index.enabled` | `true` nếu dùng Matching Engine truy vấn index |
| `index.type` | `faiss` nếu nhóm dùng FAISS |

Ghi chú:

* MVP nên dùng một model multimodal chung cho text và image để vector nằm trong cùng embedding space.
* Nếu dùng text model và image model tách biệt nhưng không cùng không gian vector, Matching Engine sẽ không so sánh trực tiếp được.
* Nếu chưa dùng index, vẫn phải lưu vector và metadata đủ để Matching Engine load vector thủ công.
* Vector lớn không nên lưu trực tiếp trong `embedding_metadata.json`.

## 5. Output

Stage này tạo output chính:

```text
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/emb_text_a001.npy
data/intermediate/embeddings/emb_visual_v01_c003_k01.npy
data/intermediate/index/visual.index
```

Stage này có thể tạo output phụ:

```text
data/intermediate/embedding_indexing_log.json
```

Trong đó:

* `embedding_metadata.json` là Data Contract chính cho Matching Engine.
* Vector files chứa embedding nếu lưu riêng từng vector.
* Visual index files phục vụ truy vấn nhanh nếu dùng FAISS hoặc index tương đương.
* `embedding_indexing_log.json` là log phụ để debug model, vector, index và mapping.

Các module sau chỉ nên phụ thuộc vào `embedding_metadata.json`, vector/index paths trong file này và các file vector/index tương ứng. Log phụ không phải contract bắt buộc.

## 6. Data Contract: `embedding_metadata.json`

### 6.1. Vai trò

`embedding_metadata.json` lưu mapping giữa audio segment, clip/keyframe và embedding tương ứng.

File này không nhất thiết chứa trực tiếp vector lớn. Vector có thể lưu ở file riêng hoặc index riêng.

File này giúp Matching Engine biết:

* Model embedding nào đã được dùng.
* Text embedding nào tương ứng với segment nào.
* Visual embedding nào tương ứng với clip/keyframe nào.
* Vector nằm ở file nào nếu lưu riêng.
* Index visual embedding nằm ở đâu nếu dùng index.

### 6.2. Cấu trúc top-level

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "model": {},
  "created_at": "2026-06-11T10:15:00Z",
  "text_embeddings": [],
  "visual_embeddings": [],
  "index": {}
}
```

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `schema_version` | string | Phiên bản schema |
| `project_id` | string | ID dự án đang xử lý |
| `model` | object | Thông tin model embedding |
| `created_at` | string | Thời điểm tạo file |
| `text_embeddings` | array[object] | Danh sách text embedding |
| `visual_embeddings` | array[object] | Danh sách visual embedding |
| `index` | object | Thông tin index nếu có |

Quy ước:

* `schema_version` dùng `"1.0"` trong MVP.
* `project_id` phải khớp với `audio_segments.json` và `clip_metadata.json`.
* `text_embeddings` không được rỗng nếu có audio segment hợp lệ.
* `visual_embeddings` không được rỗng nếu có clip/keyframe usable.

### 6.3. Model object

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `name` | string | Tên model embedding |
| `type` | string | Loại model |
| `dimension` | integer | Số chiều vector |

Allowed `type`:

```text
text
image
multimodal
```

Quy tắc MVP:

* Nên dùng `type = multimodal`.
* `dimension` phải khớp với vector thật được lưu.
* Không ghi sai dimension chỉ để khớp config.

### 6.4. Text embedding item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `embedding_id` | string | ID embedding |
| `segment_id` | string | Audio segment tương ứng |
| `source_text` | string | Text dùng để embedding |
| `vector_path` | string/null | Đường dẫn vector nếu lưu riêng |

Quy tắc:

* `segment_id` phải tồn tại trong `audio_segments.json`.
* `source_text` phải là text thực sự được đưa vào model embedding.
* `vector_path` nên là relative path nếu vector lưu riêng.
* Trong MVP, nên lưu `vector_path` cho mọi text embedding để Matching Engine có thể load trực tiếp khi cần debug hoặc khi không dùng index.
* Chỉ dùng `vector_path = null` nếu đã có cơ chế truy xuất text vector khác được thống nhất rõ với Matching Engine.

### 6.5. Visual embedding item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `embedding_id` | string | ID embedding |
| `clip_id` | string | Clip tương ứng |
| `keyframe_id` | string/null | Keyframe tương ứng nếu embedding theo keyframe |
| `vector_path` | string/null | Đường dẫn vector nếu lưu riêng |

Quy tắc:

* `clip_id` phải tồn tại trong `clip_metadata.json`.
* Nếu embedding theo keyframe, `keyframe_id` phải tồn tại trong keyframes của clip tương ứng.
* Nếu embedding đại diện cho cả clip, `keyframe_id = null`.
* `vector_path` nên là relative path nếu vector lưu riêng.
* Trong MVP, nên lưu `vector_path` cho mọi visual embedding, kể cả khi đã tạo index.
* Index nên được xem là lớp tăng tốc truy vấn, không phải nơi duy nhất giữ vector.
* Chỉ dùng `vector_path = null` nếu đã có cơ chế truy xuất visual vector khác được thống nhất rõ với Matching Engine.

### 6.6. Index object

Data Contract tổng chỉ yêu cầu `index` là object. Với MVP, nên dùng cấu trúc tối thiểu sau:

```json
{
  "type": "faiss",
  "path": "data/intermediate/index/visual.index"
}
```

Quy tắc:

* Nếu có index, `type` và `path` nên có giá trị rõ ràng.
* `path` phải là relative path.
* File index tại `path` phải tồn tại nếu `index.path` được ghi.
* Nếu chưa dùng index, có thể dùng object rỗng `{}` và Matching Engine sẽ đọc vector files trực tiếp.
* Trong MVP, nếu dùng index, thứ tự vector được insert vào index phải trùng với thứ tự item trong `visual_embeddings`, hoặc phải có file mapping phụ được thống nhất với Matching Engine.

## 7. Quy tắc chọn source_text

`source_text` là text thật sự được đưa vào model để tạo text embedding.

Quy tắc đề xuất:

1. Nếu `translated_query` có giá trị và model embedding mạnh hơn với tiếng Anh, dùng `translated_query`.
2. Nếu không có `translated_query`, dùng `query`.
3. Nếu `query` rỗng hoặc thiếu, đây là lỗi input từ Stage 2, không tự bịa text thay thế.

Ví dụ:

```json
{
  "segment_id": "a001",
  "query": "khu vực cổng chính khu tham quan",
  "translated_query": "main entrance of tourist area"
}
```

Nếu model là CLIP tiếng Anh:

```json
{
  "embedding_id": "emb_text_a001",
  "segment_id": "a001",
  "source_text": "main entrance of tourist area",
  "vector_path": "data/intermediate/embeddings/emb_text_a001.npy"
}
```

Nếu model hỗ trợ tiếng Việt tốt:

```json
{
  "embedding_id": "emb_text_a001",
  "segment_id": "a001",
  "source_text": "khu vực cổng chính khu tham quan",
  "vector_path": "data/intermediate/embeddings/emb_text_a001.npy"
}
```

## 8. Quy tắc đặt ID

ID cần ngắn gọn, ổn định và dễ map giữa các file.

Với MVP, quy tắc đề xuất:

```text
text embedding: emb_text_a001
visual embedding theo keyframe: emb_visual_v01_c003_k01
visual embedding theo clip: emb_visual_v01_c003
```

Quy tắc sinh `embedding_id`:

* Text embedding dùng `segment_id`.
* Visual embedding theo keyframe dùng `keyframe_id`.
* Visual embedding theo clip dùng `clip_id`.
* Nếu chạy lại với cùng input và cùng model, ID nên giữ ổn định.
* Không dùng timestamp hoặc hash ngẫu nhiên làm ID chính trong MVP.

## 9. Quy trình xử lý đề xuất

### 9.1. Bước 1 - Đọc input metadata

Embedding Indexer đọc:

* `audio_segments.json`
* `clip_metadata.json`

Kiểm tra:

* Hai file parse được.
* Hai file có cùng `project_id`.
* Audio segment có `segment_id`, `query`.
* Clip/keyframe có `clip_id`, `keyframe_id`, `path`.

### 9.2. Bước 2 - Chọn segment hợp lệ

Segment hợp lệ để tạo text embedding cần có:

* `segment_id`
* `query` không rỗng hoặc `translated_query` không rỗng
* `start`, `end`, `duration` hợp lệ

Nếu segment có `needs_review = true`, vẫn tạo embedding. Đây là cảnh báo cho UI hoặc Matching Engine, không phải lỗi chặn Stage 4.

Nếu segment không có text hợp lệ để embedding, bỏ qua segment đó và ghi error/warning trong log. Nếu bỏ qua segment làm thiếu text embedding cho pipeline, integration có thể xem đây là lỗi chặn.

### 9.3. Bước 3 - Chọn clip/keyframe hợp lệ

Clip hợp lệ để tạo visual embedding trong MVP:

* `status = usable` hoặc `status = low_quality`
* Có ít nhất một keyframe.
* Keyframe path tồn tại.
* Keyframe file đọc được.

Không tạo visual embedding cho clip:

* `status = too_short`
* `status = error`

Nếu clip thiếu `status`, xử lý theo rule thận trọng ở mục 4.3.

### 9.4. Bước 4 - Load model embedding

Load model embedding theo config.

Yêu cầu:

* Model phải hỗ trợ text và image cùng embedding space nếu muốn matching trực tiếp.
* Dimension output phải khớp `model.dimension`.
* Nếu model load thất bại, module phải dừng và báo lỗi rõ ràng.

Trong MVP, nên ưu tiên model multimodal có sẵn thay vì train model từ đầu.

### 9.5. Bước 5 - Tạo text embedding

Với mỗi audio segment hợp lệ:

1. Chọn `source_text`.
2. Encode text thành vector.
3. Validate vector không rỗng.
4. Validate dimension đúng.
5. Lưu vector nếu dùng vector files.
6. Thêm item vào `text_embeddings`.

Không tự sửa `query` ở Stage 4. Nếu query quá yếu, đây là vấn đề của Stage 2 hoặc Matching Engine sẽ xử lý bằng score thấp.

### 9.6. Bước 6 - Tạo visual embedding

Với mỗi keyframe hợp lệ:

1. Đọc ảnh keyframe.
2. Tiền xử lý ảnh theo yêu cầu model.
3. Encode ảnh thành vector.
4. Validate vector không rỗng.
5. Validate dimension đúng.
6. Lưu vector nếu dùng vector files.
7. Thêm item vào `visual_embeddings`.

Nếu một clip có nhiều keyframe, MVP nên tạo embedding riêng cho từng keyframe.

Nếu sau này muốn tạo embedding đại diện clip:

* Có thể average các keyframe vector.
* Ghi visual embedding item với `clip_id` và `keyframe_id = null`.
* Cần đảm bảo Matching Engine hiểu cách dùng embedding clip-level này.

### 9.7. Bước 7 - Lưu vector files

Vector files nên lưu ở:

```text
data/intermediate/embeddings/
```

Ví dụ:

```text
data/intermediate/embeddings/emb_text_a001.npy
data/intermediate/embeddings/emb_visual_v01_c003_k01.npy
```

Quy tắc:

* Path trong JSON phải là relative path.
* File vector phải tồn tại nếu `vector_path` khác `null`.
* Trong MVP, nên lưu vector file cho cả text embedding và visual embedding.
* Không lưu vector lớn trực tiếp vào JSON.
* Format vector nên thống nhất, ví dụ `.npy`.

### 9.8. Bước 8 - Tạo visual index

Nếu `index.enabled = true`, tạo index cho visual embeddings.

Mục tiêu:

* Matching Engine có thể truy vấn nhanh top candidate visual embedding cho từng text embedding.
* Index phải map được kết quả search về `clip_id` và `keyframe_id`.

Quy tắc:

* Index chỉ nên chứa visual embeddings hợp lệ.
* Trong MVP, index row `i` nên tương ứng với `visual_embeddings[i]`.
* Nếu không dùng quy tắc thứ tự trên, cần có mapping phụ đủ rõ để Matching Engine map index result về `clip_id` và `keyframe_id`.
* File index phải tồn tại nếu ghi `index.path`.
* Nếu chưa dùng index, để `index = {}` và Matching Engine đọc vector files trực tiếp.

Ghi chú:

Data Contract hiện tại chỉ có `index.type` và `index.path` trong ví dụ. Nếu cần mapping phụ cho FAISS, có thể lưu file phụ như:

```text
data/intermediate/index/visual_index_mapping.json
```

File mapping phụ không phải Data Contract chính trong MVP, nhưng nếu Matching Engine cần thì phải thống nhất giữa hai module.

Khuyến nghị MVP:

```text
Insert visual embeddings vào index theo đúng thứ tự visual_embeddings.
Matching Engine dùng index result id để lấy visual_embeddings[result_id].
```

### 9.9. Bước 9 - Ghi `embedding_metadata.json`

Trước khi ghi file, cần kiểm tra:

* Có đủ top-level fields.
* `model` có đủ `name`, `type`, `dimension`.
* `text_embeddings` không rỗng.
* `visual_embeddings` không rỗng.
* `embedding_id` không trùng.
* Mỗi `segment_id` trong text embedding tồn tại trong `audio_segments.json`.
* Mỗi `clip_id` trong visual embedding tồn tại trong `clip_metadata.json`.
* Mỗi `keyframe_id` nếu có tồn tại trong clip tương ứng.
* `vector_path` là relative path hoặc `null`.
* Trong MVP, `vector_path` nên khác `null` cho mọi embedding.
* File vector tồn tại nếu `vector_path` khác `null`.
* `index.path` là relative path nếu có.
* File index tồn tại nếu `index.path` có giá trị.

## 10. Quy tắc vector và index

### 10.1. Không lưu vector lớn trực tiếp trong JSON

Không nên ghi:

```json
{
  "vector": [0.012, -0.034, 0.128]
}
```

trong `embedding_metadata.json`.

Lý do:

* JSON sẽ rất lớn.
* Khó debug bằng mắt.
* Tốn bộ nhớ khi load metadata.
* Dễ chậm khi commit hoặc truyền file.

Nên lưu vector ở file riêng và ghi `vector_path`.

### 10.2. Vector dimension phải nhất quán

Tất cả vector do cùng một model tạo ra phải có dimension bằng `model.dimension`.

Nếu phát hiện vector sai dimension:

* Không ghi vector đó như item hợp lệ.
* Ghi lỗi trong `embedding_indexing_log.json`.
* Nếu lỗi ảnh hưởng nhiều item, module nên dừng.

### 10.3. Text và visual vector phải cùng embedding space

Matching Engine chỉ so sánh trực tiếp text vector và visual vector nếu chúng cùng embedding space.

MVP nên dùng model multimodal để đảm bảo điều này.

Không nên dùng:

```text
Text vector từ model A
Image vector từ model B không cùng không gian
```

rồi tính cosine similarity trực tiếp.

### 10.4. Normalize vector

Nếu Matching Engine dùng cosine similarity, vector nên được normalize L2 trước khi lưu hoặc trước khi search.

Quy tắc:

* Cần thống nhất giữa Embedding Indexer và Matching Engine.
* Nếu đã normalize ở Stage 4, ghi rõ trong `embedding_indexing_log.json`.
* Nếu chưa normalize, Matching Engine phải normalize trước khi tính similarity.

Vì Data Contract chưa có field riêng cho normalize status, MVP nên ghi thông tin này trong log phụ hoặc config dùng chung.

## 11. Quy tắc text embedding chi tiết

### 11.1. Không bỏ segment chỉ vì needs_review

Segment có `needs_review = true` vẫn nên được tạo embedding.

Lý do:

* UI hoặc người dùng có thể review sau.
* Matching Engine vẫn cần candidate ban đầu.
* Nếu bỏ segment, timeline có thể thiếu đoạn.

### 11.2. Không sửa query tại Stage 4

Stage 4 không nên tự sửa query.

Nếu query kém:

* Vẫn tạo embedding nếu query không rỗng.
* Ghi warning nếu cần.
* Để Stage 2 hoặc UI correction xử lý ở lần chạy sau.

### 11.3. Text dùng cho embedding phải được ghi lại

`source_text` phải phản ánh đúng text đưa vào model.

Nếu dùng `translated_query`, `source_text` phải là `translated_query`.

Nếu dùng `query`, `source_text` phải là `query`.

Không ghi `source_text` khác với text thực tế đã encode.

## 12. Quy tắc visual embedding chi tiết

### 12.1. Embedding theo keyframe

MVP nên embedding theo keyframe.

Ưu điểm:

* Dễ map với keyframe image files.
* Dễ hiển thị trên UI.
* Một clip có nhiều đại diện hình ảnh.
* Matching Engine có thể lấy max/average score giữa các keyframe của cùng clip.

### 12.2. Embedding theo clip

Embedding theo clip có thể làm sau.

Nếu triển khai:

* Có thể tổng hợp từ nhiều keyframe.
* `keyframe_id = null`.
* Cần ghi rõ trong log cách aggregate.
* Matching Engine phải biết visual embedding đó là clip-level.

### 12.3. Clip low_quality

Clip `low_quality` vẫn có thể được tạo embedding.

Lý do:

* Trong trường hợp footage thiếu, clip này vẫn có thể là lựa chọn gần nghĩa nhất.
* Matching Engine có thể áp dụng `bad_clip_penalty` hoặc giảm `visual_quality_score`.

### 12.4. Clip too_short và error

MVP không nên tạo embedding cho clip `too_short` và `error`.

Nếu cần debug, thông tin clip vẫn nằm trong `clip_metadata.json`, nhưng không đưa vào search index chính.

## 13. Output phụ: `embedding_indexing_log.json`

### 13.1. Vai trò

`embedding_indexing_log.json` là file log phụ của Stage 4, dùng để debug model, vector, index và mapping.

File này không phải Data Contract chính giữa các module. Các module sau không nên phụ thuộc vào file này để chạy logic chính.

Nên dùng file này để ghi:

* Model name, type, dimension.
* Số text embeddings tạo được.
* Số visual embeddings tạo được.
* Segment nào bị bỏ qua và lý do.
* Clip/keyframe nào bị bỏ qua và lý do.
* Vector dimension thực tế.
* Vector có normalize hay không.
* Index type và path.
* Thời gian chạy module nếu cần.

### 13.2. Cấu trúc đề xuất

Đây là cấu trúc đề xuất, không bắt buộc phải xem là schema liên module:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:15:00Z",
  "model": {
    "name": "clip-vit-base-patch32",
    "type": "multimodal",
    "dimension": 512
  },
  "summary": {
    "segment_count": 12,
    "text_embedding_count": 12,
    "clip_count": 34,
    "visual_embedding_count": 84,
    "skipped_segment_count": 0,
    "skipped_visual_count": 3
  },
  "index": {
    "enabled": true,
    "type": "faiss",
    "path": "data/intermediate/index/visual.index"
  },
  "warnings": [],
  "errors": []
}
```

### 13.3. Nguyên tắc sử dụng

`embedding_metadata.json` là nguồn dữ liệu chính cho Matching Engine. `embedding_indexing_log.json` chỉ dùng để:

* Debug vì sao thiếu embedding.
* Debug vì sao index không load được.
* Kiểm tra model/dimension.
* Hỗ trợ leader review chất lượng stage.

Nếu `embedding_metadata.json` và `embedding_indexing_log.json` có thông tin mâu thuẫn, các module pipeline phải ưu tiên `embedding_metadata.json`.

## 14. Ví dụ `embedding_metadata.json`

**Mẫu chuẩn:** `docs/samples/embedding_metadata_sample.json`.

Ví dụ rút gọn:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "model": {
    "name": "clip-vit-base-patch32",
    "type": "multimodal",
    "dimension": 512
  },
  "created_at": "2026-06-11T10:15:00Z",
  "text_embeddings": [
    {
      "embedding_id": "emb_text_a001",
      "segment_id": "a001",
      "source_text": "main entrance of tourist area",
      "vector_path": "data/intermediate/embeddings/emb_text_a001.npy"
    },
    {
      "embedding_id": "emb_text_a002",
      "segment_id": "a002",
      "source_text": "exhibition area with notable artifacts",
      "vector_path": "data/intermediate/embeddings/emb_text_a002.npy"
    }
  ],
  "visual_embeddings": [
    {
      "embedding_id": "emb_visual_v01_c003_k01",
      "clip_id": "v01_c003",
      "keyframe_id": "v01_c003_k01",
      "vector_path": "data/intermediate/embeddings/emb_visual_v01_c003_k01.npy"
    },
    {
      "embedding_id": "emb_visual_v01_c003_k02",
      "clip_id": "v01_c003",
      "keyframe_id": "v01_c003_k02",
      "vector_path": "data/intermediate/embeddings/emb_visual_v01_c003_k02.npy"
    }
  ],
  "index": {
    "type": "faiss",
    "path": "data/intermediate/index/visual.index"
  }
}
```

## 15. Quan hệ với các module khác

### 15.1. Audio Analyzer

Embedding Indexer đọc:

```text
audio_segments.json
items[*].segment_id
items[*].query
items[*].translated_query
```

Embedding Indexer không tự tạo lại query và không sửa transcript.

### 15.2. Video Analyzer

Embedding Indexer đọc:

```text
clip_metadata.json
items[*].clip_id
items[*].status
items[*].keyframes
items[*].keyframes[*].path
```

Embedding Indexer không tự trích lại keyframe nếu keyframe thiếu.

### 15.3. Matching Engine

Matching Engine đọc:

```text
embedding_metadata.json
audio_segments.json
clip_metadata.json
vector/index files
```

Matching Engine dùng:

* `text_embeddings` để lấy vector cho từng audio segment.
* `visual_embeddings` để lấy vector cho clip/keyframe.
* `index` để search visual embeddings nếu có.
* `clip_metadata.json` để lấy duration, quality_score và status.
* `audio_segments.json` để lấy segment duration và text nếu cần giải thích kết quả.

Stage 4 không tạo `matching_candidates.json`. Đó là trách nhiệm của Matching Engine.

### 15.4. Review UI

Review UI thường không cần đọc embedding trực tiếp.

Tuy nhiên, nếu cần debug hoặc demo, UI có thể hiển thị:

* Model embedding đã dùng.
* Số embedding đã tạo.
* Clip/keyframe nào thiếu embedding.

Thông tin này nên lấy từ `embedding_metadata.json` hoặc log phụ.

### 15.5. Evaluation

Evaluation có thể dùng `embedding_metadata.json` để:

* Kiểm tra coverage embedding.
* Kiểm tra segment nào thiếu text embedding.
* Kiểm tra clip nào thiếu visual embedding.
* Ghi nhận model embedding dùng trong báo cáo.

## 16. Điều kiện handoff sang stage sau

Stage 4 được phép bàn giao cho Matching Engine khi thỏa các điều kiện sau:

```text
embedding_metadata.json parse được
embedding_metadata.json có đủ top-level required fields
model có name, type, dimension
text_embeddings không rỗng
visual_embeddings không rỗng
embedding_id không trùng
mỗi text embedding map tới segment_id hợp lệ
mỗi visual embedding map tới clip_id hợp lệ
keyframe_id nếu có map đúng keyframe của clip
vector_path là relative path hoặc null
vector_path nên khác null cho mọi embedding trong MVP
file vector tồn tại nếu vector_path khác null
index.path là relative path nếu có
file index tồn tại nếu index.path có giá trị
index row map được về visual_embeddings
```

Nếu thiếu text embedding cho một số segment:

* Module phải ghi rõ trong log.
* Matching Engine sẽ không thể matching đầy đủ cho các segment đó.
* Integration pipeline nên xem đây là lỗi cần review nếu segment đó không thể bỏ qua.

Nếu thiếu visual embedding:

* Matching Engine vẫn có thể chạy nếu còn đủ visual embeddings khác.
* Clip thiếu embedding sẽ không xuất hiện trong search nếu dùng index.
* Cần ghi rõ trong log để debug.

## 17. Ràng buộc kỹ thuật

### 17.1. Không thay đổi input contract

Embedding Indexer không được sửa trực tiếp:

* `audio_segments.json`
* `clip_metadata.json`
* keyframe image files

Nếu phát hiện lỗi input, ghi log và báo lỗi. Việc sửa input thuộc về stage tạo ra input đó.

### 17.2. Không nhét vector lớn vào JSON

`embedding_metadata.json` chỉ nên chứa metadata và path.

Vector lớn phải nằm ở:

```text
data/intermediate/embeddings/
```

hoặc index riêng.

### 17.3. Không bịa vector_path

Nếu file vector không tồn tại, không được ghi `vector_path` giả.

Nếu không lưu vector riêng vì đã lưu trong index, dùng:

```json
"vector_path": null
```

nhưng phải đảm bảo Matching Engine có cách truy xuất embedding.

Khuyến nghị MVP: vẫn lưu vector file riêng cho mọi embedding, kể cả khi có index, để dễ debug và tránh phụ thuộc hoàn toàn vào index binary.

### 17.4. Không dùng model không tương thích

Không dùng text embedding và visual embedding không cùng embedding space để tính similarity trực tiếp.

Nếu cần dùng hai model riêng, phải có phương pháp alignment rõ ràng. Phần này nằm ngoài MVP.

### 17.5. Không phụ thuộc vào log phụ

Các module sau không được phụ thuộc vào `embedding_indexing_log.json` để chạy logic chính.

Nếu thông tin cần thiết cho Matching Engine, thông tin đó phải nằm trong `embedding_metadata.json` hoặc file vector/index được metadata trỏ đến.

## 18. Re-run behavior

Embedding Indexer cần có quy tắc rõ ràng khi chạy lại với cùng `project_id`.

### 18.1. Mục tiêu

Chạy lại module không được làm `embedding_id` thay đổi bất ngờ nếu input, model và config không đổi.

Yêu cầu:

* Nếu input và model không đổi, `embedding_id` nên giữ ổn định.
* Nếu đổi model, dimension hoặc source text rule, vector có thể thay đổi nhưng ID mapping vẫn nên ổn định nếu segment/clip/keyframe không đổi.
* Không ghi đè output cũ nếu người chạy chưa cho phép.

### 18.2. Quy tắc đề xuất

Nếu chạy lại với cùng `project_id`:

* Nếu có flag `--overwrite`, module được phép ghi đè `embedding_metadata.json`, vector files, index files và `embedding_indexing_log.json`.
* Nếu không có `--overwrite`, module nên báo output đã tồn tại và dừng an toàn, hoặc yêu cầu người dùng chọn output/run khác.
* Nếu đã có `matching_candidates.json` dựa trên embedding cũ, nên chạy lại Matching Engine sau khi Stage 4 chạy lại.

## 19. Gợi ý cấu trúc code

Đây là gợi ý tổ chức module, không bắt buộc nếu nhóm đã có style code riêng.

```text
embedding_indexer/
│
├── __init__.py
├── main.py
├── config.py
├── model_loader.py
├── text_embedder.py
├── visual_embedder.py
├── vector_store.py
├── index_builder.py
├── embedding_metadata_writer.py
└── validator.py
```

Vai trò từng file:

| File | Vai trò |
| ---- | ------- |
| `main.py` | Entry point chạy module |
| `config.py` | Đọc và validate cấu hình chạy module |
| `model_loader.py` | Load model embedding |
| `text_embedder.py` | Tạo text embedding từ query/translated_query |
| `visual_embedder.py` | Tạo visual embedding từ keyframe image files |
| `vector_store.py` | Lưu vector files |
| `index_builder.py` | Tạo visual index nếu cần |
| `embedding_metadata_writer.py` | Tạo và ghi `embedding_metadata.json` |
| `validator.py` | Kiểm tra input và output theo quy tắc hiện hành |

Nếu nhóm dùng ngôn ngữ hoặc framework khác, vẫn cần giữ nguyên trách nhiệm logic tương đương.

## 20. Gợi ý CLI

CLI tối thiểu:

```text
python -m embedding_indexer.main \
  --audio-segments data/intermediate/audio_segments.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --output-dir data/intermediate \
  --embedding-dir data/intermediate/embeddings \
  --index-dir data/intermediate/index
```

Output mong đợi:

```text
data/intermediate/embedding_metadata.json
data/intermediate/embedding_indexing_log.json
data/intermediate/embeddings/emb_text_a001.npy
data/intermediate/embeddings/emb_visual_v01_c003_k01.npy
data/intermediate/index/visual.index
```

CLI nên trả về:

* exit code `0` nếu xử lý thành công.
* exit code khác `0` nếu lỗi chặn pipeline.
* message ngắn gọn cho người dùng.
* log chi tiết hơn cho developer nếu cần debug.

CLI nên có thêm flag:

```text
--overwrite
```

Flag này cho phép ghi đè output cũ khi chạy lại cùng `project_id`.

## 21. Test cases bắt buộc

### 21.1. Test input hợp lệ

Input:

```text
audio_segments.json
clip_metadata.json
keyframe image files
```

Kỳ vọng:

* Tạo được `embedding_metadata.json`.
* Tạo được text embeddings.
* Tạo được visual embeddings.
* Top-level có đúng `project_id`.
* Model object có đủ required fields.

### 21.2. Test project_id không khớp

Kỳ vọng:

* Module dừng.
* Không tạo metadata giả.
* Báo lỗi rõ ràng.

### 21.3. Test chọn source_text

Kỳ vọng:

* Nếu ưu tiên `translated_query` và field này có giá trị, `source_text` dùng `translated_query`.
* Nếu không có `translated_query`, fallback sang `query`.
* Không tự bịa source_text.

### 21.4. Test segment needs_review

Kỳ vọng:

* Segment `needs_review = true` vẫn được tạo embedding nếu có text hợp lệ.
* Log có thể ghi warning nếu cần.

### 21.5. Test clip low_quality

Kỳ vọng:

* Clip `low_quality` vẫn được tạo embedding nếu có keyframe hợp lệ.
* Matching Engine sẽ xử lý penalty ở stage sau.

### 21.6. Test clip too_short/error

Kỳ vọng:

* Clip `too_short` và `error` không được đưa vào visual index chính trong MVP.
* Không tạo visual embedding cho keyframe lỗi.

### 21.7. Test keyframe path thiếu

Kỳ vọng:

* Không ghi vector_path giả.
* Ghi warning/error trong log.
* Nếu thiếu quá nhiều visual embeddings, module dừng hoặc báo lỗi chặn.

### 21.8. Test vector dimension

Kỳ vọng:

* Mọi vector có dimension đúng bằng `model.dimension`.
* Vector sai dimension không được ghi như embedding hợp lệ.

### 21.9. Test vector_path

Kỳ vọng:

* `vector_path` là relative path hoặc `null`.
* Trong MVP, `vector_path` nên khác `null` cho mọi embedding trừ khi đã thống nhất cơ chế truy xuất khác với Matching Engine.
* Nếu `vector_path` khác `null`, file vector tồn tại.
* Không lưu vector trực tiếp trong JSON.

### 21.10. Test index

Kỳ vọng:

* Nếu `index.enabled = true`, tạo được index file.
* `index.path` là relative path.
* File tại `index.path` tồn tại.
* Index chỉ chứa visual embeddings hợp lệ.
* Index result id map được về đúng item trong `visual_embeddings`.

### 21.11. Test embedding_id

Kỳ vọng:

* `embedding_id` không trùng.
* Text embedding ID map đúng `segment_id`.
* Visual embedding ID map đúng `clip_id` hoặc `keyframe_id`.

### 21.12. Test chạy lại module

Kỳ vọng:

* Nếu chạy lại không có `--overwrite` và output đã tồn tại, module dừng an toàn hoặc yêu cầu chọn output khác.
* Nếu chạy lại có `--overwrite`, module được phép ghi đè output cũ.
* Nếu input và model không đổi, ID giữ ổn định.

## 22. Tiêu chí nghiệm thu

Module Embedding Indexer được xem là đạt yêu cầu MVP khi:

1. Đọc được `audio_segments.json`.
2. Đọc được `clip_metadata.json`.
3. Validate được `project_id` khớp giữa hai file.
4. Chọn đúng `source_text` cho từng segment.
5. Tạo được text embedding cho segment hợp lệ.
6. Tạo được visual embedding cho keyframe hợp lệ.
7. Không tạo embedding cho clip `too_short` hoặc `error` trong MVP.
8. Clip `low_quality` vẫn có thể được tạo embedding.
9. Tạo `embedding_metadata.json` đúng schema hiện hành.
10. `model` có `name`, `type`, `dimension`.
11. `embedding_id` không trùng và ổn định.
12. `segment_id`, `clip_id`, `keyframe_id` map đúng về input.
13. Vector dimension đúng với `model.dimension`.
14. `vector_path` là relative path hoặc `null`.
15. Trong MVP, `vector_path` nên khác `null` cho mọi embedding.
16. File vector tồn tại nếu `vector_path` khác `null`.
17. Không nhét vector lớn trực tiếp vào JSON.
18. Tạo visual index nếu config yêu cầu.
19. `index.path` là relative path và file tồn tại nếu được ghi.
20. Index result id map được về `visual_embeddings`.
21. Tạo `embedding_indexing_log.json` để hỗ trợ debug.
22. Matching Engine có thể load metadata và vector/index để chạy tiếp.
23. Có quy tắc rõ ràng khi chạy lại cùng `project_id`.

## 23. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 4 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được audio_segments.json
[ ] Đọc được clip_metadata.json
[ ] Kiểm tra project_id hai file khớp nhau
[ ] Chọn source_text đúng rule
[ ] Không sửa query ở Stage 4
[ ] Load được model embedding
[ ] Model text/image nằm cùng embedding space
[ ] Tạo được text embedding
[ ] Tạo được visual embedding từ keyframe
[ ] Không tạo embedding cho clip too_short/error trong MVP
[ ] Có xử lý clip low_quality đúng rule
[ ] Vector có dimension đúng
[ ] Lưu vector file nếu cần
[ ] Không nhét vector lớn trực tiếp vào JSON
[ ] vector_path là relative path hoặc null
[ ] vector_path khác null cho mọi embedding trong MVP
[ ] File vector tồn tại nếu vector_path khác null
[ ] Tạo index nếu config yêu cầu
[ ] index.path là relative path nếu có
[ ] File index tồn tại nếu index.path có giá trị
[ ] Index result id map được về visual_embeddings
[ ] Sinh embedding_id ổn định
[ ] Ghi đúng embedding_metadata.json
[ ] Ghi được embedding_indexing_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương khi chạy lại
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Output có thể đưa cho Matching Engine chạy tiếp
```

## 24. Ghi chú triển khai MVP

Trong MVP, không cần làm Embedding Indexer quá phức tạp. Ưu tiên quan trọng nhất là tạo được embedding ổn định, đúng mapping và Matching Engine có thể load được.

Thứ tự ưu tiên nên là:

1. Đọc đúng `audio_segments.json` và `clip_metadata.json`.
2. Dùng một model multimodal chung cho text và image.
3. Tạo text embedding từ `translated_query` hoặc `query`.
4. Tạo visual embedding từ keyframe.
5. Lưu vector hoặc index theo path rõ ràng.
6. Ghi `embedding_metadata.json` đúng schema.
7. Validate mapping segment/clip/keyframe.
8. Ghi log dễ debug.
9. Tối ưu index và tốc độ sau.

Nếu có tranh luận giữa việc chọn model embedding thật tốt và việc đảm bảo pipeline end-to-end chạy được, MVP nên ưu tiên model có sẵn, dễ chạy, dễ tích hợp trước. Model có thể thay sau miễn là `embedding_metadata.json` không đổi schema.
