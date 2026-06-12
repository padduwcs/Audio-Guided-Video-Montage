# matching_candidates.json schema

Source of truth: `docs/details/02_data_contract.md`.

## Top-level required fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `top_k` | integer |
| `created_at` | string |
| `items` | array |

## `items[]` required fields

| Field | Type |
| --- | --- |
| `candidate_set_id` | string |
| `audio_segment_id` | string |
| `selected_clip_id` | string/null |
| `confidence` | string |
| `candidates` | array |

Allowed `confidence`: `high`, `medium`, `low`.

## `items[].candidates[]` required fields

| Field | Type |
| --- | --- |
| `rank` | integer |
| `clip_id` | string |
| `final_score` | number |

Optional score fields on `candidates[]`: `semantic_score`, `visual_quality_score`, `duration_fit_score`, `continuity_score`, `diversity_score`, `repetition_penalty`, `bad_clip_penalty`, `reason`. Penalty fields store non-negative magnitudes in `[0.0, 1.0]` and are subtracted when computing `final_score` (see Stage 5 spec).
