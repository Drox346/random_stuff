"""Runtime policy lookup and deterministic conflict resolution."""

from __future__ import annotations

from dataclasses import dataclass

from .memory_store import MemoryStore
from .models import PolicyDecision, PreferenceCandidate, SemanticParse


@dataclass(slots=True)
class _ScoredMatch:
    candidate: PreferenceCandidate
    context_specificity: int
    entity_specificity: int


class PolicyEngine:
    def __init__(self, store: MemoryStore):
        self.store = store

    def decide(self, parse: SemanticParse) -> PolicyDecision:
        matches: list[_ScoredMatch] = []
        for candidate in self.store.get_active_preferences():
            if not self._is_match(candidate, parse):
                continue
            matches.append(
                _ScoredMatch(
                    candidate=candidate,
                    context_specificity=len(candidate.rule_key.context),
                    entity_specificity=len(candidate.rule_key.entities),
                )
            )

        if not matches:
            return PolicyDecision(desired_state={}, considered_rule_hashes=[], applied_rule_hashes=[])

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

        considered = [item.candidate.candidate_id for item in ordered]
        winner = ordered[0].candidate
        return PolicyDecision(
            desired_state=winner.rule_value.to_desired_state(),
            considered_rule_hashes=considered,
            applied_rule_hashes=[winner.candidate_id],
        )

    def _is_match(self, candidate: PreferenceCandidate, parse: SemanticParse) -> bool:
        key = candidate.rule_key
        if key.intent != parse.intent:
            return False
        if key.role != parse.role:
            return False

        for entity_key, entity_value in key.entities.items():
            if parse.entities.get(entity_key) != entity_value:
                return False

        for context_key, context_value in key.context.items():
            if str(parse.context.get(context_key)) != str(context_value):
                return False

        return True
