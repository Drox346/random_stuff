"""Learns and updates preference candidates from user corrections."""

from __future__ import annotations

from typing import Any

from .constants import (
    BASE_INTENTS,
    CORRECTION_INTENTS,
    CORRECTION_WINDOW_SECONDS,
    DISABLE_NEGATIVE_THRESHOLD,
    PROMOTION_MARGIN_THRESHOLD,
    PROMOTION_POSITIVE_THRESHOLD,
)
from .memory_store import MemoryStore
from .models import (
    Episode,
    PreferenceCandidate,
    RuleKey,
    RuleValue,
    SemanticParse,
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

    def is_correction(self, parse: SemanticParse) -> bool:
        return parse.intent in CORRECTION_INTENTS

    def link_correction_episode(self, correction: SemanticParse) -> Episode | None:
        episodes = self.store.list_episodes()
        compatible: list[Episode] = []

        for episode in episodes:
            if episode.parsed_intent not in BASE_INTENTS:
                continue
            if episode.outcome != "success":
                continue
            if episode.target_role != correction.role:
                continue
            delta = correction.timestamp - episode.timestamp
            if delta < 0 or delta > self.correction_window_seconds:
                continue
            compatible.append(episode)

        if not compatible:
            return None
        return max(compatible, key=lambda episode: episode.timestamp)

    def correction_to_rule_value(self, correction: SemanticParse) -> RuleValue:
        entities = correction.entities
        if correction.intent == "set_window_state":
            return RuleValue(window_state=entities.get("window_state"))
        if correction.intent == "set_display":
            return RuleValue(display=entities.get("display"))
        if correction.intent == "set_size_preset":
            return RuleValue(size_preset=entities.get("size_preset"))
        if correction.intent == "set_dock_region":
            return RuleValue(dock_region=entities.get("dock_region"))
        if correction.intent == "set_visibility":
            return RuleValue(visibility=entities.get("visibility"))
        if correction.intent == "set_always_on_top":
            return RuleValue(always_on_top=entities.get("always_on_top") == "true")
        return RuleValue()

    def rule_key_from_episode(self, episode: Episode) -> RuleKey:
        return RuleKey(
            intent=episode.parsed_intent,
            entities=canonicalize_entities(episode.parsed_entities),
            role=episode.target_role,
            context=canonicalize_context(episode.context_signature),
        )

    def record_correction(
        self,
        target_episode: Episode,
        correction: SemanticParse,
        success: bool,
        correction_episode_id: str,
    ) -> dict[str, Any]:
        if not success:
            return {"updated_candidates": [], "negative_updates": []}

        rule_key = self.rule_key_from_episode(target_episode)
        rule_value = self.correction_to_rule_value(correction)
        desired = rule_value.to_desired_state()
        if not desired:
            return {"updated_candidates": [], "negative_updates": []}

        negative_updates: list[str] = []
        had_opposite_auto_rule = False
        for applied_candidate_id in target_episode.applied_rule_hashes:
            applied_candidate = self.store.get_candidate_by_id(applied_candidate_id)
            if not applied_candidate:
                continue
            if not self._is_opposite(applied_candidate.rule_value, rule_value):
                continue
            had_opposite_auto_rule = True
            applied_candidate.negative_count += 1
            applied_candidate.last_seen = correction.timestamp
            self._append_sources(applied_candidate, [target_episode.episode_id, correction_episode_id])
            self._recompute_status(applied_candidate)
            self.store.upsert_candidate(applied_candidate)
            negative_updates.append(applied_candidate.candidate_id)

        if had_opposite_auto_rule:
            return {
                "updated_candidates": [],
                "negative_updates": negative_updates,
            }

        positive_candidate = self._get_or_create_candidate(rule_key, rule_value)
        positive_candidate.positive_count += 1
        positive_candidate.last_seen = correction.timestamp
        self._append_sources(positive_candidate, [target_episode.episode_id, correction_episode_id])
        self._recompute_status(positive_candidate)
        self.store.upsert_candidate(positive_candidate)

        return {
            "updated_candidates": [positive_candidate.candidate_id],
            "negative_updates": negative_updates,
        }

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

    def _is_opposite(self, existing_value: RuleValue, incoming_value: RuleValue) -> bool:
        existing = existing_value.to_desired_state()
        incoming = incoming_value.to_desired_state()

        for key, incoming_state in incoming.items():
            if key not in existing:
                continue
            if existing[key] != incoming_state:
                return True
        return False
