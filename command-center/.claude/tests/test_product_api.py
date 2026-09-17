import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[2]))
import product_api

class ProductApiTests(unittest.TestCase):
    def test_health_and_auth_contract(self):
        self.assertEqual(product_api.Handler.server_version, "HouseNetDeputy/1.0")
        self.assertFalse(product_api._auth(type('H',(),{'client_address':('10.0.0.1',0),'headers':{}})()))

    def test_operator_api_exposes_one_runtime_surface(self):
        self.assertTrue(hasattr(product_api, 'serve'))
        self.assertTrue(hasattr(product_api, 'Handler'))


class ProductHardeningTests(unittest.TestCase):
    def test_ui_has_all_operator_surfaces(self):
        for label in ('Company Cockpit','Gev Attention','Approval Inbox','Mission Center','Execution Center','Integration Health','Reports','Ask Deputy','Search','History / Timeline','Notifications','Worker status'):
            self.assertIn(label, product_api.INDEX_HTML)
    def test_readiness_is_dependency_shaped(self):
        self.assertIn('actions', product_api.Handler._readiness.__code__.co_names)
        self.assertIn('optional_sources', __import__('inspect').getsource(product_api.Handler._readiness))
    def test_approval_routes_delegate_to_action_runtime(self):
        self.assertIn('approve', product_api.Handler.do_POST.__code__.co_names)
        self.assertIn('execute_approved', product_api.Handler.do_POST.__code__.co_names)
    def test_request_limit_and_safe_headers(self):
        self.assertIn('REQUEST_TOO_LARGE', product_api.Handler.do_POST.__code__.co_consts)
        self.assertIn('X-Content-Type-Options', product_api.Handler._json.__code__.co_consts)

class OperatorPresentationTests(unittest.TestCase):
    def test_house_net_tokens_are_the_single_visual_contract(self):
        css = product_api.INDEX_HTML
        for token in ('#E4003A', '#1C2125', '#F6F9FB', '#EDF3F6', '#D1DCE2', '#78AD57', 'Inter', 'Noto Sans Armenian', '1180px'):
            self.assertIn(token, css)
        self.assertNotIn('--blue', css)

    def test_screen_specific_adapters_and_safe_diagnostic_boundary(self):
        js = product_api.APP_JS
        for fn in ('renderCockpit','renderAttention','renderApprovals','renderMissions','renderExecution','renderSources','renderReports','renderHistory','renderNotifications','renderWorker'):
            self.assertIn('function '+fn, js)
        self.assertIn('Evidence and diagnostic details', js)
        self.assertNotIn('[object Object]', js)
        self.assertNotIn("'Record '+(i+1)", js)
        self.assertNotIn('Record '+"' +", js)

    def test_humanized_timestamps_and_semantic_empty_states(self):
        js = product_api.APP_JS
        self.assertIn('toLocaleString', js)
        self.assertIn('Deputy has no matching canonical data', js)
        self.assertIn('Chronological activity', js)
        self.assertIn('Exact approval inbox', js)

if __name__=='__main__': unittest.main()
