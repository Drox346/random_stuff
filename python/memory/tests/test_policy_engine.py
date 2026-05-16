from __future__ import annotations

import tempfile
import unittest

from memory.memory_store import MemoryStore
from memory.models import PlannedAction, PreferenceCandidate, RuleKey, RuleValue, compute_candidate_id
from memory.policy_engine import PolicyEngine


class TestPolicyEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(data_dir=self.tmp.name)
        self.engine = PolicyEngine(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def _candidate(
        self,
        *,
        entities: dict[str, str],
        context: dict[str, str],
        value: RuleValue,
        confidence: float,
        last_seen: float,
    ) -> PreferenceCandidate:
        key = RuleKey(intent="open_widget", entities=entities, role="widget", context=context)
        candidate = PreferenceCandidate(
            candidate_id=compute_candidate_id(key.hash(), value),
            rule_key_hash=key.hash(),
            rule_key=key,
            rule_value=value,
            positive_count=3,
            negative_count=0,
            last_seen=last_seen,
            status="active",
            confidence=confidence,
        )
        self.store.upsert_candidate(candidate)
        return candidate

    def test_specific_override_beats_group_rule(self):
        group_rule = self._candidate(
            entities={"widget_group": "small_graph"},
            context={"workspace_mode": "editing"},
            value=RuleValue(preferences={"placement": "top_right"}),
            confidence=0.7,
            last_seen=100,
        )
        specific_rule = self._candidate(
            entities={"widget_group": "small_graph", "widget_id": "speed_history"},
            context={"workspace_mode": "editing"},
            value=RuleValue(preferences={"placement": "top_left"}),
            confidence=0.7,
            last_seen=110,
        )

        action = PlannedAction(
            intent="open_widget",
            entities={"widget_group": "small_graph", "widget_id": "speed_history"},
            action={"placement": "center"},
            context={"display_count": 1, "workspace_mode": "editing"},
            timestamp=1000.0,
            role="widget",
        )
        matches = self.engine.select_matches(action)
        self.assertEqual(matches[0].candidate_id, specific_rule.candidate_id)
        self.assertEqual(matches[1].candidate_id, group_rule.candidate_id)

    def test_context_specificity_beats_broader_context(self):
        broad = self._candidate(
            entities={"widget_group": "small_graph"},
            context={"workspace_mode": "editing"},
            value=RuleValue(preferences={"placement": "top_right"}),
            confidence=0.9,
            last_seen=100,
        )
        narrow = self._candidate(
            entities={"widget_group": "small_graph"},
            context={"workspace_mode": "editing", "display_count_bucket": "2"},
            value=RuleValue(preferences={"placement": "bottom_right"}),
            confidence=0.7,
            last_seen=90,
        )

        action = PlannedAction(
            intent="open_widget",
            entities={"widget_group": "small_graph", "widget_id": "latency_chart"},
            action={"placement": "center"},
            context={"display_count": 2, "workspace_mode": "editing"},
            timestamp=1000.0,
            role="widget",
        )
        matches = self.engine.select_matches(action)
        self.assertEqual(matches[0].candidate_id, narrow.candidate_id)
        self.assertEqual(matches[1].candidate_id, broad.candidate_id)


if __name__ == "__main__":
    unittest.main()
