"""Learns and updates preference candidates from structured correction records."""

from __future__ import annotations

from typing import Any

from .constants import (
    CORRECTION_WINDOW_SECONDS,
    DISABLE_NEGATIVE_THRESHOLD,
    PROMOTION_MARGIN_THRESHOLD,
    PROMOTION_POSITIVE_THRESHOLD,
)
from .memory_store import MemoryStore
from .models import (
    CorrectionRecord,
    Episode,
    PlannedAction,
    PreferenceCandidate,
    RuleKey,
    RuleValue,
    canonicalize_action,
    canonicalize_context,
    canonicalize_entities,
    compute_candidate_id,
)


class PreferenceLearner:
    def __init__(
        self,
        store: MemoryStore,
        correction_window_seconds: int = CORRECTION_WINDOW_SECONDS,
    ):
        self.store = store
        self.correction_window_seconds = correction_window_seconds

    def link_correction_episode(self, correction: CorrectionRecord) -> Episode | None:
        episodes = self.store.list_episodes()
        original = correction.original.canonical_dict()
        original_without_timestamp = dict(original)
        original_without_timestamp.pop("timestamp", None)
        compatible: list[Episode] = []
        for episode in episodes:
            if episode.episode_type != "attempt":
                continue
            if episode.outcome != "success":
                continue
            if not episode.planned_action:
                continue
            planned_without_timestamp = dict(episode.planned_action)
            planned_without_timestamp.pop("timestamp", None)
            if planned_without_timestamp != original_without_timestamp:
                continue
            delta = correction.timestamp - episode.timestamp
            if delta < 0 or delta > self.correction_window_seconds:
                continue
            compatible.append(episode)

        if not compatible:
            return None
        return max(compatible, key=lambda episode: episode.timestamp)

    def rule_key_from_action(self, planned_action: PlannedAction) -> RuleKey:
        return RuleKey(
            intent=planned_action.intent,
            entities=canonicalize_entities(planned_action.entities),
            role=planned_action.role,
            context=canonicalize_context(planned_action.context),
        )

    def record_correction(
        self,
        correction: CorrectionRecord,
        correction_episode_id: str,
        matching_active_candidates: list[PreferenceCandidate],
        linked_episode_id: str | None,
    ) -> dict[str, Any]:
        changes = self.diff_actions(correction.original, correction.corrected)
        if not changes:
            return {"updated_candidates": [], "negative_updates": []}

        rule_key = self.rule_key_from_action(correction.original)
        positive_updates: list[str] = []
        negative_updates: list[str] = []

        for action_key, corrected_value in changes.items():
            rule_value = RuleValue(preferences={action_key: corrected_value})
            positive_candidate = self._get_or_create_candidate(rule_key, rule_value)
            positive_candidate.positive_count += 1
            positive_candidate.last_seen = correction.timestamp
            self._append_sources(positive_candidate, [linked_episode_id, correction_episode_id])
            self._recompute_status(positive_candidate)
            self.store.upsert_candidate(positive_candidate)
            positive_updates.append(positive_candidate.candidate_id)

            for candidate in matching_active_candidates:
                candidate_preferences = candidate.rule_value.to_preferences()
                if action_key not in candidate_preferences:
                    continue
                if candidate_preferences[action_key] == corrected_value:
                    continue
                candidate.negative_count += 1
                candidate.last_seen = correction.timestamp
                self._append_sources(candidate, [linked_episode_id, correction_episode_id])
                self._recompute_status(candidate)
                self.store.upsert_candidate(candidate)
                negative_updates.append(candidate.candidate_id)

        return {
            "updated_candidates": positive_updates,
            "negative_updates": negative_updates,
        }

    def diff_actions(
        self,
        original: PlannedAction,
        corrected: PlannedAction,
    ) -> dict[str, Any]:
        original_action = canonicalize_action(original.action)
        corrected_action = canonicalize_action(corrected.action)
        changes: dict[str, Any] = {}
        for key, value in corrected_action.items():
            if original_action.get(key) != value:
                changes[key] = value
        return changes

    def _get_or_create_candidate(self, rule_key: RuleKey, rule_value: RuleValue) -> PreferenceCandidate:
        rule_key_hash = rule_key.hash()
        candidate = self.store.find_candidate(rule_key_hash, rule_value)
        if candidate is not None:
            return candidate

        candidate_id = compute_candidate_id(rule_key_hash, rule_value)
        return PreferenceCandidate(
            candidate_id=candidate_id,
            rule_key_hash=rule_key_hash,
            rule_key=rule_key,
            rule_value=rule_value,
            status="candidate",
            confidence=0.0,
        )

    def _append_sources(self, candidate: PreferenceCandidate, episode_ids: list[str]) -> None:
        existing = set(candidate.source_episode_ids)
        for episode_id in episode_ids:
            if episode_id and episode_id not in existing:
                candidate.source_episode_ids.append(episode_id)
                existing.add(episode_id)

    def _recompute_status(self, candidate: PreferenceCandidate) -> None:
        p = candidate.positive_count
        n = candidate.negative_count
        candidate.confidence = p / (p + n + 1)

        if n >= DISABLE_NEGATIVE_THRESHOLD:
            candidate.status = "blocked"
            return

        if p >= PROMOTION_POSITIVE_THRESHOLD and (
            n == 0
            or (p - n) >= PROMOTION_MARGIN_THRESHOLD
            or candidate.status == "active"
        ):
            candidate.status = "active"
            return

        candidate.status = "candidate"
