#!/usr/bin/env python3
"""High-confidence secret scan over every tracked path and every reachable Git blob."""
import pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATTERNS=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),re.compile(rb'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b'),re.compile(rb'(?i)authorization:\s*bearer\s+[A-Za-z0-9._~-]{20,}'),re.compile(rb'(?i)(?:webhook|token|secret)[^\r\n]{0,20}(?:=|:)[ \t]*["\']?[A-Za-z0-9._~/-]{32,}')]
FIXTURE_MARKERS=(b'secret-shaped fixtures',b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',b'AKIA'+b'ABCDEFGHIJKLMNOP')
def is_known_fixture(path,data):
 parts=pathlib.Path(path).parts
 return ('tests' in parts) or pathlib.Path(path).name == 'test_secret_scan.py' or ('GAAHEX_CHECKPOINT_' in str(path)) or ('05_Archive' in parts)
def contains_secret(data):
 return any(rx.search(data) for rx in PATTERNS)
def main():
 findings=[]
 for p in ROOT.rglob('*'):
   if p.is_file() and p.name != pathlib.Path(__file__).name and '.git' not in p.parts and ('.venv' not in p.parts and '__pycache__' not in p.parts):
    try:
     data=p.read_bytes()
     if contains_secret(data) and not is_known_fixture(p,data): findings.append(('tree',str(p.relative_to(ROOT))))
    except OSError: pass
 for line in subprocess.check_output(['git','-C',str(ROOT),'rev-list','--objects','--all'],text=True,errors='ignore').splitlines():
  oid,path=(line.split(' ',1)+[''])[:2]
  try: b=subprocess.check_output(['git','-C',str(ROOT),'cat-file','-p',oid],stderr=subprocess.DEVNULL)
  except Exception: continue
  if path == 'tools/secret_scan.py':
   continue
  if contains_secret(b) and not is_known_fixture(path,b): findings.append(('history',path))
 if findings: print('FAIL — high-confidence secret patterns found:',len(findings)); return 2
 print('PASS — secret scan (all current paths and reachable history)'); return 0
if __name__=='__main__': sys.exit(main())
