# 03. Stage 1 — Input Processing

| | |
|---|---|
| **Module** | `input_processor/` |
| **Core docs** | [`00`](./00_project_scope.md) · [`01`](./01_system_architecture.md) · [`02`](./02_data_contract.md) |
| **Schema / Sample** | [`media_metadata.schema.md`](../schemas/media_metadata.schema.md) · [`media_metadata_sample.json`](../samples/media_metadata_sample.json) |
| **Stage spec** | File này |

---

## 1. Mục tiêu stage

Stage 1 tiếp nhận video nguồn và audio thuyết minh, kiểm tra tính hợp lệ, chuẩn hóa nếu cần, trích metadata và tạo `media_metadata.json` — cổng vào pipeline.

**Mục tiêu cụ thể:**

* Đảm bảo ít nhất một video và một audio hợp lệ.
* Kiểm tra định dạng, duration, fps, resolution, sample rate.
* Chuẩn hóa video/audio về dạng ổn định cho các stage sau.
* Sinh `video_id`, `audio_id` ổn định.
* Xuất `media_metadata.json` đúng Data Contract.
* Lưu normalized files và `input_processing_log.json` để debug.

**Không phải mục tiêu:** ASR, scene detection, matching, timeline, render (→ §3.2).

---

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  video thô + voice-over thô
              │
              ▼
         ┌────────┐
  [raw]──►│   ①   │──► ② Audio ─┐
         │ Input  │              ├──► ④ → ⑤ → ⑥ → ⑦ → ⑧
         └────────┘              │
              ▲                   └──► ③ Video ─┘
         Stage này

  ── Chi tiết Stage ① ─────────────────────────────────────

  video thô + voice-over thô
              │
              ▼
