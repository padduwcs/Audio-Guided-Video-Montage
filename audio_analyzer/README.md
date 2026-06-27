# Audio Analyzer

Module Stage 2 chuyển audio thuyết minh đã chuẩn hóa thành transcript có
timestamp, chia transcript thành các segment và tạo dữ liệu nội bộ phục vụ các
stage phía sau.

Module sử dụng `faster-whisper` làm ASR backend. Sau ASR, transcript được làm
sạch nhẹ, phân đoạn và bổ sung `query`, `keywords`, `segment_type` cùng cờ
`needs_review`. Module không phân tích video, chọn clip, tạo timeline hoặc
render video.

## Input

Input metadata mặc định:

```text
data/intermediate/media_metadata.json
```

Module đọc file audio từ:

```text
media_metadata.json → audio.normalized_path
```

Đường dẫn audio không được hard-code. Module chỉ chạy khi `audio.status` là
`ready` hoặc `warning`, đồng thời kiểm tra `audio.normalized_path`,
`audio.duration` và sự tồn tại của file audio. Trạng thái `error` làm pipeline
dừng với thông báo lỗi.

## Output

```text
data/intermediate/audio_segments.json
data/intermediate/audio_analysis_log.json
```

- `audio_segments.json` là output theo Data Contract, chứa transcript segment,
  timestamp, query và metadata enrichment.
- `audio_analysis_log.json` là log debug nội bộ, chứa backend/model, raw ASR
  chunks, warning/error, thao tác merge/split và lý do segment cần review. Các
  module downstream không nên phụ thuộc vào cấu trúc của log này.

Output được ghi qua file tạm rồi replace. Nếu `audio_segments.json` đã tồn tại,
module dừng trừ khi có `--overwrite`.

## Cài dependency

Chạy tại thư mục gốc của repository:

```bash
pip install -r requirements.txt
```

Lần chạy ASR thật đầu tiên có thể cần tải model được chọn nếu model chưa có
trong cache cục bộ.

## Chạy module

```bash
python -m audio_analyzer.main --media-metadata data/intermediate/media_metadata.json --output-dir data/intermediate --model base --language auto --overwrite
```

Để rerank các query candidate bằng multilingual embedding local:

```bash
python -m audio_analyzer.main --media-metadata data/intermediate/media_metadata.json --output-dir data/intermediate --model base --language auto --query-backend local-embedding --overwrite
```

Lần chạy đầu của `local-embedding` sẽ tải model query nếu chưa có trong cache.
Nếu model không load/inference được, pipeline ghi warning vào
`audio_analysis_log.json` và fallback về query rule-based.

Các tham số:

- `--media-metadata`: đường dẫn tới `media_metadata.json`.
- `--output-dir`: thư mục ghi hai output của module.
- `--model`: tên hoặc đường dẫn model faster-whisper, mặc định là `base`.
- `--language`: chế độ ngôn ngữ, mặc định là `auto`. Chọn theo audio:
  - Audio thuần tiếng Việt: dùng `--language vi`.
  - Audio thuần tiếng Anh: dùng `--language en`.
  - Audio lẫn Việt–Anh hoặc có thuật ngữ tiếng Anh: dùng `--language auto`.
    Chế độ này bật nhận diện đa ngôn ngữ và không dịch transcript.
- `--device`: thiết bị inference, ví dụ `cpu` hoặc `cuda`; mặc định là `cpu`.
- `--compute-type`: kiểu tính toán của CTranslate2, mặc định là `int8`.
- `--query-backend`: `rules` (nhanh, không tải model) hoặc `local-embedding`
  (batch multilingual semantic reranking); mặc định là `rules`.
- `--query-model`: tên hoặc đường dẫn Sentence Transformers model dùng cho
  query reranking.
- `--query-min-similarity`: ngưỡng cosine tối thiểu để chấp nhận candidate;
  mặc định `0.72`.
- `--overwrite`: cho phép ghi đè `audio_segments.json` đã tồn tại.

Xem toàn bộ tham số:

```bash
python -m audio_analyzer.main --help
```

## Confidence

`asr_confidence` chỉ được ghi khi ASR backend cung cấp trực tiếp một confidence
hợp lệ trong khoảng `[0.0, 1.0]`. Module không quy đổi `avg_logprob` hoặc score
nội bộ thành confidence. Nếu backend không có confidence phù hợp, giá trị được
ghi là `null`.

## Chạy test

Test sử dụng fake backend và không tải model ASR:

```bash
python -m unittest discover -s audio_analyzer/tests -v
```

Integration test ghi output trong temporary directory, không ghi vào
`data/intermediate` thật.

## Giới hạn hiện tại

- `translated_query` chưa được dịch và được để là `null`.
- Cần metadata và audio thật để chạy smoke test với faster-whisper; smoke test
  thực tế chưa được thực hiện.
- Downstream integration chưa được kiểm tra vì các module phía sau chưa hoàn
  thiện.
- Chất lượng transcript, timestamp và segmentation thực tế còn phụ thuộc model,
  chất lượng audio và thiết bị inference.

## Tài liệu tham chiếu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/04_stage_2_audio_analysis.md`
- Schema: `docs/schemas/audio_segments.schema.md`
- JSON mẫu: `docs/samples/audio_segments_sample.json`
