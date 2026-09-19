import unittest
from unittest.mock import patch

from ai_provider import ask_agent, parse_tool_request


class AgentLoopTests(unittest.TestCase):
    def test_parse_accepts_only_registered_read_requests(self):
        self.assertEqual(parse_tool_request('DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"search_work","query":"sales blockers"}')["tool"], "search_work")
        self.assertIsNone(parse_tool_request('DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"send_email","query":"send it"}'))

    def test_multi_step_read_loop(self):
        responses = [
            {"status": "OK", "provider": "claude-code-max", "answer": 'DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"search_work","query":"sales blockers"}'},
            {"status": "OK", "provider": "claude-code-max", "answer": 'DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"search_open_loops","query":"sales blockers"}'},
            {"status": "OK", "provider": "claude-code-max", "answer": "Sales has one blocked item."},
        ]
        calls = []
        def tool(req):
            calls.append(req["tool"])
            return {"records": [{"summary": req["query"]}]}
        with patch("ai_provider.ask", side_effect=responses):
            out = ask_agent("question", tool_executor=tool, max_iterations=4)
        self.assertEqual(out["status"], "OK")
        self.assertEqual(calls, ["search_work", "search_open_loops"])
        self.assertEqual(len(out["agent_trace"]), 2)

    def test_tool_loop_stops_at_bound_without_mutation(self):
        responses = [
            {"status": "OK", "provider": "claude-code-max", "answer": 'DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"search_work","query":"more one"}'},
            {"status": "OK", "provider": "claude-code-max", "answer": 'DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"search_work","query":"more two"}'},
        ]
        writes = []
        with patch("ai_provider.ask", side_effect=responses):
            out = ask_agent("question", tool_executor=lambda req: {"records": []}, max_iterations=2)
        self.assertEqual(out["status"], "DEGRADED")
        self.assertIn("bounded read-tool limit", out["reason"])
        self.assertEqual(writes, [])

    def test_tool_failure_is_partial_and_provider_can_finish(self):
        responses = [
            {"status": "OK", "provider": "claude-code-max", "answer": 'DEPUTY_TOOL_REQUEST {"type":"tool_request","tool":"search_work","query":"missing"}'},
            {"status": "OK", "provider": "claude-code-max", "answer": "I can answer with partial evidence."},
        ]
        with patch("ai_provider.ask", side_effect=responses):
            out = ask_agent("question", tool_executor=lambda req: (_ for _ in ()).throw(RuntimeError("source down")), max_iterations=3)
        self.assertEqual(out["status"], "OK")
        self.assertEqual(out["agent_trace"][0]["status"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
