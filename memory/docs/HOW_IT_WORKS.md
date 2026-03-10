# How It Works

## End-to-end flow

The service operates on structured LLM outputs, not raw text:

1. Upstream LLM or tool-calling code produces a `PlannedAction`.
2. The app may call `build_prompt_snippet()` before the next LLM decision.
3. The app records the chosen plan with `record_attempt(planned_action)`.
4. If the user corrects the result, upstream code produces a `CorrectionRecord` with:
   - the original planned action
   - the corrected planned action
5. `record_correction(...)` diffs the action payloads and updates preference candidates.

## Rule model

Rules are keyed by:

- `intent`
- normalized `entities`
- optional `role`
- whitelisted `context`

Rules store a preferred action patch such as:

- `{"window_state": "fullscreen"}`
- `{"presentation": "widget"}`
- `{"placement": "top_right"}`

## Matching and precedence

Active candidates are matched against the current `PlannedAction` and ranked by:

1. context specificity
2. entity specificity
3. confidence
4. recency
5. candidate id tie-break

That allows broad group rules plus specific overrides. A rule keyed by `widget_id=speed_history` beats a broader `widget_group=small_graph` rule.

## Prompt rendering

Active rules are rendered into a single global system-prompt snippet. Wording is derived from evidence strength:

- strong: `always` / `never`
- medium: `consistently`
- lower active confidence: `usually`

Rules below the inclusion threshold are omitted from the prompt.

## Explainability

`PreferenceMemoryService.explain_last_match()` returns:

- the rendered snippet
- matched candidate ids
- matched rules with confidence and evidence counts
