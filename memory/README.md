# Preference Memory + Dynamic UI Policy (Demo)

This module implements a deterministic preference-memory system that learns from user corrections and reapplies preferences later in semantically similar contexts.

It is designed for dynamic UIs where widget IDs are ephemeral. Rules are attached to semantic keys (intent + entity + role + stable context), not to UI object IDs.

## What it does

- Learns preferences from corrections after base actions.
- Promotes candidates to active rules after evidence thresholds.
- Applies active rules at runtime through a UI capability adapter.
- Handles negative evidence (opposite corrections) and blocks rules deterministically.
- Explains which rule was used and why.

## Package layout

- `memory/models.py`: dataclasses, canonicalization, rule hashing.
- `memory/constants.py`: thresholds, context whitelist, intent groups.
- `memory/memory_store.py`: JSON persistence for episodes and candidates.
- `memory/semantic_resolver.py`: rule-based utterance to semantic parse.
- `memory/preference_learner.py`: correction linking, evidence updates, promotion/blocking.
- `memory/policy_engine.py`: rule lookup and conflict resolution.
- `memory/ui_adapter.py`: UI adapter interface + dynamic mock implementation.
- `memory/runtime.py`: end-to-end orchestrator.
- `memory/event_logger.py`: per-request debug trace.
- `memory/demo.py`: scripted demo scenarios.

## Quickstart

Run demo scenarios:

```bash
python -m memory.demo
```

Run interactive CLI:

```bash
python -m memory.cli --fresh
```

Run tests:

```bash
python -m unittest discover -s memory/tests -v
```

Use runtime directly:

```python
from memory.runtime import PreferenceMemoryRuntime

runtime = PreferenceMemoryRuntime()
runtime.reset()

runtime.process_utterance(
    "open program Program X",
    runtime_context={"display_count": 1, "workspace_mode": "default"},
)
runtime.process_utterance(
    "make it fullscreen",
    runtime_context={"display_count": 1, "workspace_mode": "default"},
)

result = runtime.process_utterance(
    "open program Program X",
    runtime_context={"display_count": 1, "workspace_mode": "default"},
)
print(result["policy"])
print(runtime.explain_last_action())
```

## Docs

- `memory/docs/HOW_IT_WORKS.md`
- `memory/docs/USAGE_IN_PROJECTS.md`
- `memory/docs/DATA_MODEL.md`
- `memory/docs/CONTEXT_SCOPES.md`
