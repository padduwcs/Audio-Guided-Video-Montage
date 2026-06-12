# Shared

Tiện ích và hằng số dùng chung giữa các module.

## Trách nhiệm

- Helper validate schema, path, ID, timestamp.
- Quy ước logging dùng chung.
- Chỉ chứa logic thật sự được nhiều module dùng lại.

## Tài liệu

- `docs/details/02_data_contract.md`
- `docs/details/01_system_architecture.md`

## Cách test (sẽ bổ sung khi có code)

- Contract reference: `python scripts/validate_json.py`
- Runtime artifacts: `python scripts/validate_json.py --input-dir data/intermediate`

## Ranh giới

- Không đặt business logic riêng của từng module.
- Không hidden shared state giữa các module.
- Không đổi hằng số contract nếu chưa cập nhật docs và samples.
