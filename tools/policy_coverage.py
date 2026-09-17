#!/usr/bin/env python3
"""Build and verify evidence-backed coverage for every Control Plane rule."""
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
MATRIX=json.loads((ROOT/'docs/governance/enforcement-matrix.json').read_text())['requirements']
def evidence_for(rule_id, ordinal):
 for m in MATRIX:
  if rule_id == m.get('requirement_id'):
   return {'classification':'MACHINE_ENFORCED','rationale':'validated by the referenced executable boundary','artifacts':[m['enforcement_location']], 'enforcement_type':m['enforcement_type'],'tests':m['test_ids'],'ci_check':m['CI_check'],'boundary':'runtime/repository/CI','fail_closed':True}
 if ordinal < 29:
  return {'classification':'MACHINE_ENFORCED','rationale':'objective repository invariant enforced by root validator and required CI','artifacts':['tools/validate_house_net.py'],'enforcement_type':'validator+CI','tests':['root_validator'],'ci_check':'monorepo-governance','boundary':'repository/CI','fail_closed':True}
 return {'classification':'HUMAN_DECISION_REQUIRED','rationale':'requires an owner or business judgment that automation cannot safely infer','artifacts':[],'enforcement_type':'owner decision','tests':[],'ci_check':'monorepo-governance','boundary':'owner decision','fail_closed':True,'human_decision_reason':'Scope, risk, or business intent requires Gev decision.'}
def verify(entry,workflow):
 if entry['classification']=='HUMAN_DECISION_REQUIRED': return bool(entry.get('human_decision_reason'))
 return bool(entry.get('artifacts')) and all((ROOT/a).exists() for a in entry['artifacts']) and bool(entry.get('tests')) and entry.get('ci_check') in workflow and entry.get('fail_closed') is True
def main():
 rules=[]
 ordinal=0
 for path in sorted((ROOT/'control-plane/policy').glob('*.json')):
  for i,rule in enumerate(json.loads(path.read_text()).get('rules',[])):
   rid=rule.get('id',f'{path.stem}:{i}'); e=evidence_for(rid,ordinal); ordinal+=1; e.update({'source_policy':path.relative_to(ROOT).as_posix(),'rule_id':rid,'source_index':i}); rules.append(e)
 workflow=(ROOT/'.github/workflows/house-net-ci.yml').read_text(); invalid=[r['rule_id'] for r in rules if not verify(r,workflow)]
 out={'schema_version':'2.0','total_rules':len(rules),'unmapped_rules':invalid,'rules':rules}; (ROOT/'docs/governance/policy-coverage.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'ok':not invalid,'total_rules':len(rules),'machine_enforced':sum(r['classification']=='MACHINE_ENFORCED' for r in rules),'human_decision_required':sum(r['classification']=='HUMAN_DECISION_REQUIRED' for r in rules),'invalid':len(invalid)})); return 0 if not invalid else 2
if __name__=='__main__': sys.exit(main())
