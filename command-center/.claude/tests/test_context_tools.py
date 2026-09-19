import tempfile
import unittest

from store import Store
from context_orchestrator import run_tool


class ContextToolTests(unittest.TestCase):
    def test_prepare_follow_up_is_durable_internal_only(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(td)
            result = run_tool({"tool": "prepare_follow_up", "query": "Ask Arman for the revised offer"}, store=store)
            self.assertEqual(result["authority"], "INTERNAL_PREPARE_ONLY")
            self.assertEqual(result["records"][0]["state"], "PREPARED")
            self.assertEqual(store.list("loops")[0]["kind"], "PREPARED_FOLLOW_UP")

    def test_prepare_follow_up_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(td)
            req = {"tool": "prepare_follow_up", "query": "Ask Arman for the revised offer"}
            run_tool(req, store=store)
            run_tool(req, store=store)
            self.assertEqual(len(store.list("loops")), 1)


if __name__ == "__main__":
    unittest.main()
