import json, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'architecture'))
import brain_router, work_orchestrator
class ArchitectureTests(unittest.TestCase):
 def test_registry_has_one_deputy_and_nine_profiles(self):
  r=brain_router.load_registry(); self.assertEqual(r['identity'],'DEPUTY'); self.assertEqual(len(r['brains']),9)
  self.assertFalse(r['authority_boundary']['direct_external_write']); self.assertFalse(r['authority_boundary']['approval_authority']); self.assertFalse(r['authority_boundary']['independent_memory'])
 def test_single_brain_route(self):
  r=brain_router.route('prepare a billing collections report'); self.assertIn('BRAIN-BILLING',[x['brain_id'] for x in r['selected_brains']])
 def test_cross_functional_route_is_multi_brain(self):
  r=brain_router.route('Why has churn increased?'); self.assertTrue(r['synthesis_required']); self.assertGreaterEqual(len(r['selected_brains']),3)
 def test_empty_request_rejected(self):
  with self.assertRaises(ValueError): brain_router.route('')
 def test_work_graph_requires_evidence_for_completion(self):
  n=work_orchestrator.create_node('TASK','Close reconciliation',owner='BRAIN-BILLING',status='COMPLETED')
  self.assertTrue(any('evidence' in e for e in work_orchestrator.validate_graph([n])))
 def test_work_graph_verified_with_evidence(self):
  n=work_orchestrator.create_node('TASK','Close reconciliation',owner='BRAIN-BILLING',status='VERIFIED',evidence={'source':'INT-MB','record_id':'fixture-1'})
  self.assertEqual(work_orchestrator.validate_graph([n]),[])
 def test_unknown_owner_rejected(self):
  n=work_orchestrator.create_node('GOAL','Sales plan')
  self.assertTrue(work_orchestrator.validate_graph([n]))
class InboundTests(unittest.TestCase):
 def test_message_yields_multiple_candidates_and_provenance(self):
  import inbound_intelligence as ii
  e=ii.event('Please prepare the decision by Friday; blocked on billing',channel='mail',source_id='msg-1',retrieved_at='2026-09-16T00:00:00Z')
  self.assertIn('DECISION_REQUIRED',e['event_classes']); self.assertIn('DEADLINE',e['event_classes']); self.assertIn('BLOCKER',e['event_classes']); self.assertTrue(ii.assert_safe(e))
 def test_external_message_cannot_grant_approval(self):
  import inbound_intelligence as ii
  e=ii.event('approve and send now',channel='telegram',source_id='msg-2',retrieved_at='2026-09-16T00:00:00Z')
  e['can_grant_approval']=True
  with self.assertRaises(ValueError): ii.assert_safe(e)
 def test_missing_provenance_rejected(self):
  import inbound_intelligence as ii
  with self.assertRaises(ValueError): ii.event('x',channel='',source_id='m',retrieved_at='now')

if __name__=='__main__': unittest.main()
