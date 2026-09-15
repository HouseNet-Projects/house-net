"""Single implementation for offline policy validation, repository gates and preflight."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

OWNER = 'HouseNet-Projects'
CANONICAL = OWNER + '/house-net-control-plane'
SOURCE_SHA = 'a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491'
POLICY_VERSION = '1.1.0'
ROOT = Path(__file__).resolve().parents[1]

class Invalid(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise Invalid(message)

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result

def load(path):
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=unique_pairs)
    except (OSError, ValueError) as e:
        raise Invalid('Cannot read valid JSON: ' + str(path)) from e

def safe_path(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), 'Expected relative path')
    p = root / relative
    require(p.resolve().is_relative_to(root.resolve()), 'Path escapes repository: ' + relative)
    require(not p.is_symlink(), 'Symlink not permitted for policy-controlled file: ' + relative)
    return p

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(args, cwd=None, timeout=20):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Invalid('Required command unavailable or timed out: ' + str(args[0])) from e
    # Never propagate raw subprocess output: credential helpers may include secrets.
    require(p.returncode == 0, 'Command failed: ' + str(args[0]) + ' (exit ' + str(p.returncode) + ')')
    return p.stdout.strip()

def schemas(root):
    values = {}
    for path in sorted((root / 'schemas').glob('*.schema.json')):
        value = load(path)
        try:
            Draft202012Validator.check_schema(value)
        except Exception as e:
            raise Invalid('Invalid schema: ' + path.name) from e
        values[path.name] = value
    require(bool(values), 'No schemas found')
    def refs(value):
        if isinstance(value, dict):
            if '$ref' in value:
                name = value['$ref'].split('#')[0]
                require(not name or name in values, 'Unknown or remote schema reference')
            for x in value.values(): refs(x)
        elif isinstance(value, list):
            for x in value: refs(x)
    for value in values.values(): refs(value)
    registry = Registry().with_resources((name, Resource.from_contents(v)) for name, v in values.items())
    return {name: Draft202012Validator(v, registry=registry) for name, v in values.items()}

def validate_schema(validators, name, instance):
    try:
        errors = sorted(validators[name].iter_errors(instance), key=lambda e: str(e.path))
    except Exception as e:
        raise Invalid('Schema resolution failed: ' + name) from e
    if errors:
        e = errors[0]
        # Print path and validator only, never instance values.
        raise Invalid(name + ': rejected at ' + '/'.join(map(str, e.path)) + ' (' + str(e.validator) + ')')

def rules(root):
    return [r for p in sorted((root / 'policy').glob('*.json')) if p.name != 'manifest.json' for r in load(p)['rules']]

def by_primitive(items):
    return {r['primitive']: r['expected'] for r in items}

def applicable(items, classification):
    return sorted(r['id'] for r in items if classification in r['applicability']['classes'])

def human_view(items):
    english = '# HouseNet policy · ' + POLICY_VERSION + '\n\n## English\n\nGenerated from machine authority. Do not edit by hand. Original approved text is preserved in [source](source/HouseNet-GitHub-Policy-v1.0.md).\n\n' + ''.join(
        '### ' + r['id'] + ' · ' + r['primitive'] + '\n\n' + r['level'] + ' · ' + r['scope'] + ' · Classes ' + ', '.join(r['applicability']['classes']) + '\n\n```json\n' + json.dumps(r['expected'], indent=2, ensure_ascii=False) + '\n```\n\nApproval: ' + r['approval_requirement'] + '. Enforcement: ' + r['enforcement']['mechanism'] + '. Source sections: ' + ', '.join(map(str, r['source_sections'])) + '.\n\n' for r in sorted(items, key=lambda x: x['id']))
    armenian = '# HouseNet-ի քաղաքականություն · ' + POLICY_VERSION + '\n\nՄեքենայական հեղինակությունից ստեղծված ներկայացում է։ Խմբագրել միայն մեքենայական կանոնները։ Սկզբնական հաստատված քաղաքականությունը պահպանված է [աղբյուրում](source/HouseNet-GitHub-Policy-v1.0.md)։\n\n' + ''.join(
        '### ' + r['id'] + ' · ' + r['primitive'] + '\n\nՄակարդակ՝ ' + r['level'] + ' · Տիրույթ՝ ' + r['scope'] + ' · Դասեր՝ ' + ', '.join(r['applicability']['classes']) + '\n\n```json\n' + json.dumps(r['expected'], indent=2, ensure_ascii=False) + '\n```\n\nՀաստատում՝ ' + r['approval_requirement'] + '։ Կիրարկում՝ ' + r['enforcement']['mechanism'] + '։ Աղբյուրի բաժիններ՝ ' + ', '.join(map(str, r['source_sections'])) + '։\n\n' for r in sorted(items, key=lambda x: x['id']))
    return english + '---\n\n## Հայերեն\n\n' + armenian

HUMAN_FACING_EXCLUDES = {'docs/source/HouseNet-GitHub-Policy-v1.0.md', 'AGENTS.md', 'CLAUDE.md'}

def human_facing_paths(root):
    paths = []
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix.lower() != '.md' or '.git' in p.parts:
            continue
        rel = str(p.relative_to(root))
        if rel in HUMAN_FACING_EXCLUDES or p.name in {'AGENTS.md', 'CLAUDE.md'}:
            continue
        if rel.startswith(('README', 'CHANGELOG', 'docs/', 'audit/', 'assets/brand/')):
            paths.append(p)
    return sorted(paths)

def validate_bilingual_documents(root):
    for path in human_facing_paths(root):
        text = path.read_text()
        en = re.search(r'^## English\s*$([\s\S]*?)(?=^## |\Z)', text, re.M)
        hy = re.search(r'^## Հայերեն\s*$([\s\S]*?)(?=^## |\Z)', text, re.M)
        require(en and en.group(1).strip(), 'English section missing or empty: ' + str(path.relative_to(root)))
        require(hy and hy.group(1).strip(), 'Armenian section missing or empty: ' + str(path.relative_to(root)))

def validate_policy(root):
    validators = schemas(root)
    manifest = load(root / 'policy/manifest.json')
    validate_schema(validators, 'manifest.schema.json', manifest)
    source = safe_path(root, manifest['source']['path'])
    require(digest(source) == SOURCE_SHA == manifest['source']['sha256'], 'Immutable source checksum mismatch')
    actual_files = sorted(str(p.relative_to(root)) for folder in ['policy', 'schemas'] for p in (root / folder).glob('*.json') if p.name != 'manifest.json')
    require(manifest['canonical_files'] == actual_files, 'Canonical file inventory drift')
    require(set(manifest['file_sha256']) == set(actual_files), 'Canonical hash inventory drift')
    for f in actual_files:
        require(digest(safe_path(root, f)) == manifest['file_sha256'][f], 'Policy/schema digest drift: ' + f)
    items = []
    for path in sorted((root / 'policy').glob('*.json')):
        if path.name == 'manifest.json': continue
        value = load(path)
        validate_schema(validators, 'policy.schema.json', value)
        require(value['domain'] == path.stem, 'Domain/file ownership mismatch')
        if path.stem == 'authority': validate_schema(validators, 'authority.schema.json', value)
        if path.stem == 'repository-classes': validate_schema(validators, 'repository-class.schema.json', value)
        items += value['rules']
    require(len({r['id'] for r in items}) == len(items), 'Duplicate rule ID')
    require(len({r['primitive'] for r in items}) == len(items), 'Multiple authority owners for one primitive')
    index = {r['id']: r for r in items}
    values = by_primitive(items)
    require(values['github.identity'] == values['github.namespace'] == OWNER, 'Identity authority mismatch')
    require(values['github.configuration_change']['silence_is_approval'] is False, 'Silence cannot authorize changes')
    require(values['repository.creation']['requires'] == 'explicit_owner_instruction', 'Creation approval weakened')
    require(index['HN-DESTRUCTIVE']['approval_requirement'] == 'exact_owner', 'Destructive approval weakened')
    require(values['operation.destructive']['requires'] == 'exact_owner_approval', 'Destructive semantics weakened')
    require(values['merge.review']['single_identity_required_approvals'] == 0, 'Impossible review requirement')
    require({r['primitive'] for r in items if r['primitive'].startswith('classification.')} == {'classification.A', 'classification.B', 'classification.C'}, 'Incomplete classes')
    sections = {int(m.group(1)): m.group(0).rstrip() for m in re.finditer(r'^# (\d+)\. .*?(?=^# \d+\.|^# IMPLEMENTATION INSTRUCTION|\Z)', source.read_text(), re.M | re.S)}
    coverage = manifest['coverage']
    require(len(coverage) == len({x['section'] for x in coverage}) == 30, 'Duplicate/missing coverage section')
    require({x['section'] for x in coverage} == set(sections) == set(range(1, 31)), 'Source section coverage gap')
    covered = set()
    for entry in coverage:
        section = entry['section']
        require(hashlib.sha256(sections[section].encode()).hexdigest() == entry['source_sha256'], 'Source section drift')
        expected = sorted(r['id'] for r in items if section in r['source_sections'])
        require(bool(expected) and sorted(entry['rule_ids']) == expected, 'Rule/source coverage drift')
        covered.update(entry['rule_ids'])
    supplemental = {x['id'] for x in manifest.get('supplemental_rules', [])}
    require(supplemental <= set(index), 'Unknown supplemental rule')
    require(covered | supplemental == set(index), 'Unmapped rule')
    require((root / 'docs/POLICY.md').read_text().rstrip() == human_view(items).rstrip(), 'Generated human policy drift')
    return validators, manifest, items

def registry(root, validators, items):
    data = load(root / 'registry/repositories.json')
    validate_schema(validators, 'registry.schema.json', data)
    names = [r['repository'] for r in data['repositories']]
    require(len(names) == len(set(names)), 'Duplicate registration')
    require(CANONICAL in names, 'Control plane not registered')
    for r in data['repositories']:
        require(r['applicable_rules'] == applicable(items, r['classification']), 'Applicable rule set incomplete: ' + r['repository'])
        require(r['approval']['state'] == 'approved', 'Repository not approved: ' + r['repository'])
        for e in r['profile']['exceptions']:
            require(e['rule_id'] in r['applicable_rules'], 'Unknown exception rule')
        if r['repository'] == CANONICAL:
            require(r['classification'] == 'A', 'Control plane must be Class A')
    return data['repositories']

class StrictLoader(yaml.SafeLoader):
    pass

def yaml_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        require(key not in result, 'Duplicate YAML key')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result
StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, yaml_mapping)
# YAML 1.1 treats "on" as boolean; GitHub uses YAML 1.2 semantics.
StrictLoader.yaml_implicit_resolvers = {k: [(tag, regex) for tag, regex in v if tag != 'tag:yaml.org,2002:bool'] for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
StrictLoader.add_implicit_resolver('tag:yaml.org,2002:bool', re.compile(r'^(?:true|false)$', re.I), list('tTfF'))

def load_yaml(path):
    try:
        result = yaml.load(path.read_text(), Loader=StrictLoader)
        require(isinstance(result, dict), 'YAML document must be an object')
        return result
    except (OSError, yaml.YAMLError) as e:
        raise Invalid('Invalid YAML: ' + path.name) from e

def scan_workflows(root, record, values, action_reviews):
    warnings = []
    paths = sorted((root / '.github/workflows').glob('*.y*ml'))
    if record['classification'] == 'A' or record['profile']['meaningful_ci']:
        require(bool(paths), 'Meaningful CI is required')
    exceptions = {x['rule_id'] for x in record['profile']['exceptions']}
    def permission_check(p, where, job=False):
        require(p != 'write-all', 'Broad workflow write permissions forbidden')
        require(isinstance(p, dict), 'Explicit permission mapping required: ' + where)
        for key, value in p.items():
            require(value in ['read', 'write', 'none'], 'Invalid/dynamic workflow permission')
            if value == 'write':
                require(job and 'HN-PERMISSIONS' in exceptions, 'Job write permission needs registered owner-approved justification')
    def action_check(use):
        require(isinstance(use, str) and '${{' not in use, 'Dynamic action reference forbidden')
        if use.startswith('./'):
            safe_path(root, use)
            return
        require('@' in use, 'Unpinned action reference')
        repo, ref = use.rsplit('@', 1)
        require(re.fullmatch(r'[0-9a-f]{40}', ref) is not None, 'Remote action/workflow needs full commit SHA')
        parts = repo.split('/')
        require(len(parts) >= 2, 'Invalid action reference')
        owner = parts[0]
        if owner not in ['actions', OWNER]:
            require(use in action_reviews and action_reviews[use].get('reviewed') is True and action_reviews[use].get('justification'), 'Third-party action lacks trusted review')
        elif owner == 'actions':
            require(use in action_reviews, 'Official action SHA not in reviewed dependency inventory')
    for path in paths:
        require(not path.is_symlink(), 'Workflow symlink forbidden')
        workflow = load_yaml(path)
        require('on' in workflow and isinstance(workflow.get('jobs'), dict) and bool(workflow['jobs']), 'Workflow trigger/jobs missing')
        permission_check(workflow.get('permissions'), path.name)
        events = workflow['on']
        names = events.keys() if isinstance(events, dict) else events if isinstance(events, list) else [events]
        require('pull_request_target' not in names, 'Privileged PR trigger requires separate approved design')
        for name, job in workflow['jobs'].items():
            require(isinstance(job, dict), 'Invalid job')
            if 'permissions' in job: permission_check(job['permissions'], name, job=True)
            if 'uses' in job:
                action_check(job['uses'])
                require(job.get('secrets') != 'inherit', 'Unbounded reusable workflow secrets forbidden')
            else:
                require('runs-on' in job and isinstance(job.get('steps'), list), 'Job execution configuration missing')
                require(isinstance(job.get('timeout-minutes'), int) and 1 <= job['timeout-minutes'] <= 60, 'Job timeout must be 1–60 minutes')
                for step in job['steps']:
                    require(isinstance(step, dict), 'Invalid workflow step')
                    if 'uses' in step: action_check(step['uses'])
                    if 'run' in step:
                        require('${{ github.event.' not in step['run'], 'Untrusted event expression in shell; pass through environment')
    return warnings

def check_content(root):
    # Conservative tripwires, not a complete secret scanner.
    patterns = [re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'), re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'), re.compile(rb'github_pat_[A-Za-z0-9_]{40,}')]
    files = command(['git', 'ls-files', '-z'], root).split('\0') if (root / '.git').exists() else []
    for relative in files:
        if not relative: continue
        path = safe_path(root, relative)
        if not path.is_file(): continue
        require(path.name not in ['.env', 'id_rsa', 'id_ed25519'], 'Sensitive filename tracked: ' + relative)
        if path.stat().st_size > 2_000_000: continue
        data = path.read_bytes()
        require(not any(p.search(data) for p in patterns), 'Potential credential in tracked file: ' + relative + '; value withheld')

def validate_repository(root, target, expected_repository=None):
    validators, manifest, items = validate_policy(root)
    records = registry(root, validators, items)
    lock = load(safe_path(target, 'house-net-control.json'))
    validate_schema(validators, 'repository-lock.schema.json', lock)
    if expected_repository:
        require(lock['repository'] == expected_repository, 'Caller identity does not match repository lock')
    matches = [r for r in records if r['repository'] == lock['repository']]
    require(len(matches) == 1, 'Repository is not registered in trusted control plane')
    r = matches[0]
    require(lock['classification'] == r['classification'], 'Classification mismatch')
    require(lock['policy_version'] == r['control_plane_version'] == manifest['version'], 'Policy version mismatch')
    require(lock['policy_commit'] == r['control_plane_commit'], 'Policy commit mismatch')
    require(lock['approval_reference'] == r['approval']['reference'], 'Approval reference mismatch')
    # Require the pinned commit to carry the exact machine policy snapshot in use.
    snapshot = load(root / 'policy-snapshot.json')
    require(snapshot['commit'] == r['control_plane_commit'], 'Distribution policy snapshot mismatch')
    require(set(snapshot['files_sha256']) == set(['policy/manifest.json'] + manifest['canonical_files']), 'Snapshot inventory mismatch')
    for relative, sha in snapshot['files_sha256'].items():
        require(digest(safe_path(root, relative)) == sha, 'Pinned policy snapshot differs: ' + relative)
        if (root / '.git').exists():
            blob = command(['git', 'show', r['control_plane_commit'] + ':' + relative], root)
            require(blob == (root / relative).read_text().strip(), 'Git policy snapshot differs: ' + relative)
    values = by_primitive(items)
    class_rules = values['classification.' + r['classification']]
    required = set(class_rules['required_files']) | set(r['profile']['required_files']) | {'AGENTS.md','CLAUDE.md','house-net-control.json'}
    for name in sorted(required):
        p = safe_path(target, name)
        require(p.is_file() and p.stat().st_size > 0, 'Required file missing/empty: ' + name)
    for agent_file in ['AGENTS.md', 'CLAUDE.md']:
        text = (target / agent_file).read_text()
        require(all(x in text for x in ['house-net-control.json', 'housenet-preflight', 'house-net-control-plane']), 'Agent bootstrap map incomplete: ' + agent_file)
        require(len(text.encode()) < 4096, 'Agent map duplicates excessive policy')
    require(not any(p.is_file() for p in target.glob('LICENSE*')), 'License requires separately registered owner decision')
    reviews = load(root / 'policy-dependencies.json')['actions']
    scan_workflows(target, r, values, reviews)
    check_content(target)
    validate_bilingual_documents(target)
    return {'repository':r['repository'],'classification':r['classification'],'policy_version':manifest['version'],'policy_commit':r['control_plane_commit'],'rules':len(r['applicable_rules'])}

def internal_links(root):
    for path in root.rglob('*.md'):
        if any(x in path.parts for x in ['.git', '.venv', 'source']): continue
        text = path.read_text()
        for link in re.findall(r'\]\(([^)\s]+)\)', text):
            if '://' in link or link.startswith(('#','mailto:','/')): continue
            relative = link.split('#')[0]
            require((path.parent / relative).exists(), 'Broken internal link in ' + str(path.relative_to(root)) + ': ' + relative)

def validate_control_plane(root):
    validators, manifest, items = validate_policy(root)
    records = registry(root, validators, items)
    for path in (root / 'templates').glob('*.json'):
        validate_schema(validators, 'repository-lock.schema.json', load(path))
    for name in ['AGENTS.md', 'CLAUDE.md']:
        body = (root / 'templates' / name).read_text()
        require(len(body.encode()) < 4096 and all(x in body for x in ['house-net-control.json','housenet-preflight','house-net-control-plane']), 'Template integrity failure')
    internal_links(root)
    validate_bilingual_documents(root)
    validate_repository(root, root, CANONICAL)
    return {'policy_version':manifest['version'],'source_sha256':SOURCE_SHA,'coverage_sections':len(manifest['coverage']),'unique_rules':len(items),'registered_repositories':len(records),'schemas':len(validators)}

def remote_identity(root):
    urls = command(['git','remote','get-url','--all','origin'],root).splitlines()
    urls += command(['git','remote','get-url','--push','--all','origin'],root).splitlines()
    allowed = {'https://github.com/'+CANONICAL, 'https://github.com/'+CANONICAL+'.git', 'git@github.com:'+CANONICAL+'.git'}
    require(bool(urls) and all(x in allowed for x in urls), 'Control-plane origin is not exclusively canonical')

def preflight(root, gh=None):
    gh = gh or shutil.which('gh') or str(Path.home()/'.local/bin/gh')
    identity = command([gh,'api','user','--jq','.login'],timeout=15)
    require(identity == OWNER, 'GitHub identity mismatch; stop')
    require((root / '.git').exists(), 'Control-plane Git checkout missing')
    remote_identity(root)
    summary = validate_control_plane(root)
    values = by_primitive(rules(root))
    for key in ['user.name','user.email','init.defaultBranch','user.useConfigOnly','pull.ff']:
        actual = command(['git','config','--global','--get',key])
        require(actual == values['git.'+key], 'Global Git baseline mismatch: '+key)
    require(not command(['git','status','--porcelain','--untracked-files=normal'],root), 'Control-plane checkout has uncommitted changes; review/repair through approved workflow')
    require(not command(['git','ls-files','-u'],root), 'Unresolved Git conflict')
    # Read remote ref without modifying checkout or tracking refs.
    local = command(['git','rev-parse','HEAD'],root)
    remote = command(['git','ls-remote','--exit-code','origin','refs/heads/main'],root,timeout=15).split()[0]
    require(local == remote, 'Local control-plane HEAD is not current origin/main; approved fast-forward synchronization required')
    return summary | {'identity':identity,'control_plane':CANONICAL,'runtime_commit':local,'authority':'policy/authority.json','classification_map':'policy/repository-classes.json','approval':'explicit_owner','freshness':'remote_main_verified'}

def main(mode):
    parser = argparse.ArgumentParser()
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--control-plane',type=Path,default=ROOT)
    if mode == 'repository':
        parser.add_argument('repository_path',type=Path)
        parser.add_argument('--expected-repository',required=True)
    args = parser.parse_args()
    try:
        if mode == 'preflight': data = preflight(args.control_plane.resolve())
        elif mode == 'repository': data = validate_repository(args.control_plane.resolve(),args.repository_path.resolve(),args.expected_repository)
        else: data = validate_control_plane(args.control_plane.resolve())
        result = {'ok':True,'checks':data}
    except Exception as e:
        result = {'ok':False,'error':str(e) if isinstance(e,Invalid) else 'Unexpected validator failure: '+type(e).__name__}
    print(json.dumps(result,sort_keys=True) if args.json else ('PASS ' if result['ok'] else 'FAIL ') + json.dumps(result,sort_keys=True))
    return 0 if result['ok'] else 1
