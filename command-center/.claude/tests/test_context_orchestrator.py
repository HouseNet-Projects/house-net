import tempfile, unittest
from store import Store
from context_orchestrator import retrieve


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


if __name__=='__main__': unittest.main()
