# clip_metadata.json schema

Source of truth: `docs/details/02_data_contract.md`.

## Top-level required fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `created_at` | string |
| `items` | array |

## `items[]` required fields

| Field | Type |
| --- | --- |
| `clip_id` | string |
| `video_id` | string |
| `start` | number |
| `end` | number |
| `duration` | number |
| `keyframes` | array |
| `quality_score` | number/null |

Optional `status` values: `usable`, `low_quality`, `too_short`, `error`.

MVP implementation: mỗi clip nên có `status` và `source_path`.

## `items[].keyframes[]` required fields

| Field | Type |
| --- | --- |
| `keyframe_id` | string |
| `timestamp` | number |
| `path` | string |

Optional `position` values: `start`, `middle`, `end`, `extra`.
