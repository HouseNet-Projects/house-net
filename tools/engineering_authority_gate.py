#!/usr/bin/env python3
"""Required PR gate binding a change to a bounded engineering envelope.

Governance-boundary changes intentionally defer owner-principal proof to the
protected PR review gate; all ordinary changes require an envelope.
"""
import json, os, pathlib, subprocess, sys
from engineering_authority import validate
ROOT=pathlib.Path(__file__).resolve().parents[1]
AUTHORITY_PATH='.github/engineering-authority.json'
SENSITIVE=(' .github/'.strip(), 'CODEOWNERS', 'house-net-control.json', 'control-plane/policy/',
 'control-plane/schemas/', 'docs/governance/', 'tools/engineering_authority.py',
 'tools/engineering_authority_gate.py', 'tools/validate_house_net.py', 'tools/policy_coverage.py',
 'tools/secret_scan.py', 'vault/bin/validate-vault', 'command-center/.claude/skills/actions.py')
def sh(*args): return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def ancestor(older,newer): return subprocess.run(['git','merge-base','--is-ancestor',older,newer],cwd=ROOT).returncode==0
def is_sensitive(paths): return any(any(p==s or p.startswith(s) for s in SENSITIVE) for p in paths)
def changed_paths(base, head):
 return [p for p in sh('git','diff','--name-only',f'{base}...{head}').splitlines() if p]
def main():
 # PRs carry the bounded envelope. Push builds have no PR context; their
 # merged commit is covered by the remaining mandatory validation jobs.
 if os.environ.get('GITHUB_EVENT_NAME') not in ('pull_request', 'pull_request_target'):
  print(json.dumps({'ok':True,'mode':'PUSH_COMMIT_NO_PR_BINDING'})); return 0
 base=os.environ.get('GITHUB_BASE_SHA') or sh('git','rev-parse','origin/main')
 head=os.environ.get('GITHUB_EVENT_PULL_REQUEST_HEAD_SHA') or os.environ.get('GITHUB_SHA') or sh('git','rev-parse','HEAD')
 paths=changed_paths(base,head)
 env_path=os.environ.get('HOUSENET_ENGINEERING_AUTHORITY_FILE') or str(ROOT/'.github/engineering-authority.json')
 envelope=None
 if env_path and pathlib.Path(env_path).exists(): envelope=json.loads(pathlib.Path(env_path).read_text())
 elif os.environ.get('HOUSENET_ENGINEERING_AUTHORITY_JSON'):
  envelope=json.loads(os.environ['HOUSENET_ENGINEERING_AUTHORITY_JSON'])
 # A committed envelope is PR-bound. Never reuse a record issued for another
 # PR; sensitive-path changes then fall through to the owner-review boundary.
 if envelope and envelope.get('pr') and str(envelope['pr']) != os.environ.get('GITHUB_EVENT_PULL_REQUEST_NUMBER',''):
  envelope=None
 sensitive=is_sensitive(paths)
 if envelope:
  if envelope.get('base_sha') and not ancestor(envelope['base_sha'],base): return fail('envelope base is not ancestor of PR base')
  if envelope.get('branch') and envelope['branch'] != os.environ.get('GITHUB_HEAD_REF',''): return fail('branch binding mismatch')
  if envelope.get('pr') and str(envelope['pr']) != os.environ.get('GITHUB_EVENT_PULL_REQUEST_NUMBER',''): return fail('PR binding mismatch')
  if not envelope.get('approval_reference'): return fail('missing approval reference')
  # The envelope file is control metadata, not a capability it can grant to
  # itself. It is validated by the external authority source in Task 4; until
  # then it is excluded from the PR payload paths while every product path is
  # still checked against allowed_paths.
  for p in (p for p in paths if p != AUTHORITY_PATH):
   ok,reason=validate(envelope,'edit',p)
   if not ok: return fail(f'path {p}: {reason}')
  print(json.dumps({'ok':True,'mode':'ENVELOPE_BOUND','changed_paths':len(paths)})); return 0
 if sensitive:
  # A review note is not an authorization.  Protected branch review remains
  # useful, but this required check must fail closed until a bounded envelope
  # is present and bound to the exact PR/base/path set.
  return fail('sensitive change requires an EngineeringAuthorityEnvelope bound to this PR')
 return fail('ordinary PR requires EngineeringAuthorityEnvelope')
def fail(msg): print('FAIL — '+msg); return 2
if __name__=='__main__': sys.exit(main())
