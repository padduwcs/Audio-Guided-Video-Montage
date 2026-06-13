# Audio-Guided Video Montage

## 1. Giới thiệu dự án

**Audio-Guided Video Montage** — hệ thống dựng video bán tự động theo audio thuyết minh, tận dụng cảnh có sẵn trong video nguồn (không sinh video mới bằng AI).

Phạm vi, MVP, demo: [`docs/details/00_project_scope.md`](docs/details/00_project_scope.md).

## 2. Mục tiêu MVP

Pipeline end-to-end và checklist chức năng bắt buộc: [`docs/details/00_project_scope.md` §8](docs/details/00_project_scope.md).

Kiến trúc module: [`docs/details/01_system_architecture.md` §2](docs/details/01_system_architecture.md).

## 3. Cấu trúc thư mục

Repo chia **bốn cụm** — đọc theo thứ tự `docs` → code pipeline → `data`/`scripts` → gốc repo:

| Cụm | Vai trò |
| --- | ------- |
| **Tài liệu** (`docs/`) | Thiết kế, Data Contract, schema, JSON mẫu — nguồn tham chiếu trước khi code |
| **Pipeline** (8 module + `integration/`, `shared/`) | Code từng stage; ghép luồng; helper dùng chung |
| **Runtime** (`data/`, `scripts/`) | Media chạy thử, artifact JSON/video, script validate và demo |
| **Gốc repo** | Onboarding, dependency, gitignore |

### Tài liệu — `docs/`

```text
docs/
├── README.md                 hub — thứ tự đọc, quy tắc làm việc
├── problem.md                phát biểu bài toán gốc
├── analysis.md               lý do thiết kế (tham khảo, không phải contract)
│
├── details/                  spec chi tiết
│   ├── 00_project_scope.md       phạm vi MVP, demo
│   ├── 01_system_architecture.md kiến trúc, luồng module
│   ├── 02_data_contract.md       contract JSON giữa các stage
│   ├── 03 … 10_stage_*.md        spec triển khai Stage 1–8
│   ├── 11_team_assignment.md     phân công nhóm
│   └── 12_integration_plan.md    kế hoạch ghép pipeline
│
├── schemas/                  field bắt buộc tối thiểu từng file JSON
└── samples/                  JSON mẫu — test độc lập, validate cross-file
```

### Code pipeline — Stage 1 → 8

```text
① input_processor/      chuẩn hóa media        → media_metadata.json
② audio_analyzer/       ASR, audio segment     → audio_segments.json      ┐
③ video_analyzer/       clip, keyframe         → clip_metadata.json       ├─ ∥ sau ①
④ embedding_indexer/    embedding + index      → embedding_metadata.json  ┘
⑤ matching_engine/      top-k clip/segment     → matching_candidates.json
⑥ timeline_planner/     bản dựng ban đầu      → timeline.json
⑦ review_ui/            review, đổi clip       → timeline.json (ghi đè)
⑧ renderer/             xuất video             → final_video.mp4, render_log.json

integration/            điều phối pipeline end-to-end (leader)
shared/                 helper JSON, path, validate — thống nhất với leader
```

### Dữ liệu & script

```text
data/
├── raw/              video/audio đầu vào (không commit file nặng)
├── normalized/       media sau Input Processor
├── keyframes/        ảnh keyframe từ Video Analyzer
├── intermediate/     JSON trung gian giữa các stage
└── final/            video render cuối

scripts/
├── validate_json.py          kiểm tra contract JSON (samples / runtime)
├── bootstrap_data_dirs.*     tạo skeleton thư mục data/
├── run_demo.*                validate mẫu (+ pipeline demo sau)
└── clean_outputs.*           dọn data/intermediate, data/final
```

### Gốc repo

```text
README.md           onboarding dự án (file này)
requirements.txt    gợi ý stack MVP — owner module bổ sung version
.gitignore          bỏ qua media/output nặng; giữ .gitkeep trong data/
```

## 4. Vai trò của các thư mục chính

Tóm tắt cấu trúc theo cụm: §3. Phần dưới bổ sung chi tiết vận hành.

### `docs/`

Chứa toàn bộ tài liệu phân tích, thiết kế, schema và hướng dẫn làm việc của dự án.

