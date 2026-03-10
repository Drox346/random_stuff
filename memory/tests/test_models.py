from __future__ import annotations

import unittest

from memory.models import PlannedAction, RuleKey, RuleValue


class TestModels(unittest.TestCase):
    def test_rule_key_hash_is_stable_across_entity_ordering(self):
        key_a = RuleKey(
            intent="open_widget",
            entities={"widget_id": "speed_history", "widget_group": "small_graph"},
            role="widget",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
        )
        key_b = RuleKey(
            intent="open_widget",
            entities={"widget_group": "small_graph", "widget_id": "speed_history"},
            role="widget",
            context={"workspace_mode": "default", "display_count_bucket": "1"},
        )
        self.assertEqual(key_a.hash(), key_b.hash())

    def test_rule_value_action_normalization_is_stable(self):
        value_a = RuleValue(preferences={"Placement": "Top Right", "always_on_top": True})
        value_b = RuleValue(preferences={"always_on_top": True, "placement": "top_right"})
        self.assertEqual(value_a.to_preferences(), value_b.to_preferences())

    def test_planned_action_context_bucket_is_canonicalized(self):
        action = PlannedAction(
            intent="open_widget",
            entities={"widget_id": "speed history"},
            action={"presentation": "Full Screen"},
            context={"display_count": 3, "workspace_mode": "Editing Session"},
            timestamp=1000.0,
            role="widget",
        )
        canonical = action.canonical_dict()
        self.assertEqual(canonical["context"], {"display_count_bucket": "3+", "workspace_mode": "editing_session"})


if __name__ == "__main__":
    unittest.main()
