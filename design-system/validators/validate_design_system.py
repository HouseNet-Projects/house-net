"""Deterministic design-system checks; subjective visual quality stays human-reviewed."""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
REF = re.compile(r"\{([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)\}")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from versioning import manifest as read_version_manifest, check as check_versions

class Invalid(ValueError): pass
def require(condition, message):
    if not condition: raise Invalid(message)

def flatten_tokens(value, group=''):
    result = {}
    if isinstance(value, dict):
        if 'value' in value: result[group] = value['value']
        else:
            for k, v in value.items(): result.update(flatten_tokens(v, f'{group}.{k}'.strip('.')))
    return result

def load(path):
    try: return json.loads(path.read_text())
    except Exception as exc: raise Invalid(f'Invalid JSON: {path}') from exc

def human_docs(root):
    skip = {'AGENTS.md', 'CLAUDE.md'}
    for p in root.rglob('*.md'):
        if '.git' in p.parts or p.name in skip: continue
        if p.is_file(): yield p

def validate(root=ROOT):
    release = read_version_manifest(root)
    require(release['repository'] == 'HouseNet-Projects/house-net-design-system', 'Release manifest repository mismatch')
    require(release['control_plane_version'] == '1.4.3', 'Release manifest control-plane version mismatch')
    require(not check_versions(root), 'VERSION DRIFT')
    brand = load(root/'tokens/brand-tokens.json')
    document = load(root/'tokens/document-tokens.json')
    require(brand['version'] == document['version'] == release['version'], 'Token versions must match design-system version')
    all_tokens = flatten_tokens(brand) | flatten_tokens(document)
    require(len(all_tokens) == len(set(all_tokens)), 'Duplicate token path')
    for name, token in brand.get('color', {}).items():
        require(HEX.fullmatch(token['value']), f'Invalid color token: {name}')
    for path in [root/'assets/brand/original/housenet-main-logo.svg', root/'assets/brand/original/housenet-footer-logo.svg']:
        require(path.is_file(), f'Missing original logo: {path}')
    expected = {
      'housenet-main-logo.svg':'a903655a7180e4cbb94145002b391e44c1059cb04b56dde4277ab06f569c8345',
      'housenet-footer-logo.svg':'06ea8739ca3f3aa9759328a776eeae048c8fbf4633ca4b1f51414e2a59842b3b'}
    for name, sha in expected.items():
        actual = hashlib.sha256((root/'assets/brand/original'/name).read_bytes()).hexdigest()
        require(actual == sha, f'Logo provenance checksum mismatch: {name}')
    manifest = load(root/'documents/templates/template-manifest.json')
    require(manifest['version'] == release['version'] and manifest['templates'], 'Template manifest invalid')
    for item in manifest['templates']:
        path = root/item['source']; require(path.is_file(), f'Missing template source: {item["source"]}')
        if path.suffix == '.md':
            text = path.read_text(); require('## English' in text and '## Հայերեն' in text, f'Template is not bilingual: {item["source"]}')
    for path in human_docs(root):
        text = path.read_text()
        require(re.search(r'^## English\s*$', text, re.M), f'English section missing: {path.relative_to(root)}')
        require(re.search(r'^## Հայերեն\s*$', text, re.M), f'Armenian section missing: {path.relative_to(root)}')
    for path in root.rglob('*'):
        if path.is_file() and path.suffix in {'.md','.json','.html','.css','.svg'}:
            text = path.read_text(errors='ignore')
            require('http://' not in text and 'https://' not in text or 'github.com/HouseNet-Projects' in text or 'www.housenet.am' in text or 'json-schema.org' in text or 'www.w3.org' in text, f'Unexpected external dependency: {path.relative_to(root)}')
    # Static visual assets must remain timeless; volatile release values belong to generated status regions.
    semver = re.compile(r'\b\d+\.\d+\.\d+\b')
    for path in (root/'assets/brand/derived').glob('*.svg'):
        require(not semver.search(path.read_text(errors='ignore')), f'Volatile version embedded in static visual: {path.relative_to(root)}')
    for path in [root/'tokens/brand-tokens.json', root/'tokens/document-tokens.json']:
        data = path.read_text()
        for group, name in REF.findall(data): require(f'{group}.{name}' in all_tokens, f'Unknown token reference: {group}.{name}')
    return {'version': release['version'], 'human_docs': len(list(human_docs(root))), 'templates': len(manifest['templates']), 'tokens': len(all_tokens)}

if __name__ == '__main__':
    try: print(json.dumps({'ok': True, **validate(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT)}, sort_keys=True))
    except Invalid as exc: print(json.dumps({'ok': False, 'error': str(exc)})); raise SystemExit(1)
