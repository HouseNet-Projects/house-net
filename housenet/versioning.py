"""Portable single-source version helpers used by HouseNet repositories."""
from __future__ import annotations
import json
import re
from pathlib import Path

SEMVER_RE = re.compile(r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')

def valid_semver(value: str) -> bool:
    return isinstance(value, str) and SEMVER_RE.fullmatch(value) is not None

def read_manifest(root: Path) -> dict:
    path = root / 'release/manifest.json'
    if not path.is_file():
        raise ValueError('Canonical version source missing: release/manifest.json')
    data = json.loads(path.read_text())
    if not valid_semver(data.get('version')):
        raise ValueError('Canonical version is not strict SemVer')
    return data

def _replace_version(text: str, old: str, new: str, marker: str) -> str:
    lines = text.splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        if marker in line:
            updated = line.replace(old, new)
            lines[i] = updated
            changed |= updated != line
    return ''.join(lines) if changed else text

def sync_surfaces(root: Path, new_version: str) -> list[str]:
    manifest_path = root / 'release/manifest.json'
    manifest = read_manifest(root)
    old = manifest['version']
    manifest['version'] = new_version
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    changed = ['release/manifest.json']
    for surface in manifest.get('version_surfaces', []):
        path = root / surface['path']
        if not path.is_file():
            raise ValueError('Registered version surface missing: ' + surface['path'])
        if path.suffix.lower() == '.json':
            data = json.loads(path.read_text())
            field = surface.get('field', 'version')
            current = data
            parts = field.split('.')
            for part in parts[:-1]: current = current[part]
            current[parts[-1]] = new_version
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        else:
            updated = _replace_version(path.read_text(), old, new_version, surface['marker'])
            if updated == path.read_text() and old in path.read_text():
                raise ValueError('Version surface marker did not update: ' + surface['path'])
            path.write_text(updated)
        changed.append(surface['path'])
    return changed
