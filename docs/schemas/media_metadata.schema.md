# media_metadata.json schema

Source of truth: `docs/details/02_data_contract.md`.

## Top-level required fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `created_at` | string |
| `videos` | array |
| `audio` | object |

## `videos[]` required fields

| Field | Type |
| --- | --- |
| `video_id` | string |
| `original_path` | string |
| `normalized_path` | string |
| `duration` | number |
| `fps` | number |
| `width` | integer |
| `height` | integer |
| `has_audio` | boolean |
| `status` | string |

Allowed `status`: `ready`, `warning`, `error`.

## `audio` required fields

| Field | Type |
| --- | --- |
| `audio_id` | string |
| `original_path` | string |
| `normalized_path` | string |
| `duration` | number |
| `sample_rate` | integer |
| `channels` | integer |
| `status` | string |

Allowed `status`: `ready`, `warning`, `error`.
