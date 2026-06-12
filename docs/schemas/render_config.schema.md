# render_config.json schema

Source of truth: `docs/details/02_data_contract.md`.

`render_config.json` is optional in MVP. Renderer can use `timeline.render_settings` directly.

## Top-level fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `output` | object |
| `audio` | object |
| `video` | object |

## `output` fields

| Field | Type |
| --- | --- |
| `path` | string |
| `width` | integer |
| `height` | integer |
| `fps` | number |
| `format` | string |

Allowed `output.format`: `mp4`.

## `audio` fields

| Field | Type |
| --- | --- |
| `voiceover_path` | string |
| `keep_original_audio` | boolean |
| `original_audio_volume` | number |

## `video` fields

| Field | Type |
| --- | --- |
| `crop_mode` | string |
| `default_transition` | string |

Allowed `crop_mode`: `fit`, `fill`, `center_crop`, `blur_background`.
Allowed `default_transition`: `cut`, `fade`, `crossfade`.
