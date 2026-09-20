#!/usr/bin/env python3
"""Build and verify evidence-backed coverage for every Control Plane rule."""
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
MATRIX=json.loads((ROOT/'docs/governance/enforcement-matrix.json').read_text())['requirements']
EXPLICIT={m.get('requirement_id'): m for m in MATRIX}

def evidence_for(rule):
    """Return evidence only from an explicit rule mapping.

    A rule's position in a policy file is never evidence of enforcement. Rules
    that name an owner-review/settings boundary remain human decisions; every
    other machine mechanism must have a dedicated matrix entry.
    """
    rule_id=rule.get('id')
    m=EXPLICIT.get(rule_id)
    if m:
        return {'classification':'MACHINE_ENFORCED','rationale':m.get('rationale','validated by the explicitly named executable boundary'),'artifacts':[m['enforcement_location']], 'enforcement_type':m['enforcement_type'],'tests':m['test_ids'],'ci_check':m['CI_check'],'boundary':'runtime/repository/CI','fail_closed':True}
    mechanism=str(rule.get('enforcement',{}).get('mechanism',''))
    human=('owner_review' in mechanism or 'repository_settings_audit' in mechanism or
           'registration_and_owner_review' in mechanism or mechanism in ('owner decision',''))
    if human:
        return {'classification':'HUMAN_DECISION_REQUIRED','rationale':'requires an owner or business judgment that automation cannot safely infer','artifacts':[],'enforcement_type':'owner decision','tests':[],'ci_check':'monorepo-governance','boundary':'owner decision','fail_closed':True,'human_decision_reason':'Scope, risk, or business intent requires Gev decision.'}
    return {'classification':'UNMAPPED_MACHINE_ENFORCEMENT','rationale':'no explicit enforcement matrix entry exists for this machine mechanism','artifacts':[],'enforcement_type':mechanism,'tests':[],'ci_check':'','boundary':'repository/CI','fail_closed':False}
def verify(entry,workflow):
 if entry['classification']=='HUMAN_DECISION_REQUIRED': return bool(entry.get('human_decision_reason'))
 return bool(entry.get('artifacts')) and all((ROOT/a).exists() for a in entry['artifacts']) and bool(entry.get('tests')) and entry.get('ci_check') in workflow and entry.get('fail_closed') is True
def main(argv=None):
 argv = list(argv or sys.argv[1:])
 check = '--check' in argv
 rules=[]
 for path in sorted((ROOT/'control-plane/policy').glob('*.json')):
  for i,rule in enumerate(json.loads(path.read_text()).get('rules',[])):
   rid=rule.get('id',f'{path.stem}:{i}'); e=evidence_for(rule); e.update({'source_policy':path.relative_to(ROOT).as_posix(),'rule_id':rid,'source_index':i}); rules.append(e)
 workflow=(ROOT/'.github/workflows/house-net-ci.yml').read_text(); invalid=[r['rule_id'] for r in rules if not verify(r,workflow)]
 invalid += [r['rule_id'] for r in rules if r['classification']=='UNMAPPED_MACHINE_ENFORCEMENT']
 out={'schema_version':'2.0','total_rules':len(rules),'unmapped_rules':sorted(set(invalid)),'rules':rules}
 target=ROOT/'docs/governance/policy-coverage.json'; rendered=json.dumps(out,indent=2)+'\n'
 matches=target.exists() and target.read_text(encoding='utf-8') == rendered
 if not check:
  target.write_text(rendered, encoding='utf-8'); matches=True
 ok=not invalid and (matches if check else True)
 print(json.dumps({'ok':ok,'mode':'check' if check else 'write','matches':matches,'total_rules':len(rules),'machine_enforced':sum(r['classification']=='MACHINE_ENFORCED' for r in rules),'human_decision_required':sum(r['classification']=='HUMAN_DECISION_REQUIRED' for r in rules),'invalid':len(invalid)})); return 0 if ok else 2
if __name__=='__main__': sys.exit(main())
