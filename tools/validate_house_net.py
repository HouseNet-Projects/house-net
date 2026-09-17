#!/usr/bin/env python3
"""Root monorepo governance gate. Fails closed on missing or malformed control artifacts."""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD = tuple(f"HouseNet-Projects/house-net-{x}" for x in ("control-plane","design-system","command-center","knowledge","vault"))
def fail(msg): print(f"FAIL — {msg}"); return 2
def main():
    try:
        control=json.loads((ROOT/'house-net-control.json').read_text())
        matrix=json.loads((ROOT/'docs/governance/enforcement-matrix.json').read_text())
        docs=json.loads((ROOT/'docs/document-index.json').read_text())
    except Exception as e: return fail(f"control artifact unreadable: {type(e).__name__}")
    if control.get('repository')!='HouseNet-Projects/house-net' or control.get('control_plane')!='HouseNet-Projects/house-net': return fail('root canonical authority mismatch')
    if control.get('policy_version')!='1.4.3': return fail('unsupported policy version')
    req=matrix.get('requirements',[])
    if len(req)<1 or len({x.get('requirement_id') for x in req})!=len(req): return fail('enforcement matrix ids are not unique')
    critical=[x for x in req if x.get('severity')=='CRITICAL']
    required_fields=('source_policy','scope','enforcement_location','runtime_gate','validation_command','CI_check','test_ids','documentation_reference')
    if any(any(k not in x for k in required_fields) or not x.get('enforcement_location') or not x.get('validation_command') or not x.get('CI_check') or x.get('fail_closed') is not True for x in critical): return fail('critical requirement lacks complete executable enforcement mapping')
    if not isinstance(docs,list) or not docs or any(not x.get('path') or x.get('category') in ('UNKNOWN_PURPOSE',None) for x in docs): return fail('documentation index has unknown entries')
    tracked={p.as_posix() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and not any(part in ('__pycache__','.venv') for part in p.parts)}
    indexed={x['path'] for x in docs}
    doc_ext={'.md','.txt','.rst','.docx','.pdf','.pptx','.xlsx'}
    required={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in doc_ext and '.git' not in p.parts and not any(part in ('__pycache__','.venv') for part in p.parts)}
    if not required.issubset(indexed): return fail(f'documentation index missing {len(required-indexed)} files')
    # Active workflow/runtime references to archived repositories are forbidden; historical docs remain allowed.
    for p in (ROOT/'.github').rglob('*'):
        if p.is_file() and any(old in p.read_text(errors='ignore') for old in OLD): return fail(f'active CI references archived repository: {p.relative_to(ROOT)}')
    print(json.dumps({'ok':True,'critical_requirements':len(critical),'requirements':len(req),'indexed_documents':len(docs)},ensure_ascii=False))
    return 0
if __name__=='__main__': sys.exit(main())
