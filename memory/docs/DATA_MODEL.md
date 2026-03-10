# Data Model

The package persists two JSON collections under `memory/data/` by default.

## Files

- `episodes.json`
- `preference_candidates.json`

## PlannedAction

Structured input from the LLM or tool layer:

- `intent`
- `entities`
- `action`
- `context`
- `timestamp`
- optional `role`

Example:

```json
{
  "intent": "open_widget",
  "entities": {"widget_id": "navigation", "widget_group": "small_graph"},
  "action": {"window_state": "fullscreen"},
  "context": {"display_count_bucket": "1", "workspace_mode": "default"},
  "role": "widget",
  "timestamp": 1000.0
}
```

## CorrectionRecord

- `original`: original `PlannedAction`
- `corrected`: corrected `PlannedAction`
- `timestamp`

## Episode schema

- `episode_id`
- `episode_type`: `attempt` or `correction`
- `timestamp`
- `planned_action`
- `original_action`
- `corrected_action`
- `outcome`
- `linked_episode_id`
- `matched_rule_hashes`
- `snippet_text`

## Preference candidate schema

- `candidate_id`
- `rule_key_hash`
- `rule_key`
- `rule_value`
- `positive_count`
- `negative_count`
- `last_seen`
- `status`
- `source_episode_ids`
- `confidence`

`rule_value` is a generic normalized action patch, for example:

```json
{"placement": "top_right"}
```

or:

```json
{"presentation": "widget"}
```

## Canonicalization

- string identifiers are normalized to lowercase underscore form
- entity keys are sorted
- action keys are sorted
- context is reduced to:
  - `display_count_bucket`
  - `workspace_mode`

## Hashing

- `RuleKey.hash()` uses canonical JSON plus `sha256`
- `candidate_id` uses `sha256(rule_key_hash + canonical rule_value)`
