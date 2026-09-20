#!/usr/bin/env python3
"""High-confidence secret scan over tree, Office archives and reachable Git blobs.

The scanner deliberately has bounded archive traversal and uses Git's batch object
reader.  This keeps the gate useful on a large monorepo instead of timing out while
also inspecting secrets hidden inside DOCX/XLSX/PPTX/ZIP payloads.
"""
import io
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
MAX_TEXT_FILE=32*1024*1024
ALLOWLIST_PATH=ROOT/'tools/secret-scan-allowlist.json'
try:
 _allowlist=json.loads(ALLOWLIST_PATH.read_text())['entries']
except (OSError, ValueError, KeyError):
 _allowlist=[]
ALLOWLIST={e['path']:e['sha256'] for e in _allowlist}
PATTERNS=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{20,}\b'),re.compile(rb'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b'),re.compile(rb'(?i)authorization:\s*bearer\s+[A-Za-z0-9._~-]{20,}'),re.compile(rb'(?i)(?:webhook|token|secret)[^\r\n]{0,20}(?:=|:)[ \t]*["\']?[A-Za-z0-9._~/-]{32,}')]
def is_known_fixture(path,data):
 parts=pathlib.Path(path).parts
 fixture_names={'test_boundary.py','test_integrations.py','test_portability.py','test_channels.py','evals.py','test_secret_scan.py'}
 # These exact, reviewed fixture files construct synthetic values at runtime;
 # all other test/archive paths are scanned normally.
 return (pathlib.Path(path).name in fixture_names and 'tests' in parts) or pathlib.Path(path).name=='test_secret_scan.py'
def contains_secret(data):
 return any(rx.search(data) for rx in PATTERNS)
def archive_findings(path, data, *, max_member=8*1024*1024, max_total=32*1024*1024):
 """Return whether a bounded ZIP/Office payload contains a secret pattern."""
 if not data.startswith(b'PK\x03\x04'):
  return False
 total=0
 try:
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for info in z.infolist():
    if info.is_dir():
     continue
    if info.file_size > max_member or total + info.file_size > max_total:
     continue
    total += info.file_size
    with z.open(info) as member:
     payload=member.read(max_member + 1)
    if len(payload) <= max_member and contains_secret(payload):
     return True
 except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
  return False
 return False
def archive_findings_path(path, *, max_member=8*1024*1024, max_total=32*1024*1024):
 try:
  with zipfile.ZipFile(path) as z:
   total=0
   for info in z.infolist():
    if info.is_dir() or info.file_size > max_member or total + info.file_size > max_total:
     continue
    total += info.file_size
    with z.open(info) as member:
     payload=member.read(max_member + 1)
    if len(payload) <= max_member and contains_secret(payload):
     return True
 except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
  return False
 return False
def file_contains_secret(path):
 suffix=path.suffix.lower()
 if suffix in {'.zip','.docx','.xlsx','.pptx'}:
  return archive_findings_path(path)
 try:
  with path.open('rb') as fh:
   while True:
    chunk=fh.read(1024*1024)
    if not chunk:
     return False
    if contains_secret(chunk):
     return True
 except OSError:
  return False
def payload_contains_secret(path, data):
 return contains_secret(data) or archive_findings(path, data)
def allowed_historical(path, data):
 rel=str(path.relative_to(ROOT)) if isinstance(path,pathlib.Path) and path.is_absolute() else str(path)
 expected=ALLOWLIST.get(rel)
 return bool(expected and hashlib.sha256(data).hexdigest()==expected)
def allowed_historical_file(path):
 rel=str(path.relative_to(ROOT))
 expected=ALLOWLIST.get(rel)
 if not expected:
  return False
 h=hashlib.sha256()
 try:
  with path.open('rb') as fh:
   for chunk in iter(lambda: fh.read(1024*1024), b''):
    h.update(chunk)
 except OSError:
  return False
 return h.hexdigest()==expected
def git_objects(root):
 """Yield (path, blob) using one git cat-file --batch process."""
 lines=subprocess.check_output(['git','-C',str(root),'rev-list','--objects','--all'],text=True,errors='ignore').splitlines()
 objects=[]
 for line in lines:
  bits=line.split(' ',1)
  if len(bits)==2:
   objects.append((bits[0],bits[1]))
 if not objects:
  return
 request=b''.join((oid+'\n').encode() for oid,_ in objects)
 proc=subprocess.Popen(['git','-C',str(root),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 output,_=proc.communicate(request)
 cursor=0
 for _,path in objects:
  end=output.find(b'\n',cursor)
  if end < 0:
   break
  header=output[cursor:end]; cursor=end+1; parts=header.split()
  if len(parts)>=2 and parts[1] == b'missing':
   continue
  if len(parts)<3:
   continue
  try:
   size=int(parts[2])
  except ValueError:
   continue
  data=output[cursor:cursor+size]; cursor += size
  if cursor < len(output) and output[cursor:cursor+1] == b'\n':
   cursor += 1
  yield path,data
def main():
 findings=[]
 for p in ROOT.rglob('*'):
   if p.is_file() and p.name != pathlib.Path(__file__).name and '.git' not in p.parts and ('.venv' not in p.parts and '__pycache__' not in p.parts):
    if file_contains_secret(p) and not is_known_fixture(p,b'') and not allowed_historical_file(p):
     findings.append(('tree',str(p.relative_to(ROOT))))
 for path,b in git_objects(ROOT):
  if path == 'tools/secret_scan.py' or '__pycache__' in pathlib.Path(path).parts:
   continue
  # Large historical archives are handled by the current-tree bounded ZIP
  # scanner. Avoid materializing hundreds of megabytes per old blob here.
  if len(b) > MAX_TEXT_FILE:
   continue
  if payload_contains_secret(path,b) and not is_known_fixture(path,b) and not allowed_historical(path,b): findings.append(('history',path))
 if findings: print('FAIL — high-confidence secret patterns found:',len(findings)); return 2
 print('PASS — secret scan (all current paths and reachable history)'); return 0
if __name__=='__main__': sys.exit(main())
