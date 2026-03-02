from __future__ import annotations

import unittest

from memory.cli import normalize_context_updates, parse_key_value_assignments


class TestCLIHelpers(unittest.TestCase):
    def test_parse_key_value_assignments(self):
        parsed = parse_key_value_assignments(["display_count=2", "workspace_mode=editing mode"])
        self.assertEqual(parsed["display_count"], "2")
        self.assertEqual(parsed["workspace_mode"], "editing mode")

    def test_parse_key_value_assignments_rejects_missing_equals(self):
        with self.assertRaises(ValueError):
            parse_key_value_assignments(["display_count", "workspace_mode=editing"])

    def test_normalize_context_updates(self):
        normalized = normalize_context_updates(
            {
                "display_count": "3",
                "workspace_mode": "Editing Session",
            }
        )
        self.assertEqual(normalized, {"display_count": 3, "workspace_mode": "editing_session"})

    def test_normalize_context_updates_rejects_unsupported_key(self):
        with self.assertRaises(ValueError):
            normalize_context_updates({"device_class": "desktop"})


if __name__ == "__main__":
    unittest.main()
