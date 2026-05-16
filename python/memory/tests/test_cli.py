from __future__ import annotations

import unittest

from memory.cli import coerce_planned_action, normalize_context_updates, parse_json_payload, parse_key_value_assignments


class TestCLIHelpers(unittest.TestCase):
    def test_parse_key_value_assignments(self):
        parsed = parse_key_value_assignments(["display_count=2", "workspace_mode=editing mode"])
        self.assertEqual(parsed["display_count"], "2")
        self.assertEqual(parsed["workspace_mode"], "editing mode")

    def test_normalize_context_updates(self):
        normalized = normalize_context_updates({"display_count": "3", "workspace_mode": "Editing Session"})
        self.assertEqual(normalized, {"display_count": 3, "workspace_mode": "editing_session"})

    def test_parse_json_payload_requires_object(self):
        with self.assertRaises(ValueError):
            parse_json_payload("[1, 2, 3]")

    def test_coerce_planned_action_applies_default_timestamp(self):
        action = coerce_planned_action(
            {
                "intent": "open_widget",
                "entities": {"widget_id": "speed_history"},
                "action": {"presentation": "widget"},
                "context": {"workspace_mode": "default"},
            },
            1234.0,
        )
        self.assertEqual(action.timestamp, 1234.0)


if __name__ == "__main__":
    unittest.main()
