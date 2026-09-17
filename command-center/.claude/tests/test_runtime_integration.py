import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'architecture'))
from runtime_integration import DeputyRuntime, RuntimeBlocked, resolve_truth

class RuntimeIntegrationTests(unittest.TestCase):
    def runtime(self):
        return DeputyRuntime(state_dir=tempfile.mkdtemp())

    def test_multi_brain_plan_is_one_deputy_and_persists(self):
        r = self.runtime(); out = r.plan('Why has churn increased?')
        self.assertEqual(out['identity'], 'DEPUTY'); self.assertTrue(out['routing']['synthesis_required'])
        self.assertEqual(r.load_plan(out['op_id'])['identity'], 'DEPUTY')
        again = r.plan('Why has churn increased?'); self.assertTrue(again['duplicate'])

    def test_material_action_requires_approval(self):
        out = self.runtime().prepare_material_action({'type':'send_email'})
        self.assertEqual(out['status'], 'APPROVAL_REQUIRED'); self.assertFalse(out['approved'])

    def test_completion_requires_evidence(self):
        r=self.runtime(); node=r.plan('Create a sales action plan')['graph'][0]
        with self.assertRaises(RuntimeBlocked): r.complete(node, None)
        self.assertEqual(r.complete(node, {'source':'test'})['status'], 'VERIFIED')

    def test_full_work_graph_and_lifecycle(self):
        r=self.runtime(); g=r.persist_work_graph('Sales program', brains=['BRAIN-SALES'], source={'id':'src'})
        self.assertEqual(len(g['nodes']), 9); self.assertEqual(g['nodes'][0]['type'], 'GOAL'); self.assertEqual(g['nodes'][-1]['type'], 'VERIFIED_COMPLETION')
        with self.assertRaises(RuntimeBlocked): r.transition_work(g['nodes'][5], 'TASK_CREATED')
        n=r.transition_work(g['nodes'][5], 'TASK_CREATED', approval=True)
        self.assertEqual(n['lifecycle'], 'TASK_CREATED')
        with self.assertRaises(RuntimeBlocked): r.transition_work(n, 'TASK_COMPLETED')
        self.assertEqual(r.transition_work(n, 'RESULT_VERIFIED', evidence={'readback':'ok'})['lifecycle'], 'RESULT_VERIFIED')
        self.assertIsNotNone(r.store.get('commitments', g['nodes'][3]['id']))

    def test_control_plane_capability_is_registry_backed(self):
        import json, tempfile
        root=Path(tempfile.mkdtemp()); (root/'registry').mkdir()
        (root/'registry'/'repositories.json').write_text(json.dumps({'repositories':[{'repository':'HouseNet-Projects/x','owner':'HouseNet-Projects','capabilities':[{'capability_id':'knowledge.search','certification':'certified','health':'healthy'}]}]}))
        self.assertEqual(DeputyRuntime.discover_from_control_plane(root,'knowledge.search')['repository'],'HouseNet-Projects/x')
        with self.assertRaises(RuntimeBlocked): DeputyRuntime.discover_from_control_plane(root,'vault.read')

    def test_estate_backed_knowledge_and_vault_synthesis(self):
        import json, tempfile
        root=Path(tempfile.mkdtemp()); (root/'registry').mkdir()
        (root/'registry'/'repositories.json').write_text(json.dumps({'repositories':[
            {'repository':'HouseNet-Projects/house-net-knowledge','capabilities':[{'capability_id':'knowledge.search','path':'knowledge/index/catalog.json','certification':'certified','health':'healthy'}]},
            {'repository':'HouseNet-Projects/house-net-vault','capabilities':[{'capability_id':'vault.reference','path':'vault/index.json','certification':'certified','health':'healthy'}]}]}))
        knowledge=root/'knowledge'; (knowledge/'knowledge/index').mkdir(parents=True); (knowledge/'knowledge/canonical').mkdir(parents=True)
        (knowledge/'knowledge/index/catalog.json').write_text(json.dumps({'items':[{'id':'K1','status':'canonical','path':'knowledge/canonical/K1.json'}]}))
        (knowledge/'knowledge/canonical/K1.json').write_text(json.dumps({'id':'K1','title':'Sales process','domain':'sales','status':'canonical','owner':'HOUSE_NET_OWNER','source':{'hash':'a'*64},'freshness':{'state':'current'},'sensitivity':'INTERNAL'}))
        vault=root/'vault'; (vault/'vault').mkdir(parents=True); (vault/'vault/references').mkdir(parents=True); (vault/'vault/index.json').write_text(json.dumps({'references':[{'id':'V1'}]})); (vault/'vault/references/V1.json').write_text(json.dumps({'id':'V1','purpose':'synthetic','owner_principal':'HOUSE_NET_OWNER','target_system':'test','sensitivity':'RESTRICTED','required_for_bootstrap':False,'last_verified':'2026-09-16'}))
        out=self.runtime().synthesize_from_estate(root,knowledge,'sales',vault_root=vault,vault_reference_id='V1')
        self.assertEqual(out['evidence'][0]['id'],'K1'); self.assertEqual(out['vault_reference']['id'],'V1'); self.assertNotIn('storage',out['vault_reference'])
        (knowledge/'knowledge/canonical/K1.json').write_text(json.dumps({'id':'K1','status':'intake','source':{'hash':'a'*64},'freshness':{'state':'current'}}))
        with self.assertRaises(RuntimeBlocked): self.runtime().synthesize_from_estate(root,knowledge,'sales')

    def test_canonical_engine_entry_uses_resolver_and_audit(self):
        import tempfile as tf
        import engine, store
        old = engine.STATE_DIR
        engine.STATE_DIR = Path(tf.mkdtemp()); store.reset()
        try:
            reg = engine.load_registry()
            out = engine.run_deputy_request(reg, 'Why has churn increased?', session_id='test')
            self.assertIn('brains', out); self.assertIn('resolved_skills', out)
            self.assertTrue(out['ticket_id'])
            self.assertTrue(out['resolved_skills'])
            self.assertIn(out['status'], ('OK','PARTIAL','BLOCKED'))
            self.assertTrue(engine.get_ticket(out['ticket_id']))
        finally:
            engine.STATE_DIR = old; store.reset()

    def test_strategy_inbound_output_followthrough_fail_closed(self):
        r=self.runtime()
        self.assertIn("MISSING_KPI", r.strategy_assessment("sales plan")["gaps"])
        with self.assertRaises(RuntimeBlocked): r.reconcile_inbound({"text":"do it"})
        self.assertEqual(r.reconcile_inbound({"text":"do it","channel":"email","source_id":"m1","provenance":{"message":"m1"}})["status"], "PROPOSAL_ONLY")
        self.assertEqual(r.compose_output("report", provenance={"source":"test"})["status"], "TEMPLATE_GAP")
        self.assertEqual(r.follow_through([{"id":"t","status":"BLOCKED","owner":"GEV"}])["status"], "READY")

    def test_capability_fails_closed(self):
        with self.assertRaises(RuntimeBlocked): self.runtime().discover_capability('missing')
        r=DeputyRuntime(state_dir=tempfile.mkdtemp(), capabilities={'k':{'registered':True,'certification':'certified'}})
        self.assertEqual(r.discover_capability('k')['certification'],'certified')

    def test_truth_requires_current_provenance_and_conflict_fails(self):
        with self.assertRaises(RuntimeBlocked): resolve_truth([{'owner':'x','authority':'current','value':1}])
        with self.assertRaises(RuntimeBlocked): resolve_truth([{'owner':'x','authority':'current','value':1,'provenance':'a'}, {'owner':'y','authority':'current','value':2,'provenance':'b'}])
        self.assertEqual(resolve_truth([{'owner':'x','authority':'current','value':1,'provenance':'a'}, {'owner':'z','authority':'history','value':2,'provenance':'b'}])['value'],1)

if __name__ == '__main__': unittest.main()
