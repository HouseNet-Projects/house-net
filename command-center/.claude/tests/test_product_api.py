import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[2]))
import product_api
import deputy

class ProductApiTests(unittest.TestCase):
    def test_health_and_auth_contract(self):
        self.assertEqual(product_api.Handler.server_version, "HouseNetDeputy/1.0")
        self.assertFalse(product_api._auth(type('H',(),{'client_address':('10.0.0.1',0),'headers':{}})()))

    def test_operator_api_exposes_one_runtime_surface(self):
        self.assertTrue(hasattr(product_api, 'serve'))
        self.assertTrue(hasattr(product_api, 'Handler'))


class ProductHardeningTests(unittest.TestCase):
    def test_chat_workspace_contract(self):
        js = product_api.APP_JS
        for token in ('chat-thread', 'conversation-list', 'new-chat', 'requestSubmit'):
            self.assertIn(token, js)
        # The canonical conversation store is authoritative; browser storage may
        # hold locale/theme preferences but must not become chat state.
        self.assertNotIn("localStorage.setItem('deputy-conversation'", js)

    def test_chat_markdown_renderer_is_escaped_and_protocol_bounded(self):
        js = product_api.APP_JS
        self.assertIn('const renderMarkdown=raw=>', js)
        self.assertIn("esc(String(raw??''))", js)
        self.assertIn('safeMarkdownUrl', js)
        self.assertIn('/^(https?:|mailto:)/i', js)
        self.assertIn('rel="noopener noreferrer"', js)
        self.assertNotIn('innerHTML=m.content', js)

    def test_markdown_adversarial_inputs_are_bounded_by_renderer_contract(self):
        js = product_api.APP_JS
        for payload in ('<script>alert(1)</script>', '" onerror="alert(1)', 'javascript:alert(1)', '<img src=x onerror=alert(1)>'):
            self.assertNotIn(payload, js)
        self.assertIn(":'#'", js)

    def test_operator_controls_keep_readable_theme_foreground(self):
        html = product_api.INDEX_HTML
        self.assertIn('button,input,select,textarea{font:inherit;color:var(--text)}', html)
        self.assertIn('[data-theme="dark"] input,[data-theme="dark"] select,[data-theme="dark"] textarea', html)

    def test_runtime_labels_have_armenian_and_english_localization(self):
        js = product_api.APP_JS
        for token in ('label.tasks', 'label.outlookMail', 'status.APPROVAL_REQUIRED'):
            self.assertIn(token, js)

    def test_health_model_separates_product_and_business_data(self):
        import health_model
        h = health_model.build(store_state='READY', action_runtime_state='READY', worker={'running': True}, provider={'state': 'READY'})
        self.assertIn('product', h)
        self.assertIn('business_data', h)
        self.assertIn('developer_diagnostics', h)
        self.assertEqual(h['product']['state'], 'AVAILABLE')

    def test_provider_prompt_binds_requested_language(self):
        prompt = deputy._provider_prompt('status', {}, {}, {}, {}, {}, 'en')
        self.assertIn("English when language is 'en'", prompt)
        self.assertIn('requested response language is authoritative', prompt)
        self.assertIn('"language": "en"', prompt)

    def test_provider_prompt_states_epistemic_contract(self):
        prompt = deputy._provider_prompt('analysis', {}, {}, {}, {}, {}, 'en')
        self.assertIn('CONFIRMED FACT', prompt)
        self.assertIn('INFERENCE', prompt)
        self.assertIn('RECOMMENDATION', prompt)
        self.assertIn('UNKNOWN/MISSING', prompt)
        self.assertIn('full general knowledge', prompt)

    def test_operator_response_hides_developer_diagnostics(self):
        out = deputy.operator_response({'provider': {'answer': 'Useful answer.\nworkspace rules and GitHub sync details.'}}, language='en')
        self.assertEqual(out['answer'], 'Useful answer.')

    def test_provider_prompt_has_argv_safe_context_ceiling(self):
        context = {'sources': [], 'health': {}, 'operational_state': {},
                   'tool_trace': {'records': {'search_work': [{'blob': 'x' * 100000}]}}}
        prompt = deputy._provider_prompt('status', context, {}, {}, {}, {}, 'en')
        self.assertLessEqual(len(prompt), 60080)
        self.assertIn('Context truncated', prompt)

    def test_provider_prompt_distinguishes_partial_sources_from_worker_failure(self):
        prompt = deputy._provider_prompt('status', {'health': {'product': {'worker': 'AVAILABLE'}}}, {}, {'status': 'PARTIAL_SUCCESS'}, {}, {}, 'en')
        self.assertIn('partial business-source coverage', prompt)
        self.assertIn('Do not describe the worker as degraded', prompt)

    def test_provider_prompt_humanizes_health_codes_for_normal_answers(self):
        prompt = deputy._provider_prompt('self-audit', {'health': {}, 'sources': []}, {}, {}, {}, {}, 'hy')
        self.assertIn('never expose INT-* identifiers', prompt)
        self.assertIn('keep exact technical values only in evidence/details', prompt)

    def test_provider_prompt_receives_humanized_source_projection(self):
        context = {
            'sources': [{'source': 'INT-B24', 'state': 'NEEDS_SETUP', 'freshness': 'NOT VERIFIED'}],
            'health': {'business_data': {'state': 'PARTIAL', 'sources': [{'source_id': 'INT-B24', 'name': 'Bitrix24 CRM', 'state': 'NEEDS_SETUP'}]}},
        }
        prompt = deputy._provider_prompt('self-audit', context, {}, {}, {}, {}, 'hy')
        self.assertIn('Bitrix24 CRM', prompt)
        self.assertIn('needs connection', prompt)
        self.assertNotIn('"source_id": "INT-B24"', prompt)

    def test_assembled_context_uses_real_worker_health(self):
        with patch.object(deputy.proactive_worker, 'status', return_value={'running': True}):
            context = deputy.assemble_context()
        self.assertEqual(context['health']['product']['worker'], 'AVAILABLE')

    def test_operational_counts_exclude_internal_and_certification_noise(self):
        self.assertFalse(deputy._is_business_ticket({'source': 'DeputyCLI'}))
        self.assertFalse(deputy._is_business_ticket({'source': 'UserPromptSubmit'}))
        self.assertTrue(deputy._is_business_ticket({'source': 'INT-TASKS'}))
        self.assertTrue(deputy._is_certification_record({'source': {'channel': 'certification'}}))
        self.assertFalse(deputy._is_certification_record({'source': 'INT-TASKS'}))
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

    def test_shell_consumes_canonical_brand_token_source(self):
        css = product_api.INDEX_HTML
        self.assertEqual(product_api.BRAND_TOKENS["primary"], "#E4003A")
        self.assertEqual(product_api.BRAND_TOKENS["secondary"], "#1C2125")
        self.assertEqual(product_api.BRAND_TOKENS["font"], "Inter, Noto Sans Armenian, Arial, sans-serif")
        self.assertIn('data-i18n="home.title"', product_api.INDEX_HTML)
        self.assertIn('data-i18n="home.subtitle"', product_api.INDEX_HTML)
        self.assertNotIn('--blue', css)

    def test_screen_specific_adapters_and_safe_diagnostic_boundary(self):
        js = product_api.APP_JS
        for fn in ('renderCockpit','renderAttention','renderApprovals','renderMissions','renderExecution','renderSources','renderReports','renderHistory','renderNotifications','renderWorker'):
            self.assertIn('function '+fn, js)
        self.assertIn('Evidence and diagnostic details', js)
        self.assertNotIn('[object Object]', js)
        self.assertNotIn("'Record '+(i+1)", js)
        self.assertNotIn('Record '+"' +", js)

    def test_operator_summary_localizes_armenian_requests(self):
        import deputy
        result = deputy.operator_response({
            "completion_state": "PREPARED",
            "provider": {"status": "OK", "answer": "Բարև"},
            "understanding": {"outcome": "I will review"},
            "runtime": {}, "context": {}, "work_graph": {}
        }, language="hy")
        self.assertTrue(result["summary"].startswith("Կօգտագործեմ"))

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
    def test_conversation_store_uses_canonical_channel_events(self):
        import tempfile
        from store import Store
        import conversation_store
        with tempfile.TemporaryDirectory() as td:
            s=Store(td)
            cid=conversation_store.create(s, title='Sales')
            conversation_store.append(cid,'user','Show blockers',s,language='en')
            conversation_store.append(cid,'assistant','There are none.',s,language='en')
            self.assertEqual(len(conversation_store.get(cid,s)['messages']),2)
            self.assertEqual(conversation_store.list_conversations(s)[0]['conversation_id'],cid)

    def test_api_exposes_canonical_conversation_routes(self):
        import inspect
        source=inspect.getsource(product_api.Handler.do_GET)
        self.assertIn("path=='/conversations'",source)
        self.assertIn("conversation_store",inspect.getsource(product_api.Handler.do_POST))

    def test_approval_edit_delegates_to_runtime_invalidation(self):
        import inspect
        source=inspect.getsource(product_api.Handler.do_POST)
        self.assertIn("actions.invalidate_if_changed", source)
        self.assertIn("actions.prepare(changed['new_request']", source)

    def test_batch_approval_and_execution_delegate_to_canonical_runtime(self):
        import inspect
        post = inspect.getsource(product_api.Handler.do_POST)
        get = inspect.getsource(product_api.Handler.do_GET)
        self.assertIn("actions.approve(text,batch_id=batch_id)", post)
        self.assertIn("actions.execute_batch(batch_id)", post)
        self.assertIn("actions.list_actions(\"batch_id=?\"", get)

    def test_approval_inbox_preserves_batch_identity(self):
        import inspect
        self.assertIn("'batch_id':a.get('batch_id')", inspect.getsource(product_api.Handler.do_GET))

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

    def test_open_ended_fallback_hides_internal_skill_router_code(self):
        import deputy
        out = deputy.operator_response({
            'completion_state': 'PREPARED',
            'provider': {'status': 'OK', 'answer': 'General analysis'},
            'runtime': {'status': 'PARTIAL', 'blocked': [{'code': 'NO_APPLICABLE_SKILL'}]},
            'context': {}, 'understanding': {}, 'work_graph': {}
        }, 'en')
        self.assertNotIn('NO_APPLICABLE_SKILL', ' '.join(out['limitations']))
        self.assertIn('general governed analysis', ' '.join(out['limitations']))

    def test_partial_business_data_is_not_reported_as_full_product_block(self):
        import deputy
        out = deputy.operator_response({
            'completion_state': 'BLOCKED',
            'provider': {'status': 'OK', 'answer': 'Partial answer'},
            'runtime': {'status': 'BLOCKED', 'blocked': [{'code': 'SOURCE_UNAVAILABLE'}]},
            'context': {'health': {'business_data': {'state': 'PARTIAL'}}},
            'understanding': {}, 'work_graph': {}
        }, 'en')
        self.assertEqual(out['status'], 'PARTIAL_DATA')
        self.assertIn('unavailable', ' '.join(out['limitations']).lower())

    def test_self_audit_endpoint_is_separate_from_developer_diagnostics(self):
        import inspect
        self.assertIn("path=='/self-audit'", inspect.getsource(product_api.Handler.do_GET))

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

    def test_chat_markdown_renderer_is_escaped_and_protocol_bounded(self):
        self.assertIn('const renderMarkdown=', product_api.APP_JS)
        self.assertIn("safeMarkdownUrl=u=>/^(https?:|mailto:)/i", product_api.APP_JS)
        self.assertIn("esc(String(raw??''))", product_api.APP_JS)
        self.assertIn('rel="noopener noreferrer"', product_api.APP_JS)
        self.assertNotIn('innerHTML=m.content', product_api.APP_JS)

    def test_human_work_product_navigation_and_documents(self):
        for view in ('home','deputy','inbox','work','reports','documents','settings'):
            self.assertIn('data-view="'+view+'"', product_api.INDEX_HTML)
        self.assertIn("/documents/generate", __import__('inspect').getsource(product_api.Handler.do_POST))
        self.assertIn('function renderDocuments', product_api.APP_JS)

    def test_every_human_view_binds_heading_to_its_i18n_key(self):
        expected = {
            'home': 'home.title', 'deputy': 'deputy.title', 'inbox': 'inbox.title',
            'work': 'work.title', 'reports': 'reports.title', 'documents': 'documents.title',
            'settings': 'settings.title',
        }
        for view, key in expected.items():
            self.assertIn(key, product_api.APP_JS, view)
        self.assertIn("function setPageHeading(sub,label)", product_api.APP_JS)
        self.assertIn("setPageHeading(sub,label)", product_api.APP_JS)
        self.assertIn("setPageHeading('documents.subtitle','documents.title')", product_api.APP_JS)

if __name__=='__main__': unittest.main()
