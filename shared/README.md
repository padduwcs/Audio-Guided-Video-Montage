# Shared

Tiện ích và hằng số dùng chung giữa các module.

## Trách nhiệm

- Helper validate schema, path, ID, timestamp.
- Quy ước logging dùng chung.
- Chỉ chứa logic thật sự được nhiều module dùng lại.

## API chính

```python
from shared import repo_root, read_json, write_json, run_validate, DEFAULT_RENDER_SETTINGS

root = repo_root()
data = read_json(root / "docs/samples/media_metadata_sample.json")
run_validate(samples_dir=root / "docs/samples")
run_validate(input_dir=root / "data/intermediate")
```

## Tài liệu

- `docs/details/02_data_contract.md`
- `docs/details/01_system_architecture.md`

## Cách test

```powershell
python -c "from shared import repo_root; print(repo_root())"
python scripts/validate_json.py
python scripts/validate_json.py --input-dir data/intermediate
```

## Ranh giới

- Không đặt business logic riêng của từng module.
- Không hidden shared state giữa các module.
- Không đổi hằng số contract nếu chưa cập nhật docs và samples.
