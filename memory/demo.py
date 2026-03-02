"""Scripted demo harness for preference memory behavior."""

from __future__ import annotations

from pathlib import Path

from .models import PreferenceCandidate, RuleKey, RuleValue, compute_candidate_id
from .runtime import PreferenceMemoryRuntime


def _seed_active_preference(
    runtime: PreferenceMemoryRuntime,
    *,
    intent: str,
    entities: dict[str, str],
    role: str,
    context: dict[str, str],
    value: RuleValue,
    confidence: float,
    positive_count: int,
    negative_count: int,
    last_seen: float,
) -> PreferenceCandidate:
    key = RuleKey(intent=intent, entities=entities, role=role, context=context)
    candidate = PreferenceCandidate(
        candidate_id=compute_candidate_id(key.hash(), value),
        rule_key_hash=key.hash(),
        rule_key=key,
        rule_value=value,
        positive_count=positive_count,
        negative_count=negative_count,
        last_seen=last_seen,
        status="active",
        confidence=confidence,
    )
    runtime.store.upsert_candidate(candidate)
    return candidate


def run_demo(data_dir: str | Path | None = None) -> dict[str, object]:
    runtime = PreferenceMemoryRuntime(data_dir=data_dir)
    runtime.reset()

    context_single = {"display_count": 1, "workspace_mode": "default"}
    context_multi = {"display_count": 2, "workspace_mode": "default"}

    t = 1_000.0

    print("=== Scenario A: Learn fullscreen preference ===")
    runtime.process_utterance("open program Program X", runtime_context=context_single, timestamp=t)
    runtime.process_utterance("make it fullscreen", runtime_context=context_single, timestamp=t + 10)
    runtime.process_utterance("open program Program X", runtime_context=context_single, timestamp=t + 20)
    runtime.process_utterance("make it fullscreen", runtime_context=context_single, timestamp=t + 30)
    third_open = runtime.process_utterance(
        "open program Program X",
        runtime_context=context_single,
        timestamp=t + 40,
    )
    print(f"Third open applied rules: {third_open['policy']['applied_rule_hashes']}")
    print(f"Explain: {runtime.explain_last_action()}")

    print("\n=== Scenario B: Negative corrections disable rule ===")
    auto_1 = runtime.process_utterance("open program Program X", runtime_context=context_single, timestamp=t + 50)
    runtime.process_utterance("exit fullscreen", runtime_context=context_single, timestamp=t + 55)
    auto_2 = runtime.process_utterance("open program Program X", runtime_context=context_single, timestamp=t + 60)
    runtime.process_utterance("exit fullscreen", runtime_context=context_single, timestamp=t + 65)
    post_disable = runtime.process_utterance(
        "open program Program X",
        runtime_context=context_single,
        timestamp=t + 70,
    )
    print(f"Auto open #1 applied rules: {auto_1['policy']['applied_rule_hashes']}")
    print(f"Auto open #2 applied rules: {auto_2['policy']['applied_rule_hashes']}")
    print(f"After negatives applied rules: {post_disable['policy']['applied_rule_hashes']}")

    print("\n=== Scenario C: Context gating (single-display rule should not apply on dual-display) ===")
    multi_display_open = runtime.process_utterance(
        "open program Program X",
        runtime_context=context_multi,
        timestamp=t + 80,
    )
    print(f"Multi-display applied rules: {multi_display_open['policy']['applied_rule_hashes']}")

    return {
        "third_open": third_open,
        "auto_1": auto_1,
        "auto_2": auto_2,
        "post_disable": post_disable,
        "multi_display_open": multi_display_open,
        "explain": runtime.explain_last_action(),
    }


