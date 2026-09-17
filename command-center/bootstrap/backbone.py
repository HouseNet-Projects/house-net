#!/usr/bin/env python3
"""Deterministic HouseNet zero-state bootstrap. Dry-run is the default."""
import argparse, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; MANIFEST=ROOT/'bootstrap/backbone-manifest.json'
def fail(msg): raise RuntimeError(msg)
def run(cmd,cwd=None):
 p=subprocess.run([str(x) for x in cmd],cwd=str(cwd) if cwd else None,text=True,capture_output=True)
 return p.returncode,p.stdout.strip(),p.stderr.strip()
def report(out,step,status,detail): out['steps'].append({'step':step,'status':status,'detail':detail}); out['ok'] &= status=='PASS'
def remote(path):
 rc,out,err=run(['git','remote','get-url','origin'],path); return out if rc==0 else ''
def same_url(actual, expected):
 def norm(x): return x[:-4] if x.endswith('.git') else x
 return norm(actual.rstrip('/')) == norm(expected.rstrip('/'))
def acquire(spec, workspace, apply, out):
 path=workspace/spec['id']; expected=spec['url']
 if not path.exists():
  if not apply: report(out,'acquire:'+spec['id'],'FAIL','repository missing in dry-run; apply is required to clone'); return None
  workspace.mkdir(parents=True,exist_ok=True); rc,o,e=run(['git','clone','--branch',spec['branch'],expected,str(path)])
  if rc!=0: report(out,'acquire:'+spec['id'],'FAIL','clone failed'); return None
 if not (path/'.git').exists(): report(out,'acquire:'+spec['id'],'FAIL','path is not a Git repository'); return None
 if not same_url(remote(path), expected): report(out,'acquire:'+spec['id'],'FAIL','origin mismatch'); return None
 rc,head,err=run(['git','rev-parse','HEAD'],path); report(out,'acquire:'+spec['id'],'PASS',f'origin verified; head={head}'); return path
def prepare_explicit(spec, path, out):
 if path is None or not path.exists():
  report(out,'acquire:'+spec['id'],'FAIL','explicit repository path unavailable'); return None
 if not (path/'.git').exists():
  report(out,'acquire:'+spec['id'],'FAIL','path is not a Git repository'); return None
 if not same_url(remote(path), spec['url']):
  report(out,'acquire:'+spec['id'],'FAIL','origin mismatch'); return None
 rc,head,err=run(['git','rev-parse','HEAD'],path)
 report(out,'acquire:'+spec['id'],'PASS',f'origin verified; head={head}')
 return path
