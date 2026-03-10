"""Preference matching and deterministic conflict resolution."""

from __future__ import annotations

from dataclasses import dataclass

from .memory_store import MemoryStore
from .models import PlannedAction, PreferenceCandidate


@dataclass(slots=True)
class _ScoredMatch:
    candidate: PreferenceCandidate
    context_specificity: int
    entity_specificity: int


class PolicyEngine:
    def __init__(self, store: MemoryStore):
        self.store = store

    def select_matches(self, planned_action: PlannedAction) -> list[PreferenceCandidate]:
        matches: list[_ScoredMatch] = []
        for candidate in self.store.get_active_preferences():
            if not self._is_match(candidate, planned_action):
                continue
            matches.append(
                _ScoredMatch(
                    candidate=candidate,
                    context_specificity=len(candidate.rule_key.context),
                    entity_specificity=len(candidate.rule_key.entities),
                )
            )

        if not matches:
            return []

        ordered = sorted(
            matches,
            key=lambda item: (
                item.context_specificity,
                item.entity_specificity,
                item.candidate.confidence,
                item.candidate.last_seen,
                item.candidate.candidate_id,
            ),
            reverse=True,
        )
        return [item.candidate for item in ordered]

    def _is_match(self, candidate: PreferenceCandidate, planned_action: PlannedAction) -> bool:
        key = candidate.rule_key
        if key.intent != planned_action.intent:
            return False
        if key.role and key.role != planned_action.role:
            return False

        for entity_key, entity_value in key.entities.items():
            if planned_action.entities.get(entity_key) != entity_value:
                return False

        for context_key, context_value in key.context.items():
            if str(planned_action.context.get(context_key)) != str(context_value):
                return False

        return True
