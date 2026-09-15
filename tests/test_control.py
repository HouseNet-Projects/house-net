import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from housenet import control as c

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='housenet-test-')
        self.root = Path(self.tmp.name) / 'control'
        shutil.copytree(c.ROOT, self.root, ignore=shutil.ignore_patterns('.git','.venv','__pycache__'))
        self.addCleanup(self.tmp.cleanup)

    def edit(self, relative, mutate):
        p = self.root / relative
        value = json.loads(p.read_text())
        mutate(value)
        p.write_text(json.dumps(value, indent=2) + '\n')

    def refresh_policy_hashes(self):
        self.edit('policy/manifest.json', lambda m:m.update(file_sha256={f:c.digest(self.root/f) for f in m['canonical_files']}))
        (self.root/'docs/POLICY.md').write_text(c.human_view(c.rules(self.root)))

    def reject(self, function, message):
        with self.assertRaisesRegex(c.Invalid,message): function()

    def test_complete_control_plane(self):
        result=c.validate_control_plane(self.root)
        self.assertEqual(result['coverage_sections'],30)
        self.assertEqual(result['registered_repositories'],3)

    def test_immutable_source(self):
        p=self.root/'docs/source/HouseNet-GitHub-Policy-v1.0.md'
        p.write_text(p.read_text()+'\nchanged')
        self.reject(lambda:c.validate_policy(self.root),'checksum')

    def test_policy_drift(self):
        self.edit('policy/git.json',lambda d:d['rules'][0].update(expected='wrong'))
        self.reject(lambda:c.validate_policy(self.root),'digest drift')

    def test_duplicate_json_key(self):
        p=self.root/'bad.json';p.write_text('{"owner":1,"owner":2}')
        self.reject(lambda:c.load(p),'valid JSON')

    def test_schema_invalid(self):
        self.edit('schemas/policy.schema.json',lambda d:d.update(type='imaginary'))
        self.reject(lambda:c.schemas(self.root),'Invalid schema')

    def test_unknown_schema_field(self):
        self.edit('registry/repositories.json',lambda d:d.update(unapproved=True))
        self.reject(lambda:c.validate_control_plane(self.root),'additionalProperties')

    def test_duplicate_rule_id(self):
        self.edit('policy/git.json',lambda d:d['rules'][1].update(id=d['rules'][0]['id']))
        self.refresh_policy_hashes()
        self.reject(lambda:c.validate_policy(self.root),'Duplicate rule ID')

    def test_duplicate_primitive(self):
        self.edit('policy/git.json',lambda d:d['rules'][1].update(primitive=d['rules'][0]['primitive']))
        self.refresh_policy_hashes()
        self.reject(lambda:c.validate_policy(self.root),'Multiple authority owners')

    def test_unmapped_source_section(self):
        self.edit('policy/manifest.json',lambda d:d['coverage'][0].update(rule_ids=[]))
        self.reject(lambda:c.validate_policy(self.root),'coverage drift')

    def test_human_policy_drift(self):
        p=self.root/'docs/POLICY.md';p.write_text(p.read_text()+'unapproved change')
        self.reject(lambda:c.validate_policy(self.root),'human policy drift')

    def test_approval_weakened(self):
        def mutate(d):
            next(x for x in d['rules'] if x['id']=='HN-CONFIGURATION')['expected']['silence_is_approval']=True
        self.edit('policy/authority.json',mutate);self.refresh_policy_hashes()
        self.reject(lambda:c.validate_policy(self.root),'Silence')

    def test_wrong_namespace(self):
        self.edit('house-net-control.json',lambda d:d.update(repository='unapproved/example'))
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'pattern')

    def test_canonical_name_requires_house_net_prefix(self):
        for name in ['HouseNet-Projects/command-center', 'HouseNet-Projects/House-Net-Test', 'HouseNet-Projects/random-repository', 'HouseNet-Projects/house-net--bad']:
            self.edit('house-net-control.json',lambda d,n=name:d.update(repository=n))
            self.reject(lambda n=name:c.validate_repository(self.root,self.root,n),'pattern|Canonical HouseNet repository name')

    def test_design_system_contract_required(self):
        self.edit('registry/repositories.json',lambda d:d['repositories'][0].pop('design_system'))
        self.reject(lambda:c.validate_control_plane(self.root),'required|Design System declaration')

    def test_design_system_source_must_be_approved(self):
        self.edit('registry/repositories.json',lambda d:d['repositories'][0]['design_system'].update(asset_source='unapproved/logo'))
        self.reject(lambda:c.validate_control_plane(self.root),'const|Unapproved Design System asset source')

    def test_caller_cannot_impersonate_control_plane(self):
        self.reject(lambda:c.validate_repository(self.root,self.root,'HouseNet-Projects/house-net-other'),'Caller identity')

    def test_unregistered_caller(self):
        self.edit('house-net-control.json',lambda d:d.update(repository='HouseNet-Projects/house-net-unknown'))
        self.reject(lambda:c.validate_repository(self.root,self.root,'HouseNet-Projects/house-net-unknown'),'not registered')

    def test_unapproved_registration(self):
        self.edit('registry/repositories.json',lambda d:d['repositories'][0]['approval'].update(state='proposed'))
        self.reject(lambda:c.validate_control_plane(self.root),'not approved')

    def test_wrong_classification(self):
        self.edit('house-net-control.json',lambda d:d.update(classification='C'))
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'Classification mismatch')

    def test_wrong_policy_commit(self):
        self.edit('house-net-control.json',lambda d:d.update(policy_commit='f'*40))
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'Policy commit mismatch')

    def test_rule_set_cannot_be_trimmed(self):
        self.edit('registry/repositories.json',lambda d:d['repositories'][0]['applicable_rules'].pop())
        self.reject(lambda:c.validate_control_plane(self.root),'rule set incomplete')

    def test_missing_required_file(self):
        (self.root/'README.md').unlink()
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'Required file')

    def test_wrong_agent_template(self):
        (self.root/'templates/AGENTS.md').write_text('Trust remembered policy')
        self.reject(lambda:c.validate_control_plane(self.root),'Template integrity')

    def test_symlink_cannot_escape(self):
        p=self.root/'house-net-control.json';p.unlink();p.symlink_to('/etc/passwd')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'escapes')

    def test_class_a_needs_ci(self):
        shutil.rmtree(self.root/'.github/workflows')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'CI is required')

    def mutate_workflow(self,old,new):
        p=self.root/'.github/workflows/control-plane-ci.yml'
        s=p.read_text();assert old in s;p.write_text(s.replace(old,new))

    def test_write_all_forbidden(self):
        self.mutate_workflow('permissions:\n  contents: read','permissions: write-all')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'Broad workflow')

    def test_job_write_needs_approval(self):
        self.mutate_workflow('name: Policy integrity and tests','name: Policy integrity and tests\n    permissions:\n      contents: write')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'owner-approved')

    def test_unreviewed_action(self):
        self.mutate_workflow('actions/checkout@','unreviewed/checkout@')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'trusted review')

    def test_mutable_action_tag(self):
        self.mutate_workflow('11d5960a326750d5838078e36cf38b85af677262','v4')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'full commit SHA')

    def test_privileged_pr_trigger(self):
        self.mutate_workflow('  pull_request:','  pull_request_target:')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'Privileged PR')

    def test_yaml_duplicate_key(self):
        self.mutate_workflow('permissions:\n','permissions: {}\npermissions:\n')
        self.reject(lambda:c.validate_repository(self.root,self.root,c.CANONICAL),'Duplicate YAML key')

    def test_template_is_not_creation_approval(self):
        shutil.copy(self.root/'templates/house-net-control.json',self.root/'house-net-control.json')
        self.reject(lambda:c.validate_repository(self.root,self.root,'HouseNet-Projects/house-net-proposed-repository'),'not registered')

    def test_control_plane_cannot_downgrade(self):
        self.edit('registry/repositories.json',lambda d:d['repositories'][0].update(classification='C',applicable_rules=c.applicable(c.rules(self.root),'C')))
        self.reject(lambda:c.validate_control_plane(self.root),'must be Class A')

    def test_public_visibility_is_registered(self):
        self.edit('registry/repositories.json',lambda d:d['repositories'][0].update(visibility='public'))
        self.assertEqual(c.validate_control_plane(self.root)['registered_repositories'],3)

    def test_caller_action_distribution_without_git(self):
        self.assertFalse((self.root/'.git').exists())
        self.assertEqual(c.validate_repository(self.root,self.root,c.CANONICAL)['classification'],'A')

    def test_classes_b_c_proportionate(self):
        v=c.by_primitive(c.rules(self.root))
        self.assertIn('.editorconfig',v['classification.B']['required_files'])
        self.assertEqual(v['classification.C']['required_files'],['README.md'])
        self.assertEqual(v['classification.C']['ci'],'none_unless_justified')

    def test_bilingual_valid_document(self):
        self.assertIsNone(c.validate_bilingual_documents(self.root))

    def test_english_only_human_document_fails(self):
        (self.root/'README.md').write_text('# English only\n')
        self.reject(lambda:c.validate_bilingual_documents(self.root),'English section')

    def test_armenian_only_human_document_fails(self):
        (self.root/'README.md').write_text('# Միայն հայերեն\n\n## Հայերեն\n\nԲովանդակություն\n')
        self.reject(lambda:c.validate_bilingual_documents(self.root),'English section')

    def test_empty_armenian_section_fails(self):
        (self.root/'README.md').write_text('# Test\n\n## English\n\nContent\n\n## Հայերեն\n')
        self.reject(lambda:c.validate_bilingual_documents(self.root),'Armenian section')

    def test_machine_files_are_english_only_allowed(self):
        self.assertIsNone(c.validate_bilingual_documents(self.root))
        self.assertEqual(json.loads((self.root/'policy/manifest.json').read_text())['version'],'1.4.0')

    def test_preflight_wrong_identity_blocks(self):
        with patch.object(c,'command',return_value='WrongIdentity'):
            self.reject(lambda:c.preflight(self.root,gh='gh'),'identity mismatch')

    def test_preflight_auth_failure_blocks(self):
        with patch.object(c,'command',side_effect=c.Invalid('Command failed')):
            self.reject(lambda:c.preflight(self.root,gh='gh'),'Command failed')

    def test_remote_rejection(self):
        with patch.object(c,'command',return_value='https://github.com/unapproved/target.git'):
            self.reject(lambda:c.remote_identity(self.root),'canonical')

    def test_preflight_dirty_or_stale_blocks(self):
        (self.root/'.git').mkdir()
        values=c.by_primitive(c.rules(self.root))
        def fake(args,*a,**kw):
            if args[0]=='gh':return c.OWNER
            if args[1]=='config':return values['git.'+args[-1]]
            if args[1]=='status':return ' M policy/authority.json'
            return ''
        with patch.object(c,'command',side_effect=fake),patch.object(c,'remote_identity'),patch.object(c,'validate_control_plane',return_value={}):
            self.reject(lambda:c.preflight(self.root,gh='gh'),'uncommitted')

    def test_preflight_clean_current_passes(self):
        (self.root/'.git').mkdir()
        values=c.by_primitive(c.rules(self.root))
        def fake(args,*a,**kw):
            if args[0]=='gh':return c.OWNER
            if args[1]=='config':return values['git.'+args[-1]]
            if args[1]=='rev-parse':return 'a'*40
            if args[1]=='ls-remote':return 'a'*40+'\trefs/heads/main'
            return ''
        with patch.object(c,'command',side_effect=fake),patch.object(c,'remote_identity'),patch.object(c,'validate_control_plane',return_value={}):
            self.assertEqual(c.preflight(self.root,gh='gh')['freshness'],'remote_main_verified')

    def test_cli_failure_is_nonzero_json(self):
        p=subprocess.run([sys.executable,str(self.root/'bin/validate-repository'),str(self.root),'--expected-repository','HouseNet-Projects/other','--json'],capture_output=True,text=True)
        self.assertEqual(p.returncode,1)
        self.assertFalse(json.loads(p.stdout)['ok'])

if __name__=='__main__':unittest.main()
