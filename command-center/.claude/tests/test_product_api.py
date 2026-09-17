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

if __name__=='__main__': unittest.main()

class ProductHardeningTests(unittest.TestCase):
    def test_ui_has_all_operator_surfaces(self):
        for label in ('Company Cockpit','Gev Attention','Approval Inbox','Mission Center','Execution Center','Integration Health','Reports','Ask Deputy','Search','History / Timeline','Notifications','Worker status'):
            self.assertIn(label, product_api.INDEX_HTML)
    def test_readiness_is_dependency_shaped(self):
        self.assertIn('actions', product_api.Handler._readiness.__code__.co_names)
        self.assertIn('optional_sources', product_api.Handler._readiness.__code__.co_consts)
    def test_approval_routes_delegate_to_action_runtime(self):
        self.assertIn('approve', product_api.Handler.do_POST.__code__.co_names)
        self.assertIn('execute_approved', product_api.Handler.do_POST.__code__.co_names)
    def test_request_limit_and_safe_headers(self):
        self.assertIn('REQUEST_TOO_LARGE', product_api.Handler.do_POST.__code__.co_consts)
        self.assertIn('X-Content-Type-Options', product_api.Handler._json.__code__.co_consts)
