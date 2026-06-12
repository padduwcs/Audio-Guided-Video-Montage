# timeline.json schema

Source of truth: `docs/details/02_data_contract.md`.

## Top-level required fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `audio_id` | string |
| `created_at` | string |
| `updated_at` | string |
| `render_settings` | object |
| `items` | array |

## `render_settings` required fields

| Field | Type |
| --- | --- |
| `width` | integer |
| `height` | integer |
| `fps` | number |
| `format` | string |

Allowed `format`: `mp4`.
Allowed `default_transition`: `cut`, `fade`, `crossfade`.
Allowed `crop_mode`: `fit`, `fill`, `center_crop`, `blur_background`.

## `items[]` required fields

| Field | Type |
| --- | --- |
| `segment_id` | string |
| `audio_start` | number |
| `audio_end` | number |
| `duration` | number |
| `text` | string |
| `confidence` | string |
| `score` | number/null |
| `visual_items` | array |
| `candidates_ref` | string/null |

`text` must exactly match `audio_segments.items[].text` for the same `segment_id`. `audio_start` / `audio_end` / `duration` must match the corresponding audio segment timestamps.

`visual_items` may be empty when no clip is selected; MVP Renderer fails on such segments.

Allowed `confidence`: `high`, `medium`, `low`.

## `items[].visual_items[]` required fields

| Field | Type |
| --- | --- |
| `timeline_item_id` | string |
| `clip_id` | string |
| `video_id` | string |
| `source_path` | string |
| `clip_start` | number |
| `clip_end` | number |
| `timeline_start` | number |
| `timeline_end` | number |
| `speed` | number |
| `transition` | string |

Allowed `speed` in MVP: `0.75` to `1.25`.
Allowed `transition`: `cut`, `fade`, `crossfade`.
Allowed `effect` in MVP: `null`, `none`.
