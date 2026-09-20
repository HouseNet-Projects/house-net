#!/usr/bin/env python3
"""Generate the tracked-path purpose inventory used by zero-trust closure.

The inventory is deliberately deterministic and classifies every tracked path;
unknown purpose is a hard failure rather than a silently omitted file.
"""
from __future__ import annotations
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def purpose(path: str) -> str:
    p = pathlib.PurePosixPath(path)
    n = p.name.lower()
    if '/05_archive/' in ('/' + path.lower()) or '/historical/' in ('/' + path.lower()): return 'historical'
    if path.startswith('.github/') or '/.github/' in path: return 'ci'
    if path.startswith('tools/') or path.startswith('control-plane/bin/'): return 'governance_tool'
    if path.startswith('deploy/') or path.endswith('.service') or path.endswith('.timer'): return 'deployment'
    if 'test' in n or '/tests/' in path: return 'test'
    if path.startswith('design-system/'): return 'design_system'
    if path.startswith('knowledge/'): return 'knowledge'
    if path.startswith('vault/'): return 'vault'
    if path.startswith('docs/') or n in {'readme.md','agents.md','claude.md'}: return 'documentation'
    if path.startswith('command-center/WORKSPACE/'): return 'business_source'
    if path.startswith('command-center/') or path.endswith('.py'): return 'runtime'
    if n.endswith(('.json','.yaml','.yml','.toml','.lock')): return 'canonical_config'
    if n.endswith(('.md','.txt','.rst')): return 'documentation'
    if n.endswith(('.svg','.css','.js')): return 'product_asset'
    if n.endswith(('.xlsx','.docx','.pptx','.pdf','.zip')): return 'business_source'
    return 'repository_metadata'

def build() -> dict:
    out = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT)
    paths = [p for p in out.decode().split('\0') if p]
    entries = [{'path': p, 'purpose': purpose(p)} for p in paths]
    unknown = [e['path'] for e in entries if e['purpose'] == 'UNKNOWN_PURPOSE']
    return {'schema': 'housenet.repository.inventory.v1', 'repository': 'HouseNet-Projects/house-net',
            'source': 'git ls-files', 'tracked_count': len(entries), 'unknown_purpose': unknown,
            'entries': entries, 'ok': not unknown}

def main(argv=None):
    data = build(); target = ROOT / 'docs' / 'governance' / 'repository-inventory.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': data['ok'], 'tracked_count': data['tracked_count'], 'unknown_purpose': len(data['unknown_purpose'])}))
    return 0 if data['ok'] else 1

if __name__ == '__main__': sys.exit(main())
