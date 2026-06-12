# audio_segments.json schema

Source of truth: `docs/details/02_data_contract.md`.

## Top-level required fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `audio_id` | string |
| `language` | string |
| `created_at` | string |
| `items` | array |

## `items[]` required fields

| Field | Type |
| --- | --- |
| `segment_id` | string |
| `start` | number |
| `end` | number |
| `duration` | number |
| `text` | string |
| `query` | string |
| `asr_confidence` | number/null |

Optional `segment_type` values: `description`, `action`, `transition`, `abstract`, `unknown`.
