#!/usr/bin/env python3
"""Required PR gate binding a change to a bounded engineering envelope.

Governance-boundary changes intentionally defer owner-principal proof to the
protected PR review gate; all ordinary changes require an envelope.
"""
import json, os, pathlib, subprocess, sys
from engineering_authority import validate
ROOT=pathlib.Path(__file__).resolve().parents[1]
SENSITIVE=(' .github/'.strip(), 'CODEOWNERS', 'house-net-control.json', 'control-plane/policy/',
 'control-plane/schemas/', 'docs/governance/', 'tools/engineering_authority.py',
 'tools/engineering_authority_gate.py', 'tools/validate_house_net.py', 'tools/policy_coverage.py',
 'tools/secret_scan.py', 'vault/bin/validate-vault', 'command-center/.claude/skills/actions.py')
def sh(*args): return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def main():
 base=os.environ.get('GITHUB_BASE_SHA') or sh('git','rev-parse','origin/main')
 head=os.environ.get('GITHUB_SHA') or sh('git','rev-parse','HEAD')
 paths=[p for p in sh('git','diff','--name-only',f'{base}...{head}').splitlines() if p]
 env_path=os.environ.get('HOUSENET_ENGINEERING_AUTHORITY_FILE')
 envelope=None
 if env_path and pathlib.Path(env_path).exists(): envelope=json.loads(pathlib.Path(env_path).read_text())
 elif os.environ.get('HOUSENET_ENGINEERING_AUTHORITY_JSON'):
  envelope=json.loads(os.environ['HOUSENET_ENGINEERING_AUTHORITY_JSON'])
 sensitive=any(any(p==s or p.startswith(s) for s in SENSITIVE) for p in paths)
 if envelope:
  if envelope.get('base_sha') and not sh('git','merge-base','--is-ancestor',envelope['base_sha'],base): return fail('envelope base is not ancestor of PR base')
  if envelope.get('branch') and envelope['branch'] != os.environ.get('GITHUB_HEAD_REF',''): return fail('branch binding mismatch')
  if envelope.get('pr') and str(envelope['pr']) != os.environ.get('GITHUB_EVENT_PULL_REQUEST_NUMBER',''): return fail('PR binding mismatch')
  if not envelope.get('owner_proof'): return fail('missing owner principal proof')
  for p in paths:
   ok,reason=validate(envelope,'edit',p)
   if not ok: return fail(f'path {p}: {reason}')
  print(json.dumps({'ok':True,'mode':'ENVELOPE_BOUND','changed_paths':len(paths)})); return 0
 if sensitive:
  print(json.dumps({'ok':True,'mode':'OWNER_REVIEW_REQUIRED','changed_paths':len(paths),'owner_principal':'PENDING'})); return 0
 return fail('ordinary PR requires EngineeringAuthorityEnvelope')
def fail(msg): print('FAIL — '+msg); return 2
if __name__=='__main__': sys.exit(main())
