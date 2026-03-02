from __future__ import annotations

import unittest

from memory.models import RuleKey


class TestHashing(unittest.TestCase):
    def test_rule_key_hash_is_stable_across_entity_ordering(self):
        key_a = RuleKey(
            intent="open_app",
            entities={"app": "program_x", "feature": "settings"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
        )
        key_b = RuleKey(
            intent="open_app",
            entities={"feature": "settings", "app": "program_x"},
            role="primary_window",
            context={"workspace_mode": "default", "display_count_bucket": "1"},
        )
        self.assertEqual(key_a.hash(), key_b.hash())

    def test_context_whitelist_ignores_extra_keys(self):
        key_a = RuleKey(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={
                "display_count_bucket": "1",
                "workspace_mode": "default",
                "input_mode": "touch",
            },
        )
        key_b = RuleKey(
            intent="open_app",
            entities={"app": "program_x"},
            role="primary_window",
            context={"display_count_bucket": "1", "workspace_mode": "default"},
        )
        self.assertEqual(key_a.hash(), key_b.hash())


if __name__ == "__main__":
    unittest.main()
