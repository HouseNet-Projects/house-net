import json, os, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'architecture'))
sys.path.insert(0, str(Path(__file__).parents[1] / 'skills'))
sys.path.insert(0, str(Path(__file__).parents[1] / 'integrations'))
import execution_surface


class ExecutionSurfaceTests(unittest.TestCase):
    def test_preview_never_calls_provider(self):
        plan = execution_surface.preview([{"action_id": "ACT-1", "target_system": "INT-TG", "target_operation": "chat.send", "expected_effect": "test"}])
        self.assertEqual(plan["mode"], "PREVIEW")
        self.assertEqual(plan["provider_calls"], 0)
        self.assertTrue(plan["actions"][0]["approval_required"])

    def test_capability_matrix_is_explicitly_approval_bound(self):
        rows = execution_surface.capability_matrix()
        self.assertTrue(rows)
        self.assertTrue(all(r["approval_required"] for r in rows))
        self.assertIn("INT-TG", {r["source"] for r in rows})

    def test_inbox_is_derived_from_action_runtime(self):
        self.assertEqual(execution_surface.approval_inbox(), [])


if __name__ == '__main__': unittest.main()
