# Context Scopes and Rule Specificity

This demo supports contextual scoping with low-dimensional fields:

- `workspace_mode`
- `display_count_bucket`

Rules can be broad or narrow:

- broad: only `workspace_mode=editing`
- medium: `app=program_x` + `workspace_mode=editing`
- narrow: `app=program_x` + `workspace_mode=editing` + `display_count_bucket=2`

## Matching model

A rule matches if every key in its rule key matches the request parse.

This means a rule with fewer context keys is naturally a wildcard-like fallback.

## Precedence

When multiple active rules match, `PolicyEngine` chooses the winner by:

1. context specificity (more context keys wins)
2. entity specificity (more entity keys wins)
3. confidence (higher wins)
4. recency (`last_seen`)
5. deterministic id tie-breaker

## Why this works for dynamic UI

UI identity is resolved at runtime by role (`primary_window`, `panel`, ...).

Context scopes affect only memory lookup and do not depend on widget IDs.

## Demo scenario for scope precedence

`memory/demo.py` includes `run_context_scope_demo()` that seeds:

- global editing rule for all apps
- app-specific editing rule for `program_x`
- app+display specific editing rule for `program_x` on dual display

Expected outcome:

- Program X + editing + dual display -> most specific rule
- Program X + editing + single display -> app-specific rule
- Program Y + editing + single display -> global editing fallback rule
- Program Y + presenting + single display -> no rule
