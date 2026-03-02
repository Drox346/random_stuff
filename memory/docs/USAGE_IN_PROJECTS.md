# Using It In Your Project

## Minimal integration

```python
from memory.runtime import PreferenceMemoryRuntime

runtime = PreferenceMemoryRuntime(
    data_dir="./my_memory_data",
)

result = runtime.process_utterance(
    "open program blender",
    runtime_context={"display_count": 1, "workspace_mode": "editing"},
)

print(result["outcome"])
print(result["policy"])
```

## Interactive CLI for real-time testing

Run:

```bash
python -m memory.cli --fresh
```

Useful options:

- `--data-dir ./state_dir`: keep memory state in a custom directory
- `--time-mode real`: use wall-clock timestamps
- `--time-mode virtual --time-start 1000 --time-step 5`: deterministic simulated time
- `--display-count 2 --workspace-mode editing`: set initial context

Core CLI commands:

- `:context show`
- `:context display_count=2 workspace_mode=editing`
- `:rules active` (or `candidate`, `blocked`, `all`)
- `:episodes 20`
- `:explain`
- `:inspect <ui_object>`
- `:time mode real|virtual`
- `:time step 10`
- `:reset`

Any non-command line is treated as a user utterance and sent to `process_utterance(...)`.

## Replace mocked components

`PreferenceMemoryRuntime` accepts dependency injection for all major parts:

- `store`: use `MemoryStore` or custom persistence
- `resolver`: replace with your parser/intent model
- `learner`: customize learning policy
- `policy_engine`: customize match/rank behavior
- `adapter`: connect to your real UI runtime
- `event_logger`: send traces to your observability stack

## Custom UI adapter contract

Implement `UICapabilityAdapter` from `memory/ui_adapter.py`:

- `open_app(app_id) -> str`
- `open_document(doc_ref) -> str`
- `show_panel(panel_id) -> str`
- `resolve(role, entity, handle=None) -> str | None`
- `set_window_state(ui_object, state) -> bool`
- `move_to_display(ui_object, display_id) -> bool`
- `resize_preset(ui_object, preset) -> bool`
- `dock(ui_object, region) -> bool`
- `get_capabilities(ui_object) -> set[str]`

Optional runtime methods supported via duck typing:

- `set_visibility(ui_object, visibility)`
- `set_always_on_top(ui_object, enabled)`

## Production-oriented tips

- Keep resolver entity normalization stable across versions.
- Keep context dimensions low-cardinality to avoid overfitting.
- Use adapter capability checks to avoid false failures.
- Run periodic audits on blocked/active candidates.
- Consider schema versioning if persisting long-term data.

## Example: custom runtime assembly

```python
from memory.runtime import PreferenceMemoryRuntime
from memory.memory_store import MemoryStore
from memory.policy_engine import PolicyEngine
from memory.preference_learner import PreferenceLearner
from memory.semantic_resolver import SemanticResolver
from my_project.real_ui_adapter import RealAdapter

store = MemoryStore(data_dir="./memory_state")
resolver = SemanticResolver()  # or your own
learner = PreferenceLearner(store)
policy = PolicyEngine(store)
adapter = RealAdapter()

runtime = PreferenceMemoryRuntime(
    store=store,
    resolver=resolver,
    learner=learner,
    policy_engine=policy,
    adapter=adapter,
)
```

## Operational flow in app code

1. Build `runtime_context` from environment state (display count, workspace mode).
2. Call `process_utterance(...)` for every user request.
3. Log `result["actions"]` and `result["policy"]` for diagnostics.
4. Use `explain_last_action()` for user-facing debug command.
