import tempfile, unittest
from unittest.mock import patch

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
                commitments = store.list('commitments')
                self.assertEqual(len(commitments), 1)
                self.assertEqual(commitments[0].get('direction'), 'REQUEST_TO_GEV')
            finally:
                proactive._st = original

    def test_overdue_commitment_creates_deduplicated_follow_up_loop(self):
        with tempfile.TemporaryDirectory() as td:
            original = proactive._st
            store = Store(td)
            proactive._st = lambda: store
            try:
                store.record('commitments', 'CMT-overdue', {
                    'op_id': 'CMT-overdue', 'who': 'Arman', 'what': 'Send the proposal',
                    'due': '2020-01-01', 'state': 'OPEN', 'evidence': [{'record_id': 'mail-1'}],
                    'source': {'channel': 'fixture'}
                })
                first = proactive.run_cycle()
                second = proactive.run_cycle()
                self.assertTrue(any(e.get('event_type') == 'COMMITMENT_OVERDUE' for e in first['events']))
                self.assertEqual(len([e for e in second['events'] if e.get('event_type') == 'COMMITMENT_OVERDUE']), 1)
                self.assertEqual(len([r for r in store.list('loops') if r.get('loop_id') == 'followup:CMT-overdue']), 1)
            finally:
                proactive._st = original

    def test_meaningful_inbound_event_gets_bounded_claude_preparation(self):
        with tempfile.TemporaryDirectory() as td:
            original = proactive._st
            store = Store(td)
            proactive._st = lambda: store
            try:
                store.record('channel_events', 'signal-claude', {
                    'kind': 'INBOUND_SIGNAL', 'channel': 'fixture', 'source_id': 'fixture-claude',
                    'retrieved_at': '2026-09-18T00:00:00',
                    'text': "Please send me the proposal by Friday.", 'sender': 'customer@example.test'
                })
                fake = {'status': 'OK', 'provider': 'claude-code-max', 'provider_state': 'READY',
                        'answer': 'Prepare a proposal follow-up for review.', 'agent_trace': [], 'agent_iterations': 1}
                with patch.dict('os.environ', {'DEPUTY_USE_CLAUDE': '1'}), patch('ai_provider.ask_agent', return_value=fake):
                    result = proactive.run_cycle()
                checkpoint = store.get('checkpoints', 'proactive:analysis:' + event('Please send me the proposal by Friday.', channel='fixture', source_id='fixture-claude', retrieved_at='2026-09-18T00:00:00', sender='customer@example.test')['id'])
                self.assertIsNotNone(checkpoint)
                self.assertEqual(checkpoint['status'], 'OK')
                self.assertTrue(any(e.get('claude_preparation', {}).get('status') == 'OK' for e in result['events']))
            finally:
                proactive._st = original


if __name__ == '__main__':
    unittest.main()
