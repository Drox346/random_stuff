from __future__ import annotations

import tempfile
import unittest

from memory.memory_store import MemoryStore
from memory.models import CorrectionRecord, Episode, PlannedAction, PreferenceCandidate, RuleKey, RuleValue, compute_candidate_id
from memory.policy_engine import PolicyEngine
from memory.preference_learner import PreferenceLearner


class TestPreferenceLearner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(data_dir=self.tmp.name)
        self.learner = PreferenceLearner(self.store)
        self.engine = PolicyEngine(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def _action(self, timestamp: float, presentation: str) -> PlannedAction:
        return PlannedAction(
            intent="open_widget",
            entities={"widget_id": "speed_history", "widget_group": "small_graph"},
            action={"presentation": presentation},
            context={"display_count": 1, "workspace_mode": "default"},
            timestamp=timestamp,
            role="widget",
        )

    def test_positive_corrections_activate_preference(self):
        correction_a = CorrectionRecord(
            original=self._action(1000.0, "fullscreen"),
            corrected=self._action(1010.0, "widget"),
            timestamp=1010.0,
        )
        correction_b = CorrectionRecord(
            original=self._action(1020.0, "fullscreen"),
            corrected=self._action(1030.0, "widget"),
            timestamp=1030.0,
        )

        self.learner.record_correction(correction_a, "corr1", [], None)
        self.learner.record_correction(correction_b, "corr2", [], None)

        key = self.learner.rule_key_from_action(correction_a.original)
        candidate = self.store.find_candidate(key.hash(), RuleValue(preferences={"presentation": "widget"}))
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.positive_count, 2)
        self.assertEqual(candidate.status, "active")

    def test_negative_corrections_block_active_rule(self):
        key = RuleKey(
            intent="open_widget",
            entities={"widget_id": "speed_history", "widget_group": "small_graph"},
            role="widget",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
        )
        active_rule = PreferenceCandidate(
            candidate_id=compute_candidate_id(key.hash(), RuleValue(preferences={"presentation": "fullscreen"})),
            rule_key_hash=key.hash(),
            rule_key=key,
            rule_value=RuleValue(preferences={"presentation": "fullscreen"}),
            positive_count=3,
            negative_count=0,
            last_seen=1000.0,
            status="active",
            confidence=0.75,
        )
        self.store.upsert_candidate(active_rule)
        matches = self.engine.select_matches(self._action(1000.0, "fullscreen"))

        correction_a = CorrectionRecord(
            original=self._action(1000.0, "fullscreen"),
            corrected=self._action(1010.0, "widget"),
            timestamp=1010.0,
        )
        correction_b = CorrectionRecord(
            original=self._action(1020.0, "fullscreen"),
            corrected=self._action(1030.0, "widget"),
            timestamp=1030.0,
        )
        self.learner.record_correction(correction_a, "corr1", matches, None)
        self.learner.record_correction(correction_b, "corr2", matches, None)

        blocked = self.store.get_candidate_by_id(active_rule.candidate_id)
        self.assertIsNotNone(blocked)
        assert blocked is not None
        self.assertEqual(blocked.negative_count, 2)
        self.assertEqual(blocked.status, "blocked")

    def test_link_correction_episode_uses_matching_attempt_without_timestamp_identity(self):
        attempt = self._action(1000.0, "fullscreen")
        episode = Episode(
            episode_id="attempt1",
            episode_type="attempt",
            timestamp=1000.0,
            planned_action=attempt.to_dict(),
            original_action=None,
            corrected_action=None,
            outcome="success",
        )
        self.store.add_episode(episode)

        correction = CorrectionRecord(
            original=self._action(1005.0, "fullscreen"),
            corrected=self._action(1010.0, "widget"),
            timestamp=1010.0,
        )
        linked = self.learner.link_correction_episode(correction)
        self.assertIsNotNone(linked)
        assert linked is not None
        self.assertEqual(linked.episode_id, "attempt1")


if __name__ == "__main__":
    unittest.main()
