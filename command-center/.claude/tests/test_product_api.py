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
