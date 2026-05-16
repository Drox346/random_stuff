# CLI Guide + Example Usage

The CLI works with structured JSON payloads rather than raw utterances.

## Start the CLI

```bash
python -m memory.cli --fresh --time-mode virtual --time-start 1000 --time-step 5
```

## Core commands

- `:attempt <json>`
- `:correct <json>`
- `:snippet`
- `:rules active|candidate|blocked|all`
- `:episodes [N]`
- `:explain`
- `:context display_count=2 workspace_mode=editing`
- `:time ...`
- `:reset`

## Example: learn a fullscreen preference

```text
:attempt {"intent":"open_widget","entities":{"widget_id":"navigation","widget_group":"small_graph"},"action":{"window_state":"normal"},"role":"widget","context":{}}
:correct {"original":{"intent":"open_widget","entities":{"widget_id":"navigation","widget_group":"small_graph"},"action":{"window_state":"normal"},"role":"widget","context":{}},"corrected":{"intent":"open_widget","entities":{"widget_id":"navigation","widget_group":"small_graph"},"action":{"window_state":"fullscreen"},"role":"widget","context":{}}}
:attempt {"intent":"open_widget","entities":{"widget_id":"navigation","widget_group":"small_graph"},"action":{"window_state":"normal"},"role":"widget","context":{}}
:correct {"original":{"intent":"open_widget","entities":{"widget_id":"navigation","widget_group":"small_graph"},"action":{"window_state":"normal"},"role":"widget","context":{}},"corrected":{"intent":"open_widget","entities":{"widget_id":"navigation","widget_group":"small_graph"},"action":{"window_state":"fullscreen"},"role":"widget","context":{}}}
:snippet
```

Expected result:

- the snippet should mention that the user usually prefers `navigation` to open in fullscreen
- `:rules active` should show an active preference for `window_state=fullscreen`

## Example: group rule plus specific override

The CLI does not auto-generalize multiple widgets into a group rule. For group-level testing, create rules at the desired entity scope and then use `:snippet` to verify that:

- a `widget_group` rule applies broadly
- a more specific `widget_id` rule overrides it
