"""Interactive CLI for testing preference memory in real time."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import normalize_identifier
from .runtime import PreferenceMemoryRuntime


def parse_key_value_assignments(items: list[str]) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Expected key=value assignment, got: {item}")
        key, value = item.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid assignment (empty key): {item}")
        assignments[key] = value
    return assignments


def normalize_context_updates(assignments: dict[str, str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for key, value in assignments.items():
        if key == "display_count":
            parsed = int(value)
            if parsed < 1:
                raise ValueError("display_count must be >= 1")
            updates[key] = parsed
        elif key == "workspace_mode":
            updates[key] = normalize_identifier(value)
        else:
            raise ValueError(f"Unsupported context key: {key}")
    return updates


@dataclass(slots=True)
class ClockState:
    mode: str
    virtual_now: float
    virtual_step: float

    def consume_timestamp(self) -> float:
        if self.mode == "real":
            return time.time()

        ts = self.virtual_now
        self.virtual_now += self.virtual_step
        return ts


class InteractiveMemoryCLI:
    def __init__(
        self,
        runtime: PreferenceMemoryRuntime,
        *,
        context: dict[str, Any],
        clock: ClockState,
    ):
        self.runtime = runtime
        self.context = dict(context)
        self.clock = clock

    def run(self) -> None:
        self._print_banner()
        while True:
            try:
                prompt = self._prompt()
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                return

            if not line:
                continue

            if line.startswith(":"):
                should_exit = self._handle_command(line[1:].strip())
                if should_exit:
                    return
                continue

            self._handle_utterance(line)

    def _prompt(self) -> str:
        mode = "R" if self.clock.mode == "real" else "V"
        if self.clock.mode == "virtual":
            tinfo = f" t={self.clock.virtual_now:.1f}"
        else:
            tinfo = ""
        return (
            f"[{mode} display={self.context.get('display_count')} "
            f"workspace={self.context.get('workspace_mode')}{tinfo}] > "
        )

    def _print_banner(self) -> None:
        print("Preference Memory Interactive CLI")
        print("Type utterances directly, or use commands starting with ':'.")
        print("Use ':help' for available commands.")

    def _handle_utterance(self, utterance: str) -> None:
        timestamp = self.clock.consume_timestamp()
        result = self.runtime.process_utterance(
            utterance,
            runtime_context=self.context,
            timestamp=timestamp,
        )

        print(
            f"[{result['outcome']}] intent={result['intent']} "
            f"episode={result['episode_id'][:8]}"
        )
        if result.get("policy"):
            policy = result["policy"]
            applied = policy.get("applied_rule_hashes", [])
            desired = policy.get("desired_state", {})
            print(f"policy.applied={applied}")
            if desired:
                print(f"policy.desired_state={desired}")

        if result.get("linked_episode_id"):
            print(f"linked_episode_id={result['linked_episode_id']}")
        if result.get("learning_updates"):
            print(f"learning_updates={result['learning_updates']}")

        ui_object = result.get("ui_object")
        if ui_object:
            snapshot = self._inspect_ui_object(ui_object)
            if snapshot:
                print(f"ui_object={ui_object} snapshot={snapshot}")

    def _handle_command(self, command_line: str) -> bool:
        try:
            parts = shlex.split(command_line)
        except ValueError as exc:
            print(f"Command parse error: {exc}")
            return False

        if not parts:
            return False

        command = parts[0].lower()
        args = parts[1:]

        try:
            if command in {"quit", "exit", "q"}:
                print("Exiting.")
                return True
            if command in {"help", "h", "?"}:
                self._print_help()
                return False
            if command == "context":
                self._command_context(args)
                return False
            if command == "time":
                self._command_time(args)
                return False
            if command == "explain":
                self._command_explain()
                return False
            if command == "rules":
                self._command_rules(args)
                return False
            if command == "episodes":
                self._command_episodes(args)
                return False
            if command == "inspect":
                self._command_inspect(args)
                return False
            if command == "reset":
                self.runtime.reset()
                print("Store reset: episodes and candidates cleared.")
                return False

            print(f"Unknown command: {command}. Use :help")
            return False
        except Exception as exc:
            print(f"Command failed: {exc}")
            return False

    def _command_context(self, args: list[str]) -> None:
        if not args or args[0] in {"show", "get"}:
            print(f"context={self.context}")
            return

        assignments = parse_key_value_assignments(args)
        updates = normalize_context_updates(assignments)
        self.context.update(updates)
        print(f"updated context={self.context}")

    def _command_time(self, args: list[str]) -> None:
        if not args or args[0] in {"show", "get"}:
            print(
                f"time.mode={self.clock.mode}, "
                f"virtual_now={self.clock.virtual_now:.1f}, "
                f"virtual_step={self.clock.virtual_step:.1f}"
            )
            return

        sub = args[0]
        if sub == "mode":
            if len(args) != 2 or args[1] not in {"real", "virtual"}:
                raise ValueError("Usage: :time mode real|virtual")
            self.clock.mode = args[1]
            print(f"time.mode={self.clock.mode}")
            return
        if sub == "set":
            if len(args) != 2:
                raise ValueError("Usage: :time set <float>")
            self.clock.virtual_now = float(args[1])
            print(f"time.virtual_now={self.clock.virtual_now:.1f}")
            return
        if sub == "step":
            if len(args) != 2:
                raise ValueError("Usage: :time step <float>")
            step = float(args[1])
            if step <= 0:
                raise ValueError("step must be > 0")
            self.clock.virtual_step = step
            print(f"time.virtual_step={self.clock.virtual_step:.1f}")
            return
        if sub == "tick":
            if len(args) != 2:
                raise ValueError("Usage: :time tick <float>")
            self.clock.virtual_now += float(args[1])
            print(f"time.virtual_now={self.clock.virtual_now:.1f}")
            return

        raise ValueError("Usage: :time [show|get|mode|set|step|tick]")

    def _command_explain(self) -> None:
        print(json.dumps(self.runtime.explain_last_action(), indent=2, sort_keys=True))

    def _command_rules(self, args: list[str]) -> None:
        status_filter = args[0].lower() if args else "active"
        candidates = self.runtime.store.list_candidates()

        if status_filter != "all":
            candidates = [candidate for candidate in candidates if candidate.status == status_filter]

        if not candidates:
            print("No matching rules.")
            return

        print(f"rules({status_filter}) count={len(candidates)}")
        for candidate in candidates:
            key = candidate.rule_key.canonical_dict()
            value = candidate.rule_value.to_desired_state()
            print(
                f"- id={candidate.candidate_id[:10]} status={candidate.status} "
                f"p={candidate.positive_count} n={candidate.negative_count} "
                f"conf={candidate.confidence:.3f} last_seen={candidate.last_seen:.1f}"
            )
            print(f"  key={key}")
            print(f"  value={value}")

    def _command_episodes(self, args: list[str]) -> None:
        limit = int(args[0]) if args else 10
        episodes = self.runtime.store.list_episodes()
        if not episodes:
            print("No episodes.")
            return

        subset = episodes[-limit:]
        print(f"episodes(last {len(subset)} of {len(episodes)}):")
        for episode in subset:
            print(
                f"- ts={episode.timestamp:.1f} id={episode.episode_id[:8]} "
                f"intent={episode.parsed_intent} outcome={episode.outcome} "
                f"linked={episode.linked_episode_id}"
            )
            if episode.applied_rule_hashes:
                print(f"  applied={episode.applied_rule_hashes}")

    def _command_inspect(self, args: list[str]) -> None:
        if len(args) != 1:
            raise ValueError("Usage: :inspect <ui_object>")
        object_id = args[0]
        snapshot = self._inspect_ui_object(object_id)
        if not snapshot:
            print(f"No snapshot available for '{object_id}'.")
            return
        print(json.dumps(snapshot, indent=2, sort_keys=True))

    def _inspect_ui_object(self, object_id: str) -> dict[str, Any] | None:
        inspector = getattr(self.runtime.adapter, "get_object_snapshot", None)
        if inspector is None:
            return None
        snapshot = inspector(object_id)
        if not snapshot:
            return None
        return snapshot

    def _print_help(self) -> None:
        print(
            "Commands:\n"
            "  :help                         Show this message\n"
            "  :quit | :exit                 Exit CLI\n"
            "  :context show                 Show runtime context\n"
            "  :context key=value ...        Update context (display_count, workspace_mode)\n"
            "  :time show                    Show clock state\n"
            "  :time mode real|virtual       Switch time mode\n"
            "  :time set <float>             Set virtual clock value\n"
            "  :time step <float>            Set virtual auto-step\n"
            "  :time tick <float>            Advance virtual clock manually\n"
            "  :rules [active|candidate|blocked|all]  List rules\n"
            "  :episodes [N]                 Show last N episodes (default 10)\n"
            "  :inspect <ui_object>          Show mock UI object snapshot\n"
            "  :explain                      Explain last action\n"
            "  :reset                        Clear persisted episodes and rules\n"
            "\n"
            "Input any non-command line as a user utterance.\n"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive CLI for memory runtime")
    parser.add_argument("--data-dir", type=str, default=None, help="Path for episodes/candidates JSON files")
    parser.add_argument("--fresh", action="store_true", help="Reset store at startup")
    parser.add_argument("--display-count", type=int, default=1, help="Initial display count context")
    parser.add_argument("--workspace-mode", type=str, default="default", help="Initial workspace mode context")
    parser.add_argument(
        "--time-mode",
        choices=("virtual", "real"),
        default="virtual",
        help="Timestamp mode for requests",
    )
    parser.add_argument("--time-start", type=float, default=1000.0, help="Initial virtual time")
    parser.add_argument("--time-step", type=float, default=5.0, help="Virtual time step after each utterance")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    context = normalize_context_updates(
        {
            "display_count": str(args.display_count),
            "workspace_mode": args.workspace_mode,
        }
    )

    runtime = PreferenceMemoryRuntime(data_dir=Path(args.data_dir) if args.data_dir else None)
    if args.fresh:
        runtime.reset()

    cli = InteractiveMemoryCLI(
        runtime,
        context=context,
        clock=ClockState(mode=args.time_mode, virtual_now=args.time_start, virtual_step=args.time_step),
    )
    cli.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
