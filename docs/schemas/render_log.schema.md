# render_log.json schema

Source of truth: `docs/details/02_data_contract.md`.

Renderer creates this file to record render status and debug information.

## Top-level fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `started_at` | string |
| `finished_at` | string |
| `status` | string |
| `output_path` | string |
| `duration` | number |
| `render_time` | number |
| `warnings` | array |
| `errors` | array |

Allowed `status`: `success`, `warning`, `failed`.
