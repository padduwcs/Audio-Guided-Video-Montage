# Docs Hub

Day la ban do tai lieu cua repo Audio-Guided Video Montage.

## Doc Theo Vai Tro

Nguoi dung cuoi:

1. [USER_GUIDE.md](USER_GUIDE.md)
2. [kaggle_terminal_workflow.md](kaggle_terminal_workflow.md) neu can debug Kaggle

Dev:

1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. [details/02_data_contract.md](details/02_data_contract.md)
3. Stage spec tuong ung trong `details/03` den `details/10`
4. README cua module dang sua

Integration/leader:

1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. [current_pipeline_runbook.md](current_pipeline_runbook.md)
3. [details/01_system_architecture.md](details/01_system_architecture.md)
4. [details/12_integration_plan.md](details/12_integration_plan.md)

## Tai Lieu Chinh

```text
docs/
  README.md                         file nay
  USER_GUIDE.md                     clone-and-run cho nguoi dung cuoi
  DEVELOPER_GUIDE.md                ban do repo, contract, test cho dev
  current_pipeline_runbook.md       runbook ngan theo code hien tai
  kaggle_terminal_workflow.md       chi tiet scripts/kaggle_job.py
  team_setup_and_full_pipeline.md   legacy/detail guide cho setup nhom
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

Validate sample contract:

```powershell
python scripts\validate_json.py
```

Validate runtime contract:

```powershell
python scripts\validate_json.py --input-dir data/intermediate
```

Khi thay doi format JSON, cap nhat dong thoi:

1. `details/02_data_contract.md`
2. file schema trong `schemas/`
3. sample JSON trong `samples/`
4. code doc/ghi JSON
5. README/runbook lien quan

## Trang Thai Code Hien Tai

Tat ca Stage 1-8 da co code. `integration.run_pipeline` la entrypoint chinh.
`--use-sample-data` chi dung cho contract demo; render that can media path
that.

Gioi han van hanh dang can nho:

- Stage 4 mac dinh dung real CLIP embeddings; `--fake-embeddings` chi de debug nhanh.
- Stage 7 mac dinh validate non-interactive; them `--launch-ui` de mo Gradio.
- Stage 8 on dinh nhat voi transition `cut`.
- Output trong `data/` co the bi ghi de giua cac lan chay; backup vao `runs/`
  neu can giu ket qua.
