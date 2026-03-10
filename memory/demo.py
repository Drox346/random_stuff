"""Scripted demo harness for structured preference memory behavior."""

from __future__ import annotations

from pathlib import Path

from .models import PlannedAction, PreferenceCandidate, RuleKey, RuleValue, compute_candidate_id
from .service import PreferenceMemoryService


def _seed_active_preference(
    service: PreferenceMemoryService,
    *,
    intent: str,
    entities: dict[str, str],
    role: str | None,
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
    service.store.upsert_candidate(candidate)
    return candidate


def run_demo(data_dir: str | Path | None = None) -> dict[str, object]:
    service = PreferenceMemoryService(data_dir=data_dir)
    service.reset()

    context_single = {"display_count": 1, "workspace_mode": "default"}
    context_multi = {"display_count": 2, "workspace_mode": "default"}
    t = 1_000.0

    navigation_original = {
        "intent": "open_widget",
        "entities": {"widget_id": "navigation", "widget_group": "small_graph"},
        "action": {"window_state": "normal"},
        "context": context_single,
        "role": "widget",
    }
    navigation_corrected = {
        **navigation_original,
        "action": {"window_state": "fullscreen"},
    }

    print("=== Scenario A: Learn a structured preference ===")
    service.record_attempt(PlannedAction.from_dict({**navigation_original, "timestamp": t}))
    service.record_correction(
        {
            "original": {**navigation_original, "timestamp": t},
            "corrected": {**navigation_corrected, "timestamp": t + 10},
            "timestamp": t + 10,
        }
    )
    service.record_attempt(PlannedAction.from_dict({**navigation_original, "timestamp": t + 20}))
    service.record_correction(
        {
            "original": {**navigation_original, "timestamp": t + 20},
            "corrected": {**navigation_corrected, "timestamp": t + 30},
            "timestamp": t + 30,
        }
    )
    navigation_snippet = service.build_prompt_snippet()
    print(navigation_snippet)

    print("\n=== Scenario B: Negative corrections block an old rule and promote a new one ===")
    speed_history_original = {
        "intent": "open_widget",
        "entities": {"widget_id": "speed_history", "widget_group": "small_graph"},
        "action": {"presentation": "fullscreen"},
        "context": context_single,
        "role": "widget",
    }
    speed_history_corrected = {
        **speed_history_original,
        "action": {"presentation": "widget"},
    }
    for offset in (50, 70, 90, 110, 130):
        service.record_attempt(PlannedAction.from_dict({**speed_history_original, "timestamp": t + offset}))
        service.record_correction(
            {
                "original": {**speed_history_original, "timestamp": t + offset},
                "corrected": {**speed_history_corrected, "timestamp": t + offset + 5},
                "timestamp": t + offset + 5,
            }
        )
    speed_history_snippet = service.build_prompt_snippet()
    print(speed_history_snippet)

    print("\n=== Scenario C: Global prompt output ===")
    global_snippet = service.build_prompt_snippet()
    print(global_snippet or "[no active learned preferences]")

    return {
        "navigation_snippet": navigation_snippet,
        "speed_history_snippet": speed_history_snippet,
        "global_snippet": global_snippet,
        "explain": service.explain_last_match(),
    }


def run_context_scope_demo(data_dir: str | Path | None = None) -> dict[str, object]:
    service = PreferenceMemoryService(data_dir=data_dir)
    service.reset()

    base_t = 2_000.0
    print("\n=== Scenario D: Context scope precedence and fallback ===")
    global_workspace_rule = _seed_active_preference(
        service,
        intent="open_widget",
        entities={"widget_group": "small_graph"},
        role="widget",
        context={"workspace_mode": "editing"},
        value=RuleValue(preferences={"placement": "top_right"}),
        confidence=0.75,
        positive_count=4,
        negative_count=0,
        last_seen=base_t + 1,
    )
    specific_rule = _seed_active_preference(
        service,
        intent="open_widget",
        entities={"widget_group": "small_graph", "widget_id": "speed_history"},
        role="widget",
        context={"workspace_mode": "editing"},
        value=RuleValue(preferences={"placement": "top_left"}),
        confidence=0.9,
        positive_count=6,
        negative_count=0,
        last_seen=base_t + 2,
    )
    dual_display_rule = _seed_active_preference(
        service,
        intent="open_widget",
        entities={"widget_group": "small_graph", "widget_id": "speed_history"},
        role="widget",
        context={"workspace_mode": "editing", "display_count_bucket": "2"},
        value=RuleValue(preferences={"placement": "bottom_right"}),
        confidence=0.75,
        positive_count=4,
        negative_count=0,
        last_seen=base_t + 3,
    )
    print(
        "Seeded rules (group/specific/dual-display): "
        f"{global_workspace_rule.candidate_id[:8]}, "
        f"{specific_rule.candidate_id[:8]}, "
        f"{dual_display_rule.candidate_id[:8]}"
    )

    global_scoped_snippet = service.build_prompt_snippet()

    print("global learned-rules prompt ->", global_scoped_snippet)

    return {
        "global_scoped_snippet": global_scoped_snippet,
        "explain": service.explain_last_match(),
    }


if __name__ == "__main__":
    run_demo()
    run_context_scope_demo()
