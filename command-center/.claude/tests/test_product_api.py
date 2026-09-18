import unittest
from unittest.mock import patch
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
        for label in ('Home','Deputy','Inbox','Work','Reports','Documents','Settings'):
            self.assertIn(label, product_api.INDEX_HTML)
        self.assertNotIn('data-view="attention"', product_api.INDEX_HTML)
        self.assertNotIn('data-view="approvals"', product_api.INDEX_HTML)
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


class BilingualThemeProviderTests(unittest.TestCase):
    def test_i18n_theme_and_logo_contract(self):
        self.assertIn('I18N=', product_api.APP_JS)
        self.assertIn('deputy-locale', product_api.APP_JS)
        self.assertIn('deputy-theme', product_api.APP_JS)
        self.assertIn('data-theme="dark"', product_api.INDEX_HTML)
        self.assertIn('class="logo"', product_api.INDEX_HTML)
        self.assertIn('Հաստատումների մուտքային', product_api.APP_JS)
        self.assertNotIn('__LOGO__', product_api.INDEX_HTML)
        self.assertIn('data:image/svg+xml;base64,', product_api.INDEX_HTML)

    def test_claude_provider_is_cli_only_and_truthful_when_unavailable(self):
        from ai_provider import status
        result = status()
        self.assertEqual(result.get('provider'), 'claude-code-max')
        self.assertFalse(result.get('api_key_required'))
        self.assertNotIn('ANTHROPIC_API_KEY', product_api.APP_JS)
        self.assertIn('/provider', __import__('inspect').getsource(product_api.Handler.do_GET))

class BehavioralProductTests(unittest.TestCase):
    def test_i18n_uses_stable_ids_and_no_visible_text_lookup(self):
        js = product_api.APP_JS
        self.assertIn("function t(id)", js)
        self.assertIn("data-i18n=\"nav.home\"", product_api.INDEX_HTML)
        self.assertNotIn("key=el.dataset.i18n||el.textContent", js)
        self.assertIn("localStorage.setItem('deputy-locale'", js)

    def test_normalized_ask_contract_is_operator_shaped(self):
        out = product_api._normalize_ask({
            'mission_id':'MIS-test', 'completion_state':'PREPARED',
            'understanding': {'outcome':'Review current work'},
            'provider': {'status':'OK','provider':'claude-code-max','provider_state':'READY','answer':'All good.'},
            'runtime': {'status':'OK','steps':[]}, 'context': {'sources':[{'source':'INT-TASKS','state':'VERIFIED_READ'}]},
            'work_graph': {'validation':'GREEN','nodes':[{}]}
        }, 'en')
        self.assertEqual(out['answer'], 'All good.')
        self.assertEqual(out['provider'], 'claude-code-max')
        self.assertEqual(out['language'], 'en')
        self.assertIn('evidence', out)
        self.assertNotIn('raw', out)

    def test_provider_auth_truth_is_strict(self):
        from ai_provider import _auth_state
        self.assertEqual(_auth_state({'loggedIn':False}), 'AUTH_REQUIRED')
        self.assertEqual(_auth_state({'loggedIn':True,'authMethod':'api_key','apiProvider':'firstParty','subscriptionType':'max'}), 'WRONG_PROVIDER')
        self.assertEqual(_auth_state({'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty','subscriptionType':'max'}), 'READY')

    def test_provider_output_is_normalized(self):
        from ai_provider import _answer
        self.assertEqual(_answer({'result':'human answer'}), 'human answer')
        self.assertEqual(_answer({'result':{'content':[{'text':'nested answer'}]}}), 'nested answer')

    def test_ask_renderer_is_dedicated_and_approval_execute_is_bound(self):
        self.assertIn('function renderAskResponse', product_api.APP_JS)
        self.assertIn("data-execute", product_api.APP_JS)
        self.assertIn("/actions/'+encodeURIComponent(b.dataset.execute)+'/execute", product_api.APP_JS)

    def test_human_work_product_navigation_and_documents(self):
        for view in ('home','deputy','inbox','work','reports','documents','settings'):
            self.assertIn('data-view="'+view+'"', product_api.INDEX_HTML)
        self.assertIn("/documents/generate", __import__('inspect').getsource(product_api.Handler.do_POST))
        self.assertIn('function renderDocuments', product_api.APP_JS)

if __name__=='__main__': unittest.main()
