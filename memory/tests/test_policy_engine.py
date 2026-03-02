from __future__ import annotations

import tempfile
import unittest

from memory.memory_store import MemoryStore
from memory.models import PreferenceCandidate, RuleKey, RuleValue, SemanticParse, compute_candidate_id
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
        context: dict[str, str],
        value: RuleValue,
        confidence: float,
        last_seen: float,
    ) -> PreferenceCandidate:
        key = RuleKey(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context=context,
        )
        candidate = PreferenceCandidate(
            candidate_id=compute_candidate_id(key.hash(), value),
            rule_key_hash=key.hash(),
            rule_key=key,
            rule_value=value,
            positive_count=2,
            negative_count=0,
            last_seen=last_seen,
            status="active",
            confidence=confidence,
        )
        self.store.upsert_candidate(candidate)
        return candidate

    def test_conflict_resolution_prefers_specificity_then_confidence_then_recency(self):
        wildcard = self._candidate(
            context={"workspace_mode": "default"},
            value=RuleValue(window_state="fullscreen"),
            confidence=0.95,
            last_seen=100,
        )
        exact_low_conf = self._candidate(
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            value=RuleValue(window_state="fullscreen"),
            confidence=0.6,
            last_seen=120,
        )
        exact_high_conf_old = self._candidate(
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            value=RuleValue(window_state="maximized"),
            confidence=0.7,
            last_seen=110,
        )
        exact_high_conf_new = self._candidate(
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            value=RuleValue(window_state="normal"),
            confidence=0.7,
            last_seen=130,
        )

        parse = SemanticParse(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
            raw_utterance="open program program x",
            timestamp=200,
        )

        decision = self.engine.decide(parse)
        self.assertEqual(decision.applied_rule_hashes, [exact_high_conf_new.candidate_id])
        self.assertEqual(decision.desired_state["window_state"], "normal")
        self.assertIn(wildcard.candidate_id, decision.considered_rule_hashes)
        self.assertIn(exact_low_conf.candidate_id, decision.considered_rule_hashes)
        self.assertIn(exact_high_conf_old.candidate_id, decision.considered_rule_hashes)

    def test_wildcard_context_matches_when_exact_not_present(self):
        wildcard = self._candidate(
            context={"workspace_mode": "default"},
            value=RuleValue(window_state="fullscreen"),
            confidence=0.8,
            last_seen=100,
        )

        parse = SemanticParse(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={"display_count_bucket": "2", "workspace_mode": "default"},
            raw_utterance="open program program x",
            timestamp=200,
        )

        decision = self.engine.decide(parse)
        self.assertEqual(decision.applied_rule_hashes, [wildcard.candidate_id])


if __name__ == "__main__":
    unittest.main()
