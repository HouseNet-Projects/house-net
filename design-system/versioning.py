"""Universal HouseNet version contract for this repository."""
from pathlib import Path
import json, re
SEMVER_RE = re.compile(r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
def valid_semver(v): return isinstance(v,str) and SEMVER_RE.fullmatch(v) is not None
def manifest(root):
    p=root/'release/manifest.json'
    if not p.is_file(): raise ValueError('Canonical version source missing: release/manifest.json')
    d=json.loads(p.read_text())
    if not valid_semver(d.get('version')): raise ValueError('Invalid canonical SemVer')
    return d
def check(root):
    d=manifest(root); expected=d['version']; errors=[]
    for s in d['version_surfaces']:
        p=root/s['path']
        if not p.is_file(): errors.append(f'file={s["path"]} expected={expected} actual=missing'); continue
        if s['kind']=='json':
            value=json.loads(p.read_text())
            for part in s.get('field','version').split('.'): value=value[part]
            if value != expected: errors.append(f'file={s["path"]} field={s.get("field")} expected={expected} actual={value}')
        elif expected not in p.read_text(errors='ignore'):
            errors.append(f'file={s["path"]} expected={expected} actual=missing')
    return errors
