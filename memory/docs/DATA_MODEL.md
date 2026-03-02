# Data Model

This project persists two JSON collections under `memory/data/` by default.

## Files

- `episodes.json`: chronological action/correction history.
- `preference_candidates.json`: candidate/active/blocked preference rules.

## Episode schema

Each record is an `Episode` from `memory/models.py`.

Fields:

- `episode_id`: unique id.
- `timestamp`: float unix timestamp.
- `user_utterance`: original utterance text.
- `parsed_intent`: resolved intent.
- `parsed_entities`: normalized entity dictionary.
- `target_role`: semantic UI role.
- `context_signature`: canonical context dictionary.
- `actions_executed`: ordered list of action records.
- `outcome`: `success` or `failure`.
- `linked_episode_id`: prior episode id when this is a correction.
- `considered_rule_hashes`: ordered candidate ids considered by policy.
- `applied_rule_hashes`: winning candidate ids applied by policy.
- `auto_desired_state`: desired state produced by policy.

## Preference candidate schema

Each record is a `PreferenceCandidate`.

Fields:

- `candidate_id`: hash of `(rule_key_hash + canonical rule_value)`.
- `rule_key_hash`: hash of canonical key.
- `rule_key`:
  - `intent`
  - `entities` (sorted, normalized)
  - `role`
  - `context` (whitelisted fields only)
- `rule_value`:
  - optional `window_state`
  - optional `always_on_top`
  - optional `display`
  - optional `size_preset`
  - optional `dock_region`
  - optional `visibility`
- `positive_count`
- `negative_count`
- `last_seen`
- `status`: `candidate`, `active`, `blocked`
- `source_episode_ids`: episode ids that produced evidence
- `confidence`

## Canonicalization rules

Implemented in `memory/models.py`.

- identifiers are lowercased and whitespace-normalized with `_`
- entities are sorted by key
- context is reduced to whitelist from `memory/constants.py`:
  - `display_count_bucket` (`1`, `2`, `3+`)
  - `workspace_mode`

## Hashing

`RuleKey.hash()`:

- canonical JSON payload with sorted keys and compact separators
- `sha256` digest

Candidate id:

- `sha256(f"{rule_key_hash}:{canonical_json(rule_value)}")`

## Example episode record

```json
{
  "episode_id": "4f8...",
  "timestamp": 1040.0,
  "user_utterance": "open program Program X",
  "parsed_intent": "open_app",
  "parsed_entities": {"app": "program_x"},
  "target_role": "primary_window",
  "context_signature": {"display_count_bucket": "1", "workspace_mode": "default"},
  "actions_executed": [
    {"op": "open_app", "entity": "program_x", "success": true, "handle": "app_inst_3"},
    {"op": "set_window_state", "value": "fullscreen", "ui_object": "win_4", "success": true}
  ],
  "outcome": "success",
  "linked_episode_id": null,
  "considered_rule_hashes": ["...candidate_id..."],
  "applied_rule_hashes": ["...candidate_id..."],
  "auto_desired_state": {"window_state": "fullscreen"}
}
```