Tất cả thành viên cần đọc tài liệu trong `docs/` trước khi code.

### `integration/`

Chứa phần tích hợp pipeline tổng thể.

Thư mục này dùng để kết nối output của các module riêng lẻ thành một luồng xử lý hoàn chỉnh.

Leader hoặc người phụ trách tích hợp sẽ quản lý chính thư mục này.

### Module pipeline

Chi tiết vai trò từng module: [`docs/details/01_system_architecture.md` §4](docs/details/01_system_architecture.md). Stage spec triển khai: `docs/details/03`–`10`.

| Thư mục | Output chính |
| ------- | ------------ |
| `input_processor/` | `media_metadata.json` |
| `audio_analyzer/` | `audio_segments.json` |
| `video_analyzer/` | `clip_metadata.json` |
| `embedding_indexer/` | `embedding_metadata.json` |
| `matching_engine/` | `matching_candidates.json` |
| `timeline_planner/` | `timeline.json` |
| `review_ui/` | `timeline.json` (cập nhật) |
| `renderer/` | `final_video.mp4`, `render_log.json` |

### `shared/`

Chứa các thành phần dùng chung:

* Kiểu dữ liệu chung.
* Hàm đọc/ghi JSON.
* Validator kiểm tra schema.
* Helper xử lý thời gian, path, duration.

Không tự ý sửa các file trong `shared/` nếu chưa thống nhất với leader, vì đây là phần dùng chung giữa nhiều module.

### `data/`

Chứa dữ liệu chạy thử và output trung gian.

Không commit video/audio nặng lên GitHub nếu chưa thống nhất với nhóm.

Gợi ý cấu trúc:

```text
data/
├── raw/
├── normalized/
├── keyframes/
├── intermediate/
└── final/
```

### `scripts/`

Chứa các script hỗ trợ:

* Chạy demo.
* Kiểm tra schema JSON.
* Dọn output tạm.
* Chạy pipeline mẫu.
* Tạo cấu trúc thư mục `data/` (`bootstrap_data_dirs`).

**Trên Windows** (Git Bash hoặc WSL):

```bash
bash scripts/bootstrap_data_dirs.sh
bash scripts/run_demo.sh
bash scripts/clean_outputs.sh --yes
```

**Trên Windows** (PowerShell):

```powershell
.\scripts\bootstrap_data_dirs.ps1
.\scripts\run_demo.ps1
.\scripts\clean_outputs.ps1 -Yes
```

## 5. Thứ tự đọc tài liệu

**Thành viên mới:** đọc [`docs/README.md` §7](docs/README.md) — **khuyến nghị** `problem.md` + `analysis.md` (~20 phút), rồi theo §7.2 (`00` → `01` → `02` → stage spec full → stage liền kề §4/§5/§9).

Lộ trình đầy đủ (leader, toàn bộ tài liệu): [`docs/README.md` §7.1](docs/README.md).

## 6. Quy tắc làm việc chung

### 6.1. Code theo module

Mỗi thành viên làm việc chủ yếu trong thư mục module mình phụ trách.

Ví dụ:

* Người phụ trách audio làm trong `audio_analyzer/`.
* Người phụ trách video làm trong `video_analyzer/`.
* Người phụ trách matching làm trong `matching_engine/`.
* Người phụ trách UI làm trong `review_ui/`.
* Người phụ trách render làm trong `renderer/`.

Không sửa code trong module của người khác nếu chưa trao đổi trước.

### 6.2. Tuân thủ data contract

Các module có thể dùng thư viện và cách triển khai khác nhau, nhưng input/output phải tuân thủ schema đã thống nhất trong `docs/schemas/` và `docs/details/02_data_contract.md`.

Không tự ý đổi format JSON.

Trước khi tích hợp, chạy `python scripts/validate_json.py` (mặc định kiểm tra `docs/samples/`). Khi có output runtime: `python scripts/validate_json.py --input-dir data/intermediate`.

Nếu cần đổi schema, phải trao đổi với leader và cập nhật tài liệu trước.

### 6.3. Mỗi module cần có README riêng

Mỗi thư mục module nên có một file `README.md` mô tả:

* Module này làm gì.
* Input là gì.
* Output là gì.
* Cách chạy.
* Cách test.
* Các thư viện cần cài.
* Ví dụ output mẫu.

