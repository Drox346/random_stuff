from __future__ import annotations

import tempfile
import unittest

from memory.models import PlannedAction, PreferenceCandidate, RuleKey, RuleValue, compute_candidate_id
from memory.service import PreferenceMemoryService


class TestPreferenceMemoryService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = PreferenceMemoryService(data_dir=self.tmp.name)
        self.service.reset()

    def tearDown(self):
        self.tmp.cleanup()

    def _action(
        self,
        *,
        timestamp: float,
        widget_id: str,
        presentation: str | None = None,
        placement: str | None = None,
        workspace_mode: str = "default",
        display_count: int = 1,
    ) -> PlannedAction:
        action: dict[str, str] = {}
        if presentation is not None:
            action["presentation"] = presentation
        if placement is not None:
            action["placement"] = placement
        return PlannedAction(
            intent="open_widget",
            entities={"widget_id": widget_id, "widget_group": "small_graph"},
            action=action,
            context={"display_count": display_count, "workspace_mode": workspace_mode},
            timestamp=timestamp,
            role="widget",
        )

    def _seed_candidate(
        self,
        *,
        entities: dict[str, str],
        context: dict[str, str],
        preferences: dict[str, str],
        positive_count: int,
        negative_count: int,
        confidence: float,
        last_seen: float,
    ) -> PreferenceCandidate:
        key = RuleKey(intent="open_widget", entities=entities, role="widget", context=context)
        candidate = PreferenceCandidate(
            candidate_id=compute_candidate_id(key.hash(), RuleValue(preferences=preferences)),
            rule_key_hash=key.hash(),
            rule_key=key,
            rule_value=RuleValue(preferences=preferences),
            positive_count=positive_count,
            negative_count=negative_count,
            last_seen=last_seen,
            status="active",
            confidence=confidence,
        )
        self.service.store.upsert_candidate(candidate)
        return candidate

    def test_end_to_end_learning_and_prompt_rendering(self):
        original_a = self._action(timestamp=1000.0, widget_id="navigation", presentation="normal")
        corrected_a = self._action(timestamp=1010.0, widget_id="navigation", presentation="fullscreen")
        original_b = self._action(timestamp=1020.0, widget_id="navigation", presentation="normal")
        corrected_b = self._action(timestamp=1030.0, widget_id="navigation", presentation="fullscreen")

        self.service.record_attempt(original_a)
        self.service.record_correction({"original": original_a.to_dict(), "corrected": corrected_a.to_dict(), "timestamp": 1010.0})
        self.service.record_attempt(original_b)
        self.service.record_correction({"original": original_b.to_dict(), "corrected": corrected_b.to_dict(), "timestamp": 1030.0})

        snippet = self.service.build_prompt_snippet()
        self.assertIn("usually", snippet)
        self.assertIn("'navigation'", snippet)
        self.assertIn("open in fullscreen", snippet)

    def test_specific_widget_overrides_group_rule_in_snippet(self):
        self._seed_candidate(
            entities={"widget_group": "small_graph"},
            context={"workspace_mode": "editing"},
            preferences={"placement": "top_right"},
            positive_count=5,
            negative_count=0,
            confidence=0.9,
            last_seen=1000.0,
        )
        self._seed_candidate(
            entities={"widget_group": "small_graph", "widget_id": "speed_history"},
            context={"workspace_mode": "editing"},
            preferences={"placement": "top_left"},
            positive_count=5,
            negative_count=0,
            confidence=0.9,
            last_seen=1010.0,
        )

        snippet = self.service.build_prompt_snippet()
        self.assertIn("top left", snippet)
        self.assertIn("top right", snippet)

    def test_global_prompt_uses_positive_rule_language(self):
        self._seed_candidate(
            entities={"widget_id": "speed_history", "widget_group": "small_graph"},
            context={"workspace_mode": "default"},
            preferences={"presentation": "widget"},
            positive_count=8,
            negative_count=0,
            confidence=0.91,
            last_seen=1000.0,
        )
        snippet = self.service.build_prompt_snippet()
        self.assertIn("always wants", snippet)
        self.assertIn("open as a widget", snippet)


if __name__ == "__main__":
    unittest.main()
