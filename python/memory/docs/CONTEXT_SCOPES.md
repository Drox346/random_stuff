# Context Scopes and Rule Specificity

This rework still uses low-cardinality context:

- `workspace_mode`
- `display_count_bucket`

Rules can be scoped at multiple levels:

- group level: `widget_group=small_graph`
- specific widget: `widget_group=small_graph` plus `widget_id=speed_history`
- context-specific override: add `display_count_bucket=2`

## Matching

A rule matches when every field in its key matches the current `PlannedAction`.

That means:

- fewer entity fields act as broader fallbacks
- fewer context fields act as broader context fallbacks

## Precedence

`PolicyEngine` ranks matches by:

1. context specificity
2. entity specificity
3. confidence
4. recency
5. candidate id

This gives the desired behavior:

- `widget_id=speed_history` overrides `widget_group=small_graph`
- a dual-display rule overrides a broader workspace-only rule
- unrelated contexts render no snippet
