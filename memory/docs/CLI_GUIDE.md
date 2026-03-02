# CLI Guide + Example Usage

This guide focuses on interactive testing with `memory.cli`.

## Start the CLI

Fresh deterministic session (recommended for repeatable testing):

```bash
python -m memory.cli --fresh --time-mode virtual --time-start 1000 --time-step 5
```

Persist state in a custom directory:

```bash
python -m memory.cli --data-dir ./tmp/memory_state --time-mode real
```

## Core command reference

- `:help` show command list
- `:context show` print current runtime context
- `:context display_count=2 workspace_mode=editing` update context
- `:time show` print clock mode/state
- `:time mode real|virtual` switch timestamp mode
- `:time set <float>` set virtual clock value
- `:time step <float>` set automatic virtual increment per utterance
- `:time tick <float>` advance virtual clock manually
- `:rules active|candidate|blocked|all` inspect learned rules
- `:episodes [N]` show recent episodes
- `:explain` explain last action and rule selection
- `:inspect <ui_object>` inspect mock UI state snapshot
- `:reset` clear episodes + preference candidates
- `:quit` exit CLI

Any line not starting with `:` is treated as a user utterance.

## Example 1: Learn fullscreen from corrections

Commands/session:

```text
[R/V prompt omitted for brevity]
open program Program X
make it fullscreen
open program Program X
make it fullscreen
open program Program X
:rules active
:explain
```

Expected behavior:

1. First two `open` calls may have no auto-policy.
2. Two correction events (`make it fullscreen`) create enough positive evidence.
3. Third `open program Program X` auto-applies fullscreen.
4. `:rules active` shows an active candidate for:
   - `intent=open_app`
   - `entities.app=program_x`
   - `role=primary_window`
   - current context bucket
5. `:explain` shows matched rule, confidence, and source episode ids.

## Example 2: Negative evidence disables a rule

Continue from example 1:

```text
open program Program X
exit fullscreen
open program Program X
exit fullscreen
open program Program X
:rules all
```

Expected behavior:

1. Opposite corrections increment negative evidence on the auto-applied rule.
2. After two negatives, the rule becomes `blocked`.
3. Next open should not auto-apply that preference.

## Example 3: Test context scopes live

```text
:reset
:context display_count=1 workspace_mode=editing
open program Program X
make it fullscreen
open program Program X
make it fullscreen

:context display_count=2 workspace_mode=editing
open program Program X

:context display_count=1 workspace_mode=presenting
open program Program X
:episodes 20
```

What to verify:

- Learned preference is tied to context signature, not global by default.
- Different `display_count` or `workspace_mode` can prevent rule application.
- Episode list shows distinct context signatures across requests.

## Example 4: Inspect mock UI object state

After an utterance result prints `ui_object=win_XX`:

```text
:inspect win_XX
```

Useful fields in snapshot:

- `state` (`normal`, `maximized`, `fullscreen`)
- `display`
- `size_preset`
- `always_on_top`
- `capabilities`

## Tips for reliable testing

- Prefer `--time-mode virtual` when testing correction windows and thresholds.
- Use `:time set` / `:time tick` to create controlled timing gaps.
- Use `:reset` before each scenario to avoid cross-contamination.
- Use `:rules all` and `:episodes N` together for root-cause debugging.