### 6.4. Ưu tiên output kiểm tra được

Mỗi module nên tạo output trung gian rõ ràng để dễ debug.

Ví dụ:

* Audio module xuất `audio_segments.json`.
* Video module xuất `clip_metadata.json`.
* Matching module xuất `matching_candidates.json`.
* Timeline module xuất `timeline.json`.
* Renderer xuất `final_video.mp4`.

### 6.5. Không commit file nặng

Không commit các file lớn như:

* `.mp4`
* `.mov`
* `.mkv`
* `.wav`
* `.mp3`
* File model lớn
* Output render nặng

Các file này nên đặt trong `data/` và được ignore bằng `.gitignore`.

Chỉ nên commit:

* Source code.
* File cấu hình nhỏ.
* File JSON sample nhỏ.
* Tài liệu.
* Script hỗ trợ.

## 7. Workflow Git/GitHub cho nhóm

### 7.1. Nhánh chính

* **`main`** — bản ổn định để demo và nộp sản phẩm.
* **`develop`** — nhánh tích hợp chung; mọi thay đổi hợp lệ được gom tại đây trước khi release lên `main`.
* Thành viên **luôn tạo branch làm việc từ `develop`**, không tạo từ `main`.

### 7.2. Quy ước đặt tên branch

| Tiền tố | Dùng khi |
| ------- | -------- |
| `feature/...` | Thêm hoặc hoàn thiện chức năng module |
| `fix/...` | Sửa lỗi |
| `docs/...` | Cập nhật tài liệu |
| `integration/...` | Ghép pipeline, wiring giữa các module |

Ví dụ: `feature/audio-analyzer-asr`, `docs/team-git-workflow`.

### 7.3. Quy trình làm việc

1. `git checkout develop` → `git pull origin develop`
2. Tạo branch mới theo quy ước trên.
3. Làm việc, commit thường xuyên với message rõ ràng.
4. Push branch lên GitHub và **tạo Pull Request về `develop`**.
5. **Không push trực tiếp lên `main`.**

### 7.4. Quy tắc bắt buộc khi làm việc trên Git

* **Không tự ý đổi** Data Contract, schema (`docs/schemas/`), JSON mẫu (`docs/samples/`), quy ước ID hoặc timeline format — cần thống nhất với leader trước.
* **Không commit** file media (`.mp4`, `.wav`, …), model lớn, output render nặng (xem thêm §6.5).

### 7.5. Nội dung Pull Request

Mỗi PR cần mô tả đủ các mục:

* **Phần làm** — module/file nào, thay đổi gì.
* **Cách chạy** — lệnh hoặc bước thực thi.
* **Cách test** — dữ liệu đầu vào, lệnh kiểm tra.
* **Output tạo ra** — file JSON/video và đường dẫn.
* **Giới hạn hiện tại** — phần chưa làm, edge case chưa xử lý.

### 7.6. Trước khi merge vào `develop`

Người review (hoặc tác giả PR) cần xác nhận:

1. Module chạy được độc lập.
2. Output đúng schema (`python scripts/validate_json.py` hoặc `--input-dir data/intermediate`).
3. Không ảnh hưởng module khác (không đổi contract, không sửa code module người khác nếu chưa trao đổi).

## 8. Quy trình phát triển đề xuất

### Bước 1: Đọc tài liệu

Trước khi code, mỗi thành viên cần đọc:

* Tài liệu tổng quan.
* Data contract.
* Stage spec liên quan đến module của mình.

### Bước 2: Làm module độc lập

Mỗi thành viên phát triển module của mình bằng dữ liệu mẫu trong `docs/samples/`.

Không cần chờ toàn bộ pipeline hoàn thiện mới bắt đầu làm.

### Bước 3: Xuất output đúng schema

Mỗi module phải xuất output đúng schema để module sau có thể sử dụng.

Ví dụ:

```text
audio_analyzer
→ audio_segments.json
→ matching_engine sử dụng
```

### Bước 4: Test module riêng

Mỗi module cần có cách test riêng trước khi tích hợp.

Ví dụ:

* Audio module test bằng audio ngắn.
* Video module test bằng video ngắn.
* Matching module test bằng JSON mẫu.
* Renderer test bằng `timeline_sample.json`, `media_metadata_sample.json` và `render_config_sample.json`.

