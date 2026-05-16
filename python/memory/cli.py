"""Interactive CLI for structured planned-action testing."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CorrectionRecord, PlannedAction, normalize_identifier
from .service import PreferenceMemoryService


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


def parse_json_payload(payload: str) -> dict[str, Any]:
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object payload")
    return parsed


def coerce_planned_action(payload: dict[str, Any], timestamp: float) -> PlannedAction:
    action_payload = dict(payload)
    action_payload.setdefault("timestamp", timestamp)
    action_payload.setdefault("entities", {})
    action_payload.setdefault("action", {})
    action_payload.setdefault("context", {})
    return PlannedAction.from_dict(action_payload)


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
        service: PreferenceMemoryService,
        *,
        context: dict[str, Any],
        clock: ClockState,
    ):
        self.service = service
        self.context = dict(context)
        self.clock = clock

    def run(self) -> None:
        self._print_banner()
        while True:
            try:
                line = input(self._prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                return

            if not line:
                continue
            if not line.startswith(":"):
                print("Use commands starting with ':' . Use :help for syntax.")
                continue

            should_exit = self._handle_command(line[1:].strip())
            if should_exit:
                return

    def _prompt(self) -> str:
        mode = "R" if self.clock.mode == "real" else "V"
        tinfo = f" t={self.clock.virtual_now:.1f}" if self.clock.mode == "virtual" else ""
        return (
            f"[{mode} display={self.context.get('display_count')} "
            f"workspace={self.context.get('workspace_mode')}{tinfo}] > "
        )

    def _print_banner(self) -> None:
        print("Preference Memory Interactive CLI")
        print("Submit structured JSON payloads with commands starting with ':'.")
        print("Use ':help' for available commands.")

    def _handle_command(self, command_line: str) -> bool:
        if not command_line:
            return False

        command, _, remainder = command_line.partition(" ")
        command = command.lower().strip()
        remainder = remainder.strip()

        try:
            if command in {"quit", "exit", "q"}:
                print("Exiting.")
                return True
            if command in {"help", "h", "?"}:
                self._print_help()
                return False
            if command == "context":
                self._command_context(remainder.split() if remainder else [])
                return False
            if command == "time":
                self._command_time(remainder.split() if remainder else [])
                return False
            if command == "attempt":
                self._command_attempt(remainder)
                return False
            if command == "correct":
                self._command_correct(remainder)
                return False
            if command == "snippet":
                self._command_snippet(remainder)
                return False
            if command == "rules":
                self._command_rules(remainder.split() if remainder else [])
                return False
            if command == "episodes":
                self._command_episodes(remainder.split() if remainder else [])
                return False
            if command == "explain":
                self._command_explain()
                return False
            if command == "reset":
                self.service.reset()
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

        updates = normalize_context_updates(parse_key_value_assignments(args))
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

    def _command_attempt(self, remainder: str) -> None:
        if not remainder:
            raise ValueError("Usage: :attempt <json object>")
        timestamp = self.clock.consume_timestamp()
        action = self._merge_context(coerce_planned_action(parse_json_payload(remainder), timestamp))
        result = self.service.record_attempt(action)
        print(f"attempt.episode={result['episode_id'][:8]}")
        print(f"attempt.matched_rule_hashes={result['matched_rule_hashes']}")
        if result["snippet_text"]:
            print(result["snippet_text"])

    def _command_correct(self, remainder: str) -> None:
        if not remainder:
            raise ValueError("Usage: :correct <json object>")
        timestamp = self.clock.consume_timestamp()
        payload = parse_json_payload(remainder)
        original = self._merge_context(coerce_planned_action(dict(payload["original"]), timestamp))
        corrected = self._merge_context(coerce_planned_action(dict(payload["corrected"]), timestamp))
        correction = CorrectionRecord(original=original, corrected=corrected, timestamp=timestamp)
        result = self.service.record_correction(correction)
        print(f"correction.episode={result['episode_id'][:8]}")
        print(f"linked_episode_id={result['linked_episode_id']}")
        print(f"learning_updates={result['learning_updates']}")

    def _command_snippet(self, remainder: str) -> None:
        if remainder:
            raise ValueError("Usage: :snippet")
        snippet = self.service.build_prompt_snippet()
        print(snippet or "[no matching learned preferences]")

    def _command_rules(self, args: list[str]) -> None:
        status_filter = args[0].lower() if args else "active"
        candidates = self.service.store.list_candidates()
        if status_filter != "all":
            candidates = [candidate for candidate in candidates if candidate.status == status_filter]

        if not candidates:
            print("No matching rules.")
            return

        print(f"rules({status_filter}) count={len(candidates)}")
        for candidate in candidates:
            print(
                f"- id={candidate.candidate_id[:10]} status={candidate.status} "
                f"p={candidate.positive_count} n={candidate.negative_count} "
                f"conf={candidate.confidence:.3f} last_seen={candidate.last_seen:.1f}"
            )
            print(f"  key={candidate.rule_key.canonical_dict()}")
            print(f"  value={candidate.rule_value.to_preferences()}")

    def _command_episodes(self, args: list[str]) -> None:
        limit = int(args[0]) if args else 10
        episodes = self.service.store.list_episodes()
        if not episodes:
            print("No episodes.")
            return

        subset = episodes[-limit:]
        print(f"episodes(last {len(subset)} of {len(episodes)}):")
        for episode in subset:
            print(
                f"- ts={episode.timestamp:.1f} id={episode.episode_id[:8]} "
                f"type={episode.episode_type} outcome={episode.outcome} "
                f"linked={episode.linked_episode_id}"
            )
            if episode.matched_rule_hashes:
                print(f"  matched={episode.matched_rule_hashes}")

    def _command_explain(self) -> None:
        print(json.dumps(self.service.explain_last_match(), indent=2, sort_keys=True))

    def _merge_context(self, action: PlannedAction) -> PlannedAction:
        merged_context = dict(action.context)
        merged_context.update(
            normalize_context_updates(
                {
                    "display_count": str(self.context["display_count"]),
                    "workspace_mode": str(self.context["workspace_mode"]),
                }
            )
        )
        return PlannedAction(
            intent=action.intent,
            entities=action.entities,
            action=action.action,
            context=merged_context,
            timestamp=action.timestamp,
            role=action.role,
        )

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
            "  :attempt <json>               Record a planned action\n"
            "  :correct <json>               Record original/corrected planned actions\n"
            "  :snippet                      Render prompt snippet from all active rules\n"
            "  :rules [active|candidate|blocked|all]  List rules\n"
            "  :episodes [N]                 Show last N episodes (default 10)\n"
            "  :explain                      Explain last snippet match\n"
            "  :reset                        Clear persisted episodes and rules\n"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive CLI for memory service")
    parser.add_argument("--data-dir", type=str, default=None, help="Path for episodes/candidates JSON files")
    parser.add_argument("--fresh", action="store_true", help="Reset store at startup")
    parser.add_argument("--display-count", type=int, default=1, help="Initial display count context")
    parser.add_argument("--workspace-mode", type=str, default="default", help="Initial workspace mode context")
    parser.add_argument("--time-mode", choices=("virtual", "real"), default="virtual", help="Timestamp mode for requests")
    parser.add_argument("--time-start", type=float, default=1000.0, help="Initial virtual time")
    parser.add_argument("--time-step", type=float, default=5.0, help="Virtual time step after each command")
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
    service = PreferenceMemoryService(data_dir=Path(args.data_dir) if args.data_dir else None)
    if args.fresh:
        service.reset()

    InteractiveMemoryCLI(
        service,
        context=context,
        clock=ClockState(mode=args.time_mode, virtual_now=args.time_start, virtual_step=args.time_step),
    ).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
