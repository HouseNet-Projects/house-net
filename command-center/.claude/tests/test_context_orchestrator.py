import tempfile, unittest
from store import Store
from context_orchestrator import retrieve, _compact_value


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
        row = {'id': 'x', 'parameters': {'secret': 'hidden'}, 'history': list(range(100)), 'summary': 'ok'}
        compact = _compact_value(row)
        self.assertEqual(compact['id'], 'x')
        self.assertEqual(compact['summary'], 'ok')
        self.assertNotIn('parameters', compact)
        self.assertNotIn('history', compact)


if __name__=='__main__': unittest.main()
