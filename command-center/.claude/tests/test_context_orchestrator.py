import tempfile, unittest
from store import Store
from context_orchestrator import retrieve, _compact_value, _compact_rows, correlate


class ContextOrchestratorTests(unittest.TestCase):
    def test_retrieval_is_bounded_read_only_and_provenance_preserving(self):
        with tempfile.TemporaryDirectory() as td:
            s=Store(td)
            s.record('loops','loop-1',{'summary':'Sales proposal waiting','source':{'source_id':'fixture'}})
            out=retrieve('What is waiting in Sales?',store=s,limit=1)
            self.assertEqual(out['authority'],'READ_ONLY_EVIDENCE')
            self.assertIn('search_open_loops', [x['tool'] for x in out['tools']])
            self.assertEqual(out['records']['search_open_loops'][0]['source']['source_id'],'fixture')
            self.assertLessEqual(len(out['records']['search_open_loops']),1)

    def test_context_rows_are_projected_and_bounded(self):
        row = {'id': 'x', 'parameters': {'secret': 'hidden'}, 'history': list(range(100)), 'provider': {'answer': 'stale generated answer'}, 'runtime': {'status': 'PARTIAL'}, 'summary': 'ok'}
        compact = _compact_value(row)
        self.assertEqual(compact['id'], 'x')
        self.assertEqual(compact['summary'], 'ok')
        self.assertNotIn('parameters', compact)
        self.assertNotIn('history', compact)
        self.assertNotIn('provider', compact)
        self.assertNotIn('runtime', compact)

    def test_generated_answers_cannot_become_current_source_evidence(self):
        compact = _compact_value({'mission_id': 'm-1', 'provider': {'answer': 'worker is degraded'}, 'answer': 'old answer', 'summary': 'historical work'})
        self.assertEqual(compact, {'mission_id': 'm-1', 'summary': 'historical work'})

    def test_generated_missions_and_assistant_messages_are_not_retrieved_as_evidence(self):
        rows = _compact_rows([
            {'mission_id': 'm-1', 'authority': 'ACTION_RUNTIME_ONLY_FOR_MATERIAL_MUTATION', 'request': 'old self-audit'},
            {'kind': 'CONVERSATION_MESSAGE', 'role': 'assistant', 'content': 'old technical diagnosis'},
            {'kind': 'CONVERSATION_MESSAGE', 'role': 'user', 'content': 'what is blocked?'}
        ])
        self.assertEqual(rows, [{'kind': 'CONVERSATION_MESSAGE', 'role': 'user', 'content': 'what is blocked?'}])

    def test_cross_source_context_links_only_exact_evidence(self):
        grouped = correlate({
            'search_work': [{'op_id': 'W-1', 'conversation_id': 'thread-7'}],
            'search_observations': [{'event_id': 'E-1', 'conversation_id': 'thread-7'}],
            'search_approvals': [{'action_id': 'A-1', 'conversation_id': 'different'}],
        })
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['basis'], 'conversation_id')
        self.assertEqual(grouped[0]['confidence'], 'OBSERVED_EXACT')


if __name__=='__main__': unittest.main()
