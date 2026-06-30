# Docs Hub

Thu muc nay la nguon tham chieu cho kien truc, data contract va cach van hanh
pipeline Audio-Guided Video Montage.

## Nen Doc File Nao Truoc

Thanh vien moi muon clone ve chay demo:

1. `team_setup_and_full_pipeline.md`
2. `current_pipeline_runbook.md`
3. README cua module minh phu trach

Thanh vien code module:

1. `details/00_project_scope.md`
2. `details/01_system_architecture.md`
3. `details/02_data_contract.md`
4. Stage spec tuong ung trong `details/03` den `details/10`
5. Schema va sample JSON lien quan trong `schemas/` va `samples/`

Leader/integration:

1. Tat ca file tren
2. `details/12_integration_plan.md`
3. `integration/README.md`
4. `current_pipeline_runbook.md`

## Ban Do Tai Lieu

```text
docs/
  README.md                         file nay
  team_setup_and_full_pipeline.md   onboarding clone-and-run cho ca nhom
  current_pipeline_runbook.md       runbook ngan theo code hien tai
  kaggle_terminal_workflow.md       chi tiet scripts/kaggle_job.py
  problem.md                        bai toan goc
  analysis.md                       phan tich huong giai quyet
  design_system.md                  ghi chu UI/design neu can

  details/
    00_project_scope.md
    01_system_architecture.md
    02_data_contract.md
    03_stage_1_input_processing.md
    04_stage_2_audio_analysis.md
    05_stage_3_video_analysis.md
    06_stage_4_embedding_indexing.md
    07_stage_5_matching_engine.md
    08_stage_6_timeline_planning.md
    09_stage_7_review_ui.md
    10_stage_8_rendering.md
    11_team_assignment.md
    12_integration_plan.md

  schemas/                          schema toi thieu cho JSON contract
  samples/                          sample JSON hop le de test contract
```

## Contract Va Validation

Data contract chinh:

```text
docs/details/02_data_contract.md
```

Sample contract:

```powershell
python scripts\validate_json.py
```

Runtime contract:

```powershell
python scripts\validate_json.py --input-dir data/intermediate
```

Khi thay doi format JSON, can cap nhat dong thoi:

1. `details/02_data_contract.md`
2. file schema trong `schemas/`
3. sample JSON trong `samples/`
4. README/runbook lien quan
5. code doc/ghi JSON

## Trang Thai Code Hien Tai

Tat ca Stage 1-8 da co code. `integration.run_pipeline` la entrypoint chinh de
noi cac module. `--use-sample-data` chi dung cho contract demo; render that can
media path that.

Gioi han van hanh dang can nho:

- Stage 4 co `--fake-embeddings` de smoke test nhanh.
- Stage 7 mac dinh validate non-interactive; them `--launch-ui` de mo Gradio.
- Stage 8 on dinh nhat voi transition `cut`.
- Output trong `data/` co the bi ghi de giua cac lan chay; backup vao `runs/`
  neu can giu ket qua.
