# Using It In Your Project

## Minimal integration

```python
from memory.service import PreferenceMemoryService

service = PreferenceMemoryService(data_dir="./my_memory_data")

planned_action = {
    "intent": "open_widget",
    "entities": {"widget_id": "navigation", "widget_group": "small_graph"},
    "action": {"window_state": "normal"},
    "context": {"display_count": 1, "workspace_mode": "default"},
    "role": "widget",
    "timestamp": 1000.0,
}

snippet = service.build_prompt_snippet()
service.record_attempt(planned_action)
print(snippet)
```

## Exact service contract

### `record_attempt(planned_action)`

Accepted input:

- `PlannedAction`
- `dict` matching `PlannedAction`

Required fields:

- `intent`
- `entities`
- `action`
- `context`
- `timestamp`

Optional field:

- `role`

Return shape:

```json
{
  "episode_id": "abc123...",
  "matched_rule_hashes": ["..."],
  "snippet_text": "..."
}
```

Behavior:

- stores an `attempt` episode
- records which active rules match the attempt
- does not create positive evidence by itself

### `record_correction(correction_record)`

Accepted input:

- `CorrectionRecord`
- `dict` matching `CorrectionRecord`

Return shape:

```json
{
  "episode_id": "abc123...",
  "linked_episode_id": "prior_attempt_id_or_null",
  "learning_updates": {
    "updated_candidates": ["..."],
    "negative_updates": ["..."]
  }
}
```

Behavior:

- stores a `correction` episode
- compares `original.action` and `corrected.action`
- creates or reinforces one preference candidate per changed action key
- adds negative evidence to conflicting active candidates on the same action key

### `build_prompt_snippet()`

Arguments:

- none

Return:

- `str`

Behavior:

- renders one prompt block from all active learned rules
- orders rules by context specificity, entity specificity, confidence, and recency
- omits rules below the wording threshold

### `explain_last_match()`

Return:

- dict containing the rendered snippet and matched rule metadata

## Correction recording

When the user corrects the original LLM plan, send both plans:

```python
correction = {
    "original": planned_action,
    "corrected": {
        **planned_action,
        "action": {"window_state": "fullscreen"},
        "timestamp": 1010.0,
    },
    "timestamp": 1010.0,
}
service.record_correction(correction)
```

## End-to-end example with full input and generated prompt

This example shows:

- the exact structured payload your app sends into memory
- the correction records that teach memory a rule
- the prompt snippet that comes back out from all active learned rules

```python
from memory.service import PreferenceMemoryService

service = PreferenceMemoryService(data_dir="./my_memory_data")
service.reset()

# First plan proposed by the LLM or tool layer.
first_attempt = {
    "intent": "open_widget",
    "entities": {
        "widget_id": "navigation",
        "widget_group": "small_graph",
    },
    "action": {
        "window_state": "normal",
    },
    "context": {
        "display_count": 1,
        "workspace_mode": "default",
    },
    "role": "widget",
    "timestamp": 1000.0,
}

service.record_attempt(first_attempt)

# The user corrects that plan to fullscreen.
service.record_correction(
    {
        "original": first_attempt,
        "corrected": {
            **first_attempt,
            "action": {"window_state": "fullscreen"},
            "timestamp": 1010.0,
        },
        "timestamp": 1010.0,
    }
)

# A second matching correction promotes the learned preference to active.
second_attempt = {
    **first_attempt,
    "timestamp": 1020.0,
}
service.record_attempt(second_attempt)
service.record_correction(
    {
        "original": second_attempt,
        "corrected": {
            **second_attempt,
            "action": {"window_state": "fullscreen"},
            "timestamp": 1030.0,
        },
        "timestamp": 1030.0,
    }
)

# The prompt is generated from all active learned rules.
prompt_snippet = service.build_prompt_snippet()

print("PROMPT SNIPPET:")
print(prompt_snippet)
```

Generated prompt snippet from the learned rules:

```text
The system includes a memory module that tracks patterns in the user's corrections.
Use these learned preferences only when they directly apply to the current action.
Do not generalize beyond the specific cases listed.

Current learned user preferences:
- The user usually changes 'navigation' to open in fullscreen.

When responding or choosing defaults, prefer these behaviors unless the user explicitly requests something different.
```

The important point is that memory does not return a UI action. It returns prompt text derived from all active learned rules.

## Normalization and action capabilities

String normalization:

- lowercases strings
- trims whitespace
- converts spaces to underscores

Examples:

- `Top Right` -> `top_right`
- `Editing Session` -> `editing_session`
- `Speed History` -> `speed_history`

Context normalization:

- `display_count=1` -> `display_count_bucket="1"`
- `display_count=2` -> `display_count_bucket="2"`
- `display_count>=3` -> `display_count_bucket="3+"`
- `workspace_mode` is normalized

Action payload capabilities:

- keys are generic and not hardcoded to a fixed schema
- values may be `str`, `bool`, `int`, or `float`
- examples:

```json
{"window_state": "fullscreen"}
```

```json
{"presentation": "widget"}
```

```json
{"placement": "top_right", "always_on_top": true}
```

Learning behavior:

- only changed keys between `original.action` and `corrected.action` contribute evidence
- if two keys change, two separate preference updates are created

Example:

```json
{
  "original": {"action": {"placement": "center", "window_state": "normal"}},
  "corrected": {"action": {"placement": "top_right", "window_state": "fullscreen"}}
}
```

This produces:

- `placement=top_right`
- `window_state=fullscreen`

Prompt wording bands:

- `strong`: confidence `>= 0.90` and support `>= 5` -> `always`
- `consistent`: confidence `>= 0.75` and support `>= 3` -> `consistently`
- `usual`: confidence `>= 0.60` and support `>= 2` -> `usually`

Confidence formula:

- `positive_count / (positive_count + negative_count + 1)`

## Integration pattern with tool-calling

1. Build the next `PlannedAction` candidate from your LLM or tool schema.
2. Call `build_prompt_snippet()` and inject the returned text into the system prompt for the next LLM call.
3. Once the LLM commits to a plan, call `record_attempt(planned_action)`.
4. If the user corrects the action, emit a structured `CorrectionRecord` and call `record_correction(...)`.
5. Use `explain_last_match()` for debugging or trace views.

## Service dependencies

`PreferenceMemoryService` composes:

- `MemoryStore`
- `PreferenceLearner`
- `PolicyEngine`
- `PromptSnippetBuilder`

You can swap any of these if you need custom persistence, ranking, or prompt rendering.
