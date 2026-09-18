import tempfile, unittest

from store import Store
import proactive


class ProactiveInboundTests(unittest.TestCase):
    def test_safe_inbound_signal_creates_one_internal_loop(self):
        with tempfile.TemporaryDirectory() as td:
            original = proactive._st
            store = Store(td)
            proactive._st = lambda: store
            try:
                store.record('channel_events', 'signal-1', {
                    'kind': 'INBOUND_SIGNAL', 'channel': 'fixture', 'source_id': 'fixture-1',
                    'retrieved_at': '2026-09-18T00:00:00',
                    'text': "Please send me the proposal by Friday.", 'sender': 'customer@example.test'
                })
                first = proactive.run_cycle()
                second = proactive.run_cycle()
                loops = store.list('loops')
                self.assertTrue(any(e.get('event_type') == 'INBOUND_WORK_DETECTED' for e in first['events']))
                self.assertEqual(len(loops), 1)
                self.assertEqual(len([e for e in second['events'] if e.get('event_type') == 'INBOUND_WORK_DETECTED']), 0)
            finally:
                proactive._st = original


if __name__ == '__main__':
    unittest.main()
