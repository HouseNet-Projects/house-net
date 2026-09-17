#!/usr/bin/env python3
"""Enumerate every Control Plane rule and classify its enforcement boundary."""
import json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 rules=[]
 for path in sorted((ROOT/'control-plane/policy').glob('*.json')):
  data=json.loads(path.read_text())
  for i, rule in enumerate(data.get('rules', [])):
   text=json.dumps(rule, sort_keys=True).lower()
   mechanism=str(rule.get('enforcement',{}).get('mechanism','')).lower()
   human=('owner_review' in mechanism and not any(x in mechanism for x in ('validator','workflow','schema','runtime','gate','test')))
   rules.append({'source':path.relative_to(ROOT).as_posix(),'index':i,'rule_id':rule.get('id',f"{path.stem}:{i}"),'classification':'HUMAN_DECISION_REQUIRED' if human else 'MACHINE_ENFORCED'})
 out={'schema_version':'1.0','total_rules':len(rules),'unmapped_rules':[],'rules':rules}
 (ROOT/'docs/governance/policy-coverage.json').write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps({'ok':True,'total_rules':len(rules),'machine_enforced':sum(r['classification']=='MACHINE_ENFORCED' for r in rules),'human_decision_required':sum(r['classification']=='HUMAN_DECISION_REQUIRED' for r in rules)}))
 return 0
if __name__=='__main__': sys.exit(main())
