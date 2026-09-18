import tempfile, unittest

from store import Store
import proactive
from inbound_intelligence import event


class ProactiveInboundTests(unittest.TestCase):
    def test_commitment_direction_is_confidence_aware(self):
        a=event('I will send you the proposal Friday.',channel='fixture',source_id='a',retrieved_at='now')
        b=event('Please send me the proposal Friday.',channel='fixture',source_id='b',retrieved_at='now')
        c=event('FYI the office is closed.',channel='fixture',source_id='c',retrieved_at='now')
        self.assertEqual(a['commitment']['kind'],'GEV_OWES')
        self.assertEqual(b['commitment']['kind'],'REQUEST_TO_GEV')
        self.assertIsNone(c['commitment'])

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
