from __future__ import annotations

import tempfile
import unittest

from memory.models import PreferenceCandidate, RuleKey, RuleValue, compute_candidate_id
from memory.runtime import PreferenceMemoryRuntime
from memory.ui_adapter import MockDynamicUIAdapter


class TestIntegrationDemo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.adapter = MockDynamicUIAdapter()
        self.runtime = PreferenceMemoryRuntime(data_dir=self.tmp.name, adapter=self.adapter)
        self.runtime.reset()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_active_candidate(
        self,
        *,
        intent: str,
        entities: dict[str, str],
        role: str,
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
        self.runtime.store.upsert_candidate(candidate)
        return candidate

    def test_end_to_end_learning_application_disable_and_context_gating(self):
        context_single = {"display_count": 1, "workspace_mode": "default"}
        context_multi = {"display_count": 2, "workspace_mode": "default"}
        t = 1_000.0

        self.runtime.process_utterance("open program Program X", runtime_context=context_single, timestamp=t)
        self.runtime.process_utterance("make it fullscreen", runtime_context=context_single, timestamp=t + 10)
        self.runtime.process_utterance("open program Program X", runtime_context=context_single, timestamp=t + 20)
        self.runtime.process_utterance("make it fullscreen", runtime_context=context_single, timestamp=t + 30)

        learned_open = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=context_single,
            timestamp=t + 40,
        )
        self.assertTrue(learned_open["policy"]["applied_rule_hashes"])
        ui_object = learned_open["ui_object"]
        snapshot = self.adapter.get_object_snapshot(ui_object)
        self.assertEqual(snapshot.get("state"), "fullscreen")

        explanation = self.runtime.explain_last_action()
        self.assertIn("matched_rule_key", explanation)
        self.assertIn("matched_rule_value", explanation)
        self.assertIn("confidence", explanation)
        self.assertIn("source_episode_ids", explanation)

        auto_1 = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=context_single,
            timestamp=t + 50,
        )
        self.assertTrue(auto_1["policy"]["applied_rule_hashes"])
        self.runtime.process_utterance("exit fullscreen", runtime_context=context_single, timestamp=t + 55)

        auto_2 = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=context_single,
            timestamp=t + 60,
        )
        self.assertTrue(auto_2["policy"]["applied_rule_hashes"])
        self.runtime.process_utterance("exit fullscreen", runtime_context=context_single, timestamp=t + 65)

        post_disable = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=context_single,
            timestamp=t + 70,
        )
        self.assertEqual(post_disable["policy"]["applied_rule_hashes"], [])

        multi_display = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=context_multi,
            timestamp=t + 80,
        )
        self.assertEqual(multi_display["policy"]["applied_rule_hashes"], [])

    def test_context_scope_precedence_with_seeded_rules(self):
        base_t = 2_000.0
        global_workspace = self._seed_active_candidate(
            intent="open_app",
            entities={},
            role="primary_window",
            context={"workspace_mode": "editing"},
            value=RuleValue(size_preset="large"),
            confidence=0.60,
            positive_count=3,
            negative_count=1,
            last_seen=base_t + 1,
        )
        app_workspace = self._seed_active_candidate(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={"workspace_mode": "editing"},
            value=RuleValue(window_state="fullscreen"),
            confidence=0.80,
            positive_count=4,
            negative_count=0,
            last_seen=base_t + 2,
        )
        app_workspace_display = self._seed_active_candidate(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={"workspace_mode": "editing", "display_count_bucket": "2"},
            value=RuleValue(window_state="maximized"),
            confidence=0.70,
            positive_count=2,
            negative_count=0,
            last_seen=base_t + 3,
        )

        editing_single = {"display_count": 1, "workspace_mode": "editing"}
        editing_dual = {"display_count": 2, "workspace_mode": "editing"}
        presenting_single = {"display_count": 1, "workspace_mode": "presenting"}

        x_dual = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=editing_dual,
            timestamp=base_t + 10,
        )
        self.assertEqual(x_dual["policy"]["applied_rule_hashes"], [app_workspace_display.candidate_id])
        self.assertEqual(self.adapter.get_object_snapshot(x_dual["ui_object"]).get("state"), "maximized")

        x_single = self.runtime.process_utterance(
            "open program Program X",
            runtime_context=editing_single,
            timestamp=base_t + 20,
        )
        self.assertEqual(x_single["policy"]["applied_rule_hashes"], [app_workspace.candidate_id])
        self.assertEqual(self.adapter.get_object_snapshot(x_single["ui_object"]).get("state"), "fullscreen")

        y_single = self.runtime.process_utterance(
            "open program Program Y",
            runtime_context=editing_single,
            timestamp=base_t + 30,
        )
        self.assertEqual(y_single["policy"]["applied_rule_hashes"], [global_workspace.candidate_id])
        self.assertEqual(self.adapter.get_object_snapshot(y_single["ui_object"]).get("size_preset"), "large")

        y_presenting = self.runtime.process_utterance(
            "open program Program Y",
            runtime_context=presenting_single,
            timestamp=base_t + 40,
        )
        self.assertEqual(y_presenting["policy"]["applied_rule_hashes"], [])


if __name__ == "__main__":
    unittest.main()
