# evaluation_report.json schema

Source of truth: `docs/details/02_data_contract.md`.

Evaluation can be implemented after the MVP, but this schema keeps the report artifact aligned with the Data Contract.

## Top-level fields

| Field | Type |
| --- | --- |
| `schema_version` | string |
| `project_id` | string |
| `created_at` | string |
| `metrics` | object |
| `qualitative_scores` | object |
| `notes` | string |

## Common `metrics` fields

| Field | Type |
| --- | --- |
| `segment_coverage` | number |
| `average_semantic_score` | number |
| `low_confidence_rate` | number |
| `repetition_rate` | number |
| `average_duration_error` | number |
| `user_edit_count` | integer |

## Common `qualitative_scores` fields

Scores are expected to be numeric review scores.

| Field | Type |
| --- | --- |
| `semantic_alignment` | number |
| `visual_quality` | number |
| `editing_rhythm` | number |
| `ease_of_editing` | number |
| `final_usefulness` | number |