def validate_repo(spec,path,out):
 if path is None: return
 lock=path/'house-net-control.json'
 if not lock.is_file(): report(out,'lock:'+spec['id'],'FAIL','house-net-control.json missing'); return
 try: data=json.loads(lock.read_text())
 except Exception: report(out,'lock:'+spec['id'],'FAIL','invalid control lock'); return
 if data.get('repository')!=spec['repository'] or data.get('policy_version')!=out['manifest']['control_plane']['policy_version'] or data.get('policy_commit')!=out['manifest']['control_plane']['policy_commit']:
  report(out,'lock:'+spec['id'],'FAIL','repository identity/policy lock mismatch'); return
 validator=path/spec['validator']
 if not validator.is_file(): report(out,'validate:'+spec['id'],'FAIL','validator missing'); return
 rc,o,e=run([sys.executable,str(validator)])
 report(out,'validate:'+spec['id'],'PASS' if rc==0 else 'FAIL',o or e)
 if spec['id']=='knowledge':
  idx=path/'knowledge/index/catalog.json'
 else: idx=path/'vault/index.json'
 if not idx.is_file(): report(out,'index:'+spec['id'],'FAIL','required index missing')
 else:
  try: json.loads(idx.read_text()); report(out,'index:'+spec['id'],'PASS','index JSON readable')
  except Exception: report(out,'index:'+spec['id'],'FAIL','index JSON corrupted')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--workspace',type=Path,default=ROOT/'bootstrap/workspace'); ap.add_argument('--control-plane-path',type=Path); ap.add_argument('--knowledge-path',type=Path); ap.add_argument('--vault-path',type=Path); ap.add_argument('--report-dir',type=Path,default=ROOT/'bootstrap/reports'); ap.add_argument('--apply',action='store_true'); ap.add_argument('--json',action='store_true'); args=ap.parse_args()
 m=json.loads(MANIFEST.read_text()); out={'ok':True,'mode':'apply' if args.apply else 'dry-run','manifest':m,'steps':[],'secrets_exposed':False,'started_at':datetime.now(timezone.utc).isoformat()}
 cp_arg=args.control_plane_path
 cp=cp_arg or (Path(os.environ['HOUSENET_CONTROL_PLANE_PATH']) if os.environ.get('HOUSENET_CONTROL_PLANE_PATH') else None)
 if cp_arg is not None or cp is not None:
  if cp is None or not cp.exists() or not (cp/'.git').exists():
   report(out,'acquire:control-plane','FAIL','explicit control-plane path unavailable'); cp=None
  elif not same_url(remote(cp), m['control_plane']['url']):
   report(out,'control-plane-origin','FAIL','origin mismatch'); cp=None
  else: report(out,'control-plane-origin','PASS','origin verified')
 else:
  if args.apply:
   cp=args.workspace/'control-plane'; args.workspace.mkdir(parents=True,exist_ok=True); rc,o,e=run(['git','clone','--branch','main',m['control_plane']['url'],str(cp)])
   if rc!=0: report(out,'acquire:control-plane','FAIL','clone failed'); cp=None
   else: report(out,'acquire:control-plane','PASS','cloned canonical control plane')
  else: report(out,'acquire:control-plane','FAIL','control plane missing in dry-run; apply is required') ; cp=None
 if cp:
  lock=cp/'release/manifest.json'
  try: v=json.loads(lock.read_text()); report(out,'control-plane-version','PASS' if v.get('version')==m['control_plane']['policy_version'] else 'FAIL',f"version={v.get('version')}")
  except Exception: report(out,'control-plane-version','FAIL','release manifest missing/corrupt')
  pre=cp/'bin/housenet-preflight'
  if pre.is_file(): rc,o,e=run([str(pre),'--json'],cp); report(out,'control-plane-preflight','PASS' if rc==0 else 'FAIL',o or e)
  else: report(out,'control-plane-preflight','FAIL','preflight missing')
 paths={}
 for spec in m['repositories']:
  explicit={'knowledge':args.knowledge_path,'vault':args.vault_path}.get(spec['id'])
  paths[spec['id']]=prepare_explicit(spec,explicit,out) if explicit is not None else acquire(spec,args.workspace,args.apply,out)
  validate_repo(spec,paths[spec['id']],out)
 # Only non-secret context is restored. Existing valid state is never overwritten.
 if out['ok'] and args.apply:
  args.report_dir.mkdir(parents=True,exist_ok=True); marker=args.report_dir/'backbone-state.json';
  if marker.exists(): report(out,'restore-state','PASS','existing valid non-secret state retained (idempotent)')
  else: marker.write_text(json.dumps({'schema':m['schema'],'restored_non_secret_context':True},indent=2)+'\n'); report(out,'restore-state','PASS','non-secret context restored')
 elif not args.apply: report(out,'restore-state','PASS','dry-run; no local state changed')
 else: report(out,'restore-state','SKIP','blocked by failed verification')
 out['finished_at']=datetime.now(timezone.utc).isoformat(); args.report_dir.mkdir(parents=True,exist_ok=True); (args.report_dir/'backbone-report.json').write_text(json.dumps(out,indent=2)+'\n');
 if args.json: print(json.dumps(out,sort_keys=True))
 else:
  for s in out['steps']: print(f"{s['status']} — {s['step']}: {s['detail']}")
  print('PASS — zero-state bootstrap verified' if out['ok'] else 'FAIL — zero-state bootstrap blocked')
 return 0 if out['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
