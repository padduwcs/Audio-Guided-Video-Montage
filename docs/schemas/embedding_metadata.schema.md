# embedding_metadata.json schema

Source of truth: `docs/details/02_data_contract.md`.

## Top-level required fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `model` | object |
| `created_at` | string |
| `text_embeddings` | array |
| `visual_embeddings` | array |
| `index` | object |

## `model` required fields

| Field | Type |
| --- | --- |
| `name` | string |
| `type` | string |
| `dimension` | integer |

Allowed `model.type`: `text`, `image`, `multimodal`.

## `text_embeddings[]` required fields

| Field | Type |
| --- | --- |
| `embedding_id` | string |
| `segment_id` | string |
| `source_text` | string |
| `vector_path` | string/null |

## `visual_embeddings[]` required fields

| Field | Type |
| --- | --- |
| `embedding_id` | string |
| `clip_id` | string |
| `keyframe_id` | string/null |
| `vector_path` | string/null |