┌─────────────────────────────┐
│  ① Input Processor          │  ◄── bạn ở đây
└─────────────┬───────────────┘
              │ ghi
              ├─ media_metadata.json
              ├─ input_processing_log.json
              └─ data/normalized/*  (video mp4, audio wav)
              │
        ┌─────┴─────┐ đọc (song song)
        ▼           ▼
   ② Audio      ③ Video
   Analyzer     Analyzer
```

| | |
|---|---|
| **Đọc (IN)** | File video/audio thô từ người dùng |
| **Ghi (OUT)** | `media_metadata.json`, `input_processing_log.json`, media đã chuẩn hóa |
| **Downstream** | Stage ② và ③ đọc metadata + `normalized_path`; không đọc raw trực tiếp |

Chi tiết: [`01_system_architecture.md` §2, §4.1](./01_system_architecture.md).

---

## 3. Trách nhiệm

### 3.1. Làm (in-scope)

| # | Hành vi |
|---|---------|
| 1 | Nhận danh sách video + một audio thuyết minh |
| 2 | Validate file tồn tại, extension, FFprobe đọc được |
| 3 | Trích metadata video/audio (duration, fps, resolution, sample rate, channels) |
| 4 | Chuẩn hóa video (mp4/h264/30fps) và audio (wav/16kHz/mono) nếu bật |
| 5 | Đọc lại metadata sau normalize |
| 6 | Sinh `video_id`, `audio_id`; gán `status` (`ready`/`warning`/`error`) |
| 7 | Ghi `media_metadata.json`, `input_processing_log.json` |
| 8 | Giữ audio gốc trong normalized video nếu source có audio (mặc định) |

### 3.2. Không làm (out-of-scope)

| Hành vi | Thuộc |
|---------|-------|
| ASR, transcript, audio segment | Stage 2 |
| Scene detection, keyframe, clip | Stage 3 |
| Embedding, matching, timeline | Stage 4–6 |
| Render video cuối | Stage 8 |
| Cắt silence / trim video / đổi tốc độ audio | Ngoài phạm vi normalize |

Ranh giới kiến trúc: [`01` §8](./01_system_architecture.md).

---

## 4. Input cần đọc

### 4.1. File bắt buộc

| Nguồn | Path | Ghi chú |
|-------|------|---------|
| Video nguồn | `data/raw/video_*.{mp4,mov,mkv}` | Một hoặc nhiều file |
| Audio thuyết minh | `data/raw/voiceover.{wav,mp3,m4a}` | Đúng một file — kênh âm thanh chính video cuối |

### 4.2. Điều kiện input hợp lệ (fail-fast)

**Video (từng file):** tồn tại; extension `.mp4`/`.mov`/`.mkv`; có video stream; `duration > 0`; `width`, `height > 0`; fps đọc được.

**Audio:** tồn tại; extension `.wav`/`.mp3`/`.m4a`; có audio stream; `duration > 0`; sample rate và channels đọc được.

**Dừng stage nếu:** `audio_path` thiếu/không đọc được; `video_paths` rỗng; không nhận thư mục thay file (trừ integration expand).

### 4.3. Config nội bộ module

> Không phải Data Contract giữa các module.

```json
{
  "project_id": "demo_01",
  "video_paths": ["data/raw/video_01.mp4"],
  "audio_path": "data/raw/voiceover.mp3",
  "output_dir": "data",
  "normalize_video": true,
  "normalize_audio": true,
  "target_video": {
    "format": "mp4",
    "codec": "h264",
    "fps": 30,
    "preserve_original_audio": true
  },
  "target_audio": {
    "format": "wav",
    "sample_rate": 16000,
    "channels": 1
  }
}
```

| Key | MVP default | Ghi chú |
|-----|-------------|---------|
| `normalize_video` | `true` | Container mp4, h264, 30fps |
| `normalize_audio` | `true` | Mono 16 kHz WAV cho ASR |
| `preserve_original_audio` | `true` | Renderer cần để bật/tắt audio gốc |
| Resize 1080p | Không bắt buộc | Renderer scale/crop theo timeline |

Không bắt buộc resize video Stage 1; ưu tiên codec/container/fps ổn định.

---

## 5. Output cần tạo

### 5.1. Output chính

| File | Path mặc định | Ai đọc |
|------|---------------|--------|
| `media_metadata.json` | `data/intermediate/media_metadata.json` | Audio/Video Analyzer, Timeline, UI, Renderer, Integration |
| Normalized video | `data/normalized/video_*.mp4` | Video Analyzer, Renderer |
| Normalized audio | `data/normalized/voiceover.wav` | Audio Analyzer, Renderer |

### 5.2. Output phụ

| File | MVP | Mục đích |
|------|-----|----------|
| `input_processing_log.json` | Có | Debug: copy/transcode, metadata gốc, warnings — **không** phải contract liên module |

Nếu `media_metadata.json` và log mâu thuẫn, pipeline ưu tiên metadata.

---

## 6. Contract fields stage trực tiếp dùng

Canonical: [`02` §4](./02_data_contract.md#4-media_metadatajson) · schema · sample.

Quy ước chung (giây, relative path, ID): [`02` §2](./02_data_contract.md#2-quy-ước-chung).

### 6.1. Field stage ghi — `media_metadata.json`

| Field / nhóm | Rule bổ sung Stage 1 |
|--------------|----------------------|
| `videos[]` | Ít nhất 1 item; metadata từ file **normalized** |
| `videos[].video_id` | `video_01`, `video_02`, … theo thứ tự input (sort tên file nếu từ thư mục) |
| `videos[].status` | `ready` \| `warning` \| `error` |
| `videos[].has_audio` | Ghi đúng; `false` không tự động → `warning` |
| `audio.audio_id` | MVP: `audio_01` |
| `audio.status` | `error` → dừng pipeline |
| `*.duration`, `fps`, `width`, `height`, `sample_rate` | Sau normalize, đơn vị giây |

### 6.2. ID stage chịu trách nhiệm

```text
project_id: demo_01
video_id: video_01, video_02, ...
audio_id: audio_01
```

Không dùng tên file gốc làm ID; không khoảng trắng trong ID.

### 6.3. `status` — usable vs error

```text
usable = ready | warning
chỉ error bị loại khỏi pipeline
```

| Status | Khi nào |
|--------|---------|
| `ready` | Normalize/validate OK |
| `warning` | Vẫn xử lý được (fps lệch, resolution thấp, no audio khi config cần audio gốc, …) |
| `error` | Không đọc được, không stream, duration=0, normalize fail |

Audio `error` → pipeline dừng. Một video `error` OK nếu còn video usable khác.

---

## 7. Quy trình xử lý riêng

### 7.1. Luồng chính

```text
1. Nhận project_id, video_paths, audio_path, config
2. Validate từng file (§4.2)
3. FFprobe metadata gốc → lưu vào log (không vào media_metadata)
4. Normalize video (nếu bật): mp4/h264/30fps, giữ audio gốc, xử lý rotation/VFR
5. Normalize audio (nếu bật): wav/mono/16kHz — KHÔNG cắt silence, KHÔNG đổi speed
6. FFprobe metadata normalized
7. Gán video_id, audio_id, status
8. Ghi media_metadata.json + input_processing_log.json
```

### 7.2. Chuẩn hóa video

* Copy thay transcode nếu đã đúng format.
* Giữ audio stream gốc (`preserve_original_audio=true`); nếu loại audio ở normalized, Renderer không thể giữ audio gốc.
* Xử lý rotation metadata; VFR → CFR.
* **Không** cắt ngắn video; **không** loại video vì dài/ngắn hơn audio.

### 7.3. Chuẩn hóa audio

* Mono + 16 kHz cho ASR ổn định.
* **Không** cắt khoảng lặng đầu/cuối (lệch timestamp).
* **Không** đổi tốc độ; **không** lọc nhiễu mạnh chưa thống nhất.

### 7.4. Làm tròn

* `duration`: 2–3 chữ số thập phân.
* `fps`: nguyên nếu 24/25/30/60; giữ 29.97 nếu source VFR chưa convert.

### 7.5. Ranh giới nội dung media

Stage 1 **không được:** cắt đầu/cuối video; cắt silence audio; đổi thứ tự input; loại video vì nội dung không liên quan.

---

## 8. Error / fallback / re-run behavior

### 8.1. Phân loại lỗi

| Mức | Ví dụ | Hành vi |
|-----|-------|---------|
| **Fatal** | Audio không tồn tại/đọc được; tất cả video error | Exit ≠ 0, không metadata giả |
| **Item** | Một video broken trong batch | Video đó `error`, video khác tiếp tục |
| **Warning** | FPS/resolution không lý tưởng | `status=warning`, pipeline tiếp |

### 8.2. Re-run

| Tình huống | Hành vi |
|------------|---------|
| Cùng `project_id`, output tồn tại, không `--overwrite` | Dừng an toàn hoặc yêu cầu `project_id` khác |
| `--overwrite` | Ghi đè normalized + metadata + log |
| Input không đổi | `video_id`/`audio_id` ổn định (theo thứ tự input) |
| Không sinh ID theo timestamp | Tránh lệch mapping stage sau |
| Đã có stage sau chạy trên metadata cũ | Cân nhắc chạy lại pipeline từ Stage 1 |

Absolute path chỉ dùng runtime nội bộ FFmpeg; **không** ghi vào JSON.

---

## 9. Handoff condition

Stage sẵn sàng bàn giao khi:

| # | Điều kiện |
|---|-----------|
| 1 | `audio.status` là `ready` hoặc `warning` (không `error`) |
| 2 | Có ≥ 1 video `ready` hoặc `warning` |
| 3 | Mọi `normalized_path` của media usable tồn tại trên disk |
| 4 | `media_metadata.json` parse được, đủ required fields ([`02` §4](./02_data_contract.md)) |
| 5 | `python scripts/validate_json.py` pass trên output (nếu có validator) |

**Module nhận tiếp:** Audio Analyzer (`audio.normalized_path`); Video Analyzer (`videos[*].normalized_path`, `video_id` cho `clip_id`).

Stage sau nên kiểm tra file tồn tại trước khi xử lý.

---

## 10. Test cases

| ID | Mô tả | Input | Kỳ vọng |
|----|-------|-------|---------|
| T01 | Happy path 1 video + audio | `video_01.mp4`, `voiceover.mp3` | Normalized OK; metadata `ready`; JSON relative path |
| T02 | Nhiều video | 2 video + audio | `video_01`, `video_02`; đủ normalized |
| T03 | Video không audio gốc | video silent | `has_audio=false`, `status=ready` nếu visual OK |
| T04 | Audio không tồn tại | — | Lỗi rõ; pipeline dừng; không metadata giả |
| T05 | 1 video lỗi + 1 OK | valid + broken | Video OK xử lý; lỗi `error` trong log; pipeline tiếp nếu còn usable |
| T06 | Relative path | — | Không absolute path trong JSON |
| T07 | Schema required | — | Top-level object; đủ fields §6 |
| T08 | `warning` vẫn handoff | media warning | Usable; stage sau không bỏ qua |
| T09 | Giữ audio gốc normalized | video có audio | `has_audio=true`; stream giữ trong mp4 |
| T10 | Re-run | cùng project_id | Không overwrite → dừng; có `--overwrite` → ghi đè; ID ổn định |

```bash
python -m input_processor.main \
  --project-id demo_01 \
  --videos data/raw/video_01.mp4 \
  --audio data/raw/voiceover.mp3 \
  --output-dir data
```

---

## 11. Acceptance criteria

Module đạt MVP khi:

1. Chạy 1+ video và 1 audio hợp lệ; chạy nhiều video.
2. Tạo normalized video/audio + `media_metadata.json` + log.
3. JSON: giây, relative path, ID ổn định, không khoảng trắng ID.
4. Phân biệt `ready`/`warning`/`error`; usable = ready \| warning.
5. Video không audio gốc vẫn `ready` nếu visual OK.
6. Normalized video giữ audio gốc mặc định.
7. Audio error → dừng; một video error không dừng nếu còn usable.
8. Re-run có quy tắc `--overwrite`.
9. Audio/Video Analyzer đọc `normalized_path` và chạy tiếp.
10. Renderer tìm được normalized media qua metadata.

---

## 12. Checklist

```text
[ ] Đã đọc 00, 01, 02 và stage spec này
[ ] Validate input §4.2
[ ] Normalize video/audio §7; không cắt silence/trim
[ ] Sinh video_id, audio_id ổn định
[ ] Ghi media_metadata.json + input_processing_log.json
[ ] status ready/warning/error đúng §6.3
[ ] Không absolute path / milliseconds trong JSON
[ ] Normalized video giữ audio gốc nếu source có
[ ] --overwrite hoặc tương đương khi re-run
[ ] Test T01–T10 §10
[ ] Handoff §9 — Audio/Video Analyzer chạy tiếp
[ ] README input_processor/ có lệnh chạy
```
