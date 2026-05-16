# Structured Preference Memory

This package learns user preferences from structured LLM action corrections and renders prompt text for future LLM calls. It does not parse raw utterances or execute UI actions.

## What it does

- Records structured planned actions.
- Learns weighted preferences from structured original vs corrected actions.
- Matches active preferences against a new planned action.
- Renders a single system-prompt snippet from all active learned rules.
- Explains which rules matched and why.

## Main API

- `PreferenceMemoryService.record_attempt(planned_action)`
- `PreferenceMemoryService.record_correction(correction_record)`
- `PreferenceMemoryService.build_prompt_snippet() -> str`
- `PreferenceMemoryService.explain_last_match() -> dict`

## Input Contract

`record_attempt(...)` accepts either a `PlannedAction` instance or a dict with this shape:

```json
{
  "intent": "open_widget",
  "entities": {
    "widget_id": "navigation",
    "widget_group": "small_graph"
  },
  "action": {
    "window_state": "normal"
  },
  "context": {
    "display_count": 1,
    "workspace_mode": "default"
  },
  "role": "widget",
  "timestamp": 1000.0
}
```

`record_correction(...)` accepts either a `CorrectionRecord` instance or a dict with this shape:

```json
{
  "original": { "...PlannedAction..." },
  "corrected": { "...PlannedAction..." },
  "timestamp": 1010.0
}
```

## Normalization And Learning

- all string fields are normalized to lowercase underscore form
- `display_count` is canonicalized into `display_count_bucket`
- learning only happens from changed keys in `corrected.action` vs `original.action`
- each changed action key becomes its own learned preference candidate
- `record_attempt(...)` stores history and match info, but does not add positive evidence by itself

Example correction delta:

```json
{
  "original": {"action": {"placement": "center", "window_state": "normal"}},
  "corrected": {"action": {"placement": "top_right", "window_state": "fullscreen"}}
}
```

This creates or reinforces two preference updates:

- `placement=top_right`
- `window_state=fullscreen`

## Prompt Output Contract

`build_prompt_snippet()` returns one global prompt block built from all active rules.

Rules are included only if they reach one of these bands:

- `strong`: confidence `>= 0.90` and support `>= 5`
- `consistent`: confidence `>= 0.75` and support `>= 3`
- `usual`: confidence `>= 0.60` and support `>= 2`

Rendered wording:

- `strong` -> `always`
- `consistent` -> `consistently`
- `usual` -> `usually`

`explain_last_match()` returns:

```json
{
  "snippet_text": "...",
  "matched_rule_hashes": ["..."],
  "matched_rules": [
    {
      "candidate_id": "...",
      "rule_key": {...},
      "rule_value": {...},
      "positive_count": 4,
      "negative_count": 0,
      "confidence": 0.8,
      "strength": "consistent"
    }
  ]
}
```

## Quickstart

Run the structured demo:

```bash
python -m memory.demo
```

Run the structured CLI:

```bash
python -m memory.cli --fresh
```

Run tests:

```bash
python -m unittest discover -s memory/tests -v
```

Example:

```python
from memory.service import PreferenceMemoryService

service = PreferenceMemoryService()
service.reset()

original = {
    "intent": "open_widget",
    "entities": {"widget_id": "navigation", "widget_group": "small_graph"},
    "action": {"window_state": "normal"},
    "context": {"display_count": 1, "workspace_mode": "default"},
    "role": "widget",
    "timestamp": 1000.0,
}
corrected = {
    **original,
    "action": {"window_state": "fullscreen"},
    "timestamp": 1010.0,
}

service.record_attempt(original)
service.record_correction({"original": original, "corrected": corrected, "timestamp": 1010.0})
snippet = service.build_prompt_snippet()
print(snippet)
print(service.explain_last_match())
```

## Docs

- `memory/docs/HOW_IT_WORKS.md`
- `memory/docs/CLI_GUIDE.md`
- `memory/docs/USAGE_IN_PROJECTS.md`
- `memory/docs/DATA_MODEL.md`
- `memory/docs/CONTEXT_SCOPES.md`
