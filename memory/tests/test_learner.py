from __future__ import annotations

import tempfile
import unittest

from memory.memory_store import MemoryStore
from memory.models import Episode, PreferenceCandidate, RuleKey, RuleValue, SemanticParse, compute_candidate_id
from memory.preference_learner import PreferenceLearner


class TestPreferenceLearner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(data_dir=self.tmp.name)
        self.learner = PreferenceLearner(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def _base_episode(self, episode_id: str, timestamp: float, applied_rule_hashes: list[str] | None = None) -> Episode:
        return Episode(
            episode_id=episode_id,
            timestamp=timestamp,
            user_utterance="open program Program X",
            parsed_intent="open_app",
            parsed_entities={"app": "program_x"},
            target_role="primary_window",
            context_signature={"display_count_bucket": "1", "workspace_mode": "default"},
            actions_executed=[{"op": "open_app", "ui_object": "win_1", "success": True}],
            outcome="success",
            applied_rule_hashes=applied_rule_hashes or [],
        )

    def test_promotion_after_two_positive_corrections(self):
        target = self._base_episode("ep1", 1_000.0)

        correction = SemanticParse(
            intent="set_window_state",
            entities={"window_state": "fullscreen"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            raw_utterance="make it fullscreen",
            timestamp=1_010.0,
        )

        self.learner.record_correction(target, correction, success=True, correction_episode_id="corr1")
        correction.timestamp = 1_020.0
        self.learner.record_correction(target, correction, success=True, correction_episode_id="corr2")

        key = self.learner.rule_key_from_episode(target)
        candidate = self.store.find_candidate(key.hash(), RuleValue(window_state="fullscreen"))
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.positive_count, 2)
        self.assertEqual(candidate.negative_count, 0)
        self.assertEqual(candidate.status, "active")

    def test_negative_evidence_blocks_preference_after_two_opposites(self):
        key = RuleKey(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
        )
        fullscreen_value = RuleValue(window_state="fullscreen")
        fullscreen_candidate = PreferenceCandidate(
            candidate_id=compute_candidate_id(key.hash(), fullscreen_value),
            rule_key_hash=key.hash(),
            rule_key=key,
            rule_value=fullscreen_value,
            positive_count=2,
            negative_count=0,
            last_seen=1_000.0,
            status="active",
            confidence=2 / 3,
        )
        self.store.upsert_candidate(fullscreen_candidate)

        target = self._base_episode("ep-open", 1_100.0, applied_rule_hashes=[fullscreen_candidate.candidate_id])
        correction = SemanticParse(
            intent="set_window_state",
            entities={"window_state": "normal"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            raw_utterance="exit fullscreen",
            timestamp=1_110.0,
        )

        self.learner.record_correction(target, correction, success=True, correction_episode_id="corr1")
        correction.timestamp = 1_120.0
        self.learner.record_correction(target, correction, success=True, correction_episode_id="corr2")

        updated = self.store.get_candidate_by_id(fullscreen_candidate.candidate_id)
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.negative_count, 2)
        self.assertEqual(updated.status, "blocked")

    def test_link_correction_to_most_recent_compatible_episode(self):
        older = self._base_episode("older", 1_000.0)
        newer = self._base_episode("newer", 1_050.0)
        self.store.add_episode(older)
        self.store.add_episode(newer)

        correction = SemanticParse(
            intent="set_window_state",
            entities={"window_state": "fullscreen"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            raw_utterance="make it fullscreen",
            timestamp=1_080.0,
        )

        linked = self.learner.link_correction_episode(correction)
        self.assertIsNotNone(linked)
        assert linked is not None
        self.assertEqual(linked.episode_id, "newer")


if __name__ == "__main__":
    unittest.main()