### Bước 5: Tích hợp dần

Sau khi module chạy độc lập, leader sẽ tích hợp từng phần vào pipeline chung trong `integration/`.

Không chờ tất cả module hoàn hảo mới tích hợp.

### Bước 6: Chạy demo end-to-end

Mục tiêu cuối là chạy được một demo hoàn chỉnh:

```text
Input video/audio
→ intermediate JSON files
→ review/update timeline
→ final_video.mp4
```

## 9. Output trung gian chuẩn

Các file output trung gian quan trọng gồm:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
embedding_metadata.json
embedding/index files
matching_candidates.json
timeline.json
render_log.json
```

Artifact cuối cùng:

```text
final_video.mp4
```

Ý nghĩa từng file sẽ được mô tả chi tiết trong `docs/details/02_data_contract.md` và `docs/schemas/`.

## 10. Nguyên tắc tích hợp

Khi tích hợp module, cần kiểm tra theo thứ tự:

1. File output có tồn tại không?
2. JSON có đúng format không?
3. Các field bắt buộc có đủ không?
4. Đơn vị thời gian có thống nhất không?
5. `clip_id`, `segment_id`, `video_id` có khớp giữa các file không?
6. Module sau có đọc được output của module trước không?
7. Pipeline có chạy được với dữ liệu mẫu không?

Nếu có lỗi, ưu tiên kiểm tra file JSON trung gian trước khi sửa code.

## 11. Quy ước chung

### 11.1. Đơn vị thời gian

Tất cả thời gian trong JSON sử dụng đơn vị giây.

Ví dụ:

```json
{
  "start": 12.5,
  "end": 18.2
}
```

### 11.2. Score

Các điểm số nên nằm trong khoảng từ `0.0` đến `1.0`.

Ví dụ:

```json
{
  "semantic_score": 0.82,
  "visual_quality_score": 0.76,
  "final_score": 0.79
}
```

### 11.3. Confidence

Confidence dùng ba mức chính:

```text
high
medium
low
```

### 11.4. ID

ID nên đặt ngắn gọn, dễ đọc và thống nhất.

Ví dụ:

```text
video_01
a001
v01_c003
candidates_a001
```

## 12. Phân công module tổng quát

| Vai trò              | Thư mục chính                      | Output chính                  |
| -------------------- | ---------------------------------- | ----------------------------- |
| Leader / Integration | `docs/`, `integration/`, `shared/` | Schema, pipeline, sample data |
| Input Processing     | `input_processor/`                 | `media_metadata.json`         |
| Audio / NLP          | `audio_analyzer/`                  | `audio_segments.json`         |
| Video / CV           | `video_analyzer/`                  | `clip_metadata.json`          |
| Embedding / Indexing | `embedding_indexer/`               | `embedding_metadata.json`, embedding/index files |
| Matching / Retrieval | `matching_engine/`                 | `matching_candidates.json`    |
| Timeline Planning    | `timeline_planner/`                | `timeline.json`               |
| UI Review            | `review_ui/`                       | Updated `timeline.json`       |
| Rendering            | `renderer/`                        | `final_video.mp4`, `render_log.json` |

Một thành viên có thể phụ trách nhiều module tùy theo phân công thực tế.

## 13. Trạng thái hiện tại

Repo sẵn sàng cho giai đoạn triển khai module:

* Tài liệu thiết kế và Data Contract đã thống nhất.
* Schema và mẫu JSON trong `docs/samples/` đã validate cross-file.
* Chưa có implementation code; bắt đầu từ module trong `docs/details/11_team_assignment.md`.

Trước tích hợp: `python scripts/validate_json.py` (samples) và `python scripts/validate_json.py --input-dir data/intermediate` (output runtime).

## 14. Mục tiêu làm việc của repo

Repo này không chỉ chứa code, mà còn là nơi thống nhất cách cả nhóm hiểu và phát triển dự án.

Mỗi phần code cần bám theo tài liệu thiết kế, đặc biệt là:

* Scope MVP.
* Kiến trúc hệ thống.
* Data Contract.
* Stage specification.
* Kế hoạch tích hợp.

Nếu có thay đổi lớn trong cách làm, cần cập nhật tài liệu tương ứng để cả nhóm không bị lệch hướng.