def run_context_scope_demo(data_dir: str | Path | None = None) -> dict[str, object]:
    runtime = PreferenceMemoryRuntime(data_dir=data_dir)
    runtime.reset()

    base_t = 2_000.0

    print("\n=== Scenario D: Context scope precedence and fallback ===")
    global_workspace_rule = _seed_active_preference(
        runtime,
        intent="open_app",
        entities={},
        role="primary_window",
        context={"workspace_mode": "editing"},
        value=RuleValue(size_preset="large"),
        confidence=0.60,
        positive_count=3,
        negative_count=1,
        last_seen=base_t + 1,
    )
    app_workspace_rule = _seed_active_preference(
        runtime,
        intent="open_app",
        entities={"app": "program_x"},
        role="primary_window",
        context={"workspace_mode": "editing"},
        value=RuleValue(window_state="fullscreen"),
        confidence=0.80,
        positive_count=4,
        negative_count=0,
        last_seen=base_t + 2,
    )
    app_workspace_display_rule = _seed_active_preference(
        runtime,
        intent="open_app",
        entities={"app": "program_x"},
        role="primary_window",
        context={"workspace_mode": "editing", "display_count_bucket": "2"},
        value=RuleValue(window_state="maximized"),
        confidence=0.70,
        positive_count=2,
        negative_count=0,
        last_seen=base_t + 3,
    )
    print(
        "Seeded rules (global/app/app+display): "
        f"{global_workspace_rule.candidate_id[:8]}, "
        f"{app_workspace_rule.candidate_id[:8]}, "
        f"{app_workspace_display_rule.candidate_id[:8]}"
    )

    contexts = {
        "editing_single": {"display_count": 1, "workspace_mode": "editing"},
        "editing_dual": {"display_count": 2, "workspace_mode": "editing"},
        "presenting_single": {"display_count": 1, "workspace_mode": "presenting"},
    }

    program_x_dual = runtime.process_utterance(
        "open program Program X",
        runtime_context=contexts["editing_dual"],
        timestamp=base_t + 10,
    )
    program_x_single = runtime.process_utterance(
        "open program Program X",
        runtime_context=contexts["editing_single"],
        timestamp=base_t + 20,
    )
    program_y_single = runtime.process_utterance(
        "open program Program Y",
        runtime_context=contexts["editing_single"],
        timestamp=base_t + 30,
    )
    program_y_presenting = runtime.process_utterance(
        "open program Program Y",
        runtime_context=contexts["presenting_single"],
        timestamp=base_t + 40,
    )

    adapter = runtime.adapter
    x_dual_snapshot = adapter.get_object_snapshot(program_x_dual["ui_object"])
    x_single_snapshot = adapter.get_object_snapshot(program_x_single["ui_object"])
    y_single_snapshot = adapter.get_object_snapshot(program_y_single["ui_object"])
    y_presenting_snapshot = adapter.get_object_snapshot(program_y_presenting["ui_object"])

    print(
        "Program X on editing+dual -> applied:",
        program_x_dual["policy"]["applied_rule_hashes"],
        "state:",
        x_dual_snapshot.get("state"),
    )
    print(
        "Program X on editing+single -> applied:",
        program_x_single["policy"]["applied_rule_hashes"],
        "state:",
        x_single_snapshot.get("state"),
    )
    print(
        "Program Y on editing+single -> applied:",
        program_y_single["policy"]["applied_rule_hashes"],
        "size:",
        y_single_snapshot.get("size_preset"),
    )
    print(
        "Program Y on presenting+single -> applied:",
        program_y_presenting["policy"]["applied_rule_hashes"],
        "state:",
        y_presenting_snapshot.get("state"),
    )

    return {
        "seeded": {
            "global_workspace_rule": global_workspace_rule.candidate_id,
            "app_workspace_rule": app_workspace_rule.candidate_id,
            "app_workspace_display_rule": app_workspace_display_rule.candidate_id,
        },
        "program_x_dual": program_x_dual,
        "program_x_single": program_x_single,
        "program_y_single": program_y_single,
        "program_y_presenting": program_y_presenting,
        "snapshots": {
            "program_x_dual": x_dual_snapshot,
            "program_x_single": x_single_snapshot,
            "program_y_single": y_single_snapshot,
            "program_y_presenting": y_presenting_snapshot,
        },
        "explain": runtime.explain_last_action(),
    }


if __name__ == "__main__":
    run_demo()
    run_context_scope_demo()
