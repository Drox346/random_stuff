# How It Works (Detailed)

## End-to-end pipeline

For each utterance, `PreferenceMemoryRuntime.process_utterance(...)` runs:

1. Parse utterance with `SemanticResolver` into:
   - intent
   - entities
   - role
   - context signature
2. Classify intent as base request or correction.
3. Base request path:
   - execute base action (`open_app`, `open_document`, `show_panel`, etc.)
   - resolve semantic role to current UI object via adapter
   - run `PolicyEngine.decide(...)` to get desired end-state
   - apply desired end-state ops through adapter
4. Correction path:
   - find most recent compatible base episode in correction window
   - apply correction immediately to target object
   - update learner evidence and candidate status
5. Persist an `Episode` record and update explainability trace.

## Why semantics instead of widget IDs

Dynamic UIs recreate windows/panels frequently. This system stores rules over semantic targets:

- Intent: what user is doing (`open_app`, `show_panel`, ...)
- Entities: normalized identifiers (`app=program_x`, `panel=inspector`)
- Role: semantic target (`primary_window`, `panel`)
- Context: stable environment bucket (`display_count_bucket`, `workspace_mode`)

At runtime, adapter `resolve(role, entity, handle)` maps semantics to the current ephemeral UI object.

## Learning loop

1. User performs base action.
2. User issues correction shortly after (default: 90s).
3. Learner maps correction to a `RuleValue` (for example `window_state=fullscreen`).
4. Learner updates candidate evidence:
   - positive evidence for explicit correction patterns
   - negative evidence for opposite corrections against auto-applied rules
5. Candidate status transitions:
   - `candidate` -> `active` when thresholds pass
   - `active` -> `blocked` after enough negatives

## Promotion and confidence

Configured in `memory/constants.py`:

- promotion positive threshold: `2`
- promotion margin threshold: `2`
- disable negative threshold: `2`
- correction window: `90s`

Confidence formula:

- `confidence = positive_count / (positive_count + negative_count + 1)`

## Runtime policy selection

`PolicyEngine` evaluates active rules and keeps only matching keys. It ranks matches by:

1. context specificity (`len(rule_key.context)`)
2. entity specificity (`len(rule_key.entities)`)
3. confidence (higher wins)
4. last reinforcement recency (`last_seen`)
5. candidate id as deterministic tie-breaker

Winner provides `desired_state`, which runtime applies as end-state operations.

## Explainability

`runtime.explain_last_action()` returns:

- matched rule key/value
- confidence and evidence counts
- source episode ids
- considered/applied rule ids
- per-request trace from `EventLogger`
