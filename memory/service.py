"""Structured preference memory service for LLM-planned actions."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .memory_store import MemoryStore
from .models import CorrectionRecord, Episode, MatchExplanation, PlannedAction
from .policy_engine import PolicyEngine
from .preference_learner import PreferenceLearner
from .prompt_snippet_builder import PromptSnippetBuilder


class PreferenceMemoryService:
    def __init__(
        self,
        data_dir: str | Path | None = None,
        store: MemoryStore | None = None,
        learner: PreferenceLearner | None = None,
        policy_engine: PolicyEngine | None = None,
        snippet_builder: PromptSnippetBuilder | None = None,
    ):
        self.store = store or MemoryStore(data_dir=data_dir)
        self.learner = learner or PreferenceLearner(self.store)
        self.policy_engine = policy_engine or PolicyEngine(self.store)
        self.snippet_builder = snippet_builder or PromptSnippetBuilder()
        self._last_match = MatchExplanation(snippet_text="", matched_rule_hashes=[], matched_rules=[])

    def reset(self) -> None:
        self.store.clear()
        self._last_match = MatchExplanation(snippet_text="", matched_rule_hashes=[], matched_rules=[])

    def record_attempt(self, planned_action: PlannedAction | dict[str, Any]) -> dict[str, Any]:
        action = self._coerce_action(planned_action)
        matches = self.policy_engine.select_matches(action)
        snippet_text, _ = self.snippet_builder.build(self.store.get_active_preferences())
        episode = Episode(
            episode_id=self._new_episode_id(),
            episode_type="attempt",
            timestamp=action.timestamp,
            planned_action=action.to_dict(),
            original_action=None,
            corrected_action=None,
            outcome="success",
            matched_rule_hashes=[candidate.candidate_id for candidate in matches],
            snippet_text=snippet_text,
        )
        self.store.add_episode(episode)
        return {
            "episode_id": episode.episode_id,
            "matched_rule_hashes": episode.matched_rule_hashes,
            "snippet_text": snippet_text,
        }

    def record_correction(self, correction_record: CorrectionRecord | dict[str, Any]) -> dict[str, Any]:
        correction = self._coerce_correction(correction_record)
        linked_episode = self.learner.link_correction_episode(correction)
        matches = self.policy_engine.select_matches(correction.original)
        episode_id = self._new_episode_id()
        updates = self.learner.record_correction(
            correction=correction,
            correction_episode_id=episode_id,
            matching_active_candidates=matches,
            linked_episode_id=linked_episode.episode_id if linked_episode else None,
        )
        episode = Episode(
            episode_id=episode_id,
            episode_type="correction",
            timestamp=correction.timestamp,
            planned_action=None,
            original_action=correction.original.to_dict(),
            corrected_action=correction.corrected.to_dict(),
            outcome="success",
            linked_episode_id=linked_episode.episode_id if linked_episode else None,
            matched_rule_hashes=[candidate.candidate_id for candidate in matches],
        )
        self.store.add_episode(episode)
        return {
            "episode_id": episode_id,
            "linked_episode_id": episode.linked_episode_id,
            "learning_updates": updates,
        }

    def build_prompt_snippet(self) -> str:
        active_candidates = self.store.get_active_preferences()
        snippet_text, details = self.snippet_builder.build(active_candidates)
        self._last_match = MatchExplanation(
            snippet_text=snippet_text,
            matched_rule_hashes=[detail["candidate_id"] for detail in details],
            matched_rules=details,
        )
        return snippet_text

    def explain_last_match(self) -> dict[str, Any]:
        return self._last_match.to_dict()

    def _coerce_action(self, planned_action: PlannedAction | dict[str, Any]) -> PlannedAction:
        if isinstance(planned_action, PlannedAction):
            return planned_action
        payload = dict(planned_action)
        payload.setdefault("timestamp", time.time())
        return PlannedAction.from_dict(payload)

    def _coerce_correction(self, correction_record: CorrectionRecord | dict[str, Any]) -> CorrectionRecord:
        if isinstance(correction_record, CorrectionRecord):
            return correction_record
        payload = dict(correction_record)
        payload.setdefault("timestamp", time.time())
        return CorrectionRecord.from_dict(payload)

    def _new_episode_id(self) -> str:
        return uuid.uuid4().hex
