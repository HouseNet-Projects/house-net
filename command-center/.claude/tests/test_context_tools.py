import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "runtime"))
sys.path.insert(0, str(Path(__file__).parents[1] / "skills"))

from store import Store
from context_orchestrator import run_tool


class ContextToolTests(unittest.TestCase):
    def test_tool_names_map_to_their_canonical_tables(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(td)
            store.upsert("loops", "work-1", {"summary": "sales blocker", "state": "OPEN"})
            store.record("commitments", "commit-1", {"summary": "send numbers", "state": "OPEN"})
            work = run_tool({"tool": "search_work", "query": "sales"}, store=store)
            commitments = run_tool({"tool": "search_commitments", "query": "numbers"}, store=store)
            self.assertEqual(work["records"][0]["summary"], "sales blocker")
            self.assertEqual(commitments["records"][0]["summary"], "send numbers")

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
