# HouseNet documentation index / HouseNet փաստաթղթերի ցուցիչ

This index is navigation, not a second policy authority. Machine behavior is governed by the root `house-net-control.json`, Control Plane policy, runtime guards, validators and CI.

Այս ցուցիչը նավիգացիա է, ոչ թե երկրորդ քաղաքականության աղբյուր։ Մեքենայական վարքը կառավարվում է արմատի `house-net-control.json`-ով, Control Plane-ի քաղաքականությամբ, runtime guard-երով, validator-ներով և CI-ով։

The machine-readable inventory is [`docs/document-index.json`](document-index.json). Every documentation-like artifact is classified there by category, owner, authority, currentness, purpose and machine-consumption status.

Մեքենայաընթեռնելի ամբողջական ցուցակը [`docs/document-index.json`](document-index.json)-ն է։ Յուրաքանչյուր փաստաթուղթ այնտեղ ունի դաս, սեփականատեր, հեղինակավոր լինելու նշում, ընթացիկություն, նպատակ և մեքենայական օգտագործման կարգավիճակ։

## Where to start

- Governance and enforcement: `house-net-control.json`, `control-plane/policy/`, `docs/governance/enforcement-matrix.json`, `docs/governance/engineering-authority.schema.json`, `tools/validate_house_net.py`
- Deputy runtime and operational state: `command-center/.claude/`
- Durable knowledge: `knowledge/`
- Secret references and recovery metadata: `vault/`
- Brand and document standards: `design-system/`
- Migration provenance: `docs/governance/MONOREPO_MIGRATION_MANIFEST.md`

## Enforcement

Critical rules are mapped to executable validators, runtime gates, tests and CI in `docs/governance/enforcement-matrix.json`; complete Control Plane rule coverage is generated in `docs/governance/policy-coverage.json`. Engineering work is bounded by `EngineeringAuthorityEnvelope`; credentials are scanned by `tools/secret_scan.py`. Run `python tools/validate_house_net.py`, `python tools/policy_coverage.py`, `python tools/secret_scan.py` and the Control Plane validator before reviewing a change.

Կրիտիկական կանոնները executable validator-ների, runtime gate-երի, թեստերի և CI-ի հետ կապված են `docs/governance/enforcement-matrix.json`-ում, իսկ Control Plane-ի բոլոր կանոնների ծածկույթը գեներացվում է `docs/governance/policy-coverage.json`-ում։ Engineering աշխատանքը սահմանափակվում է `EngineeringAuthorityEnvelope`-ով, իսկ credentials-ը ստուգվում է `tools/secret_scan.py`-ով։ Վերանայելիս գործարկիր `python tools/validate_house_net.py`, `python tools/policy_coverage.py`, `python tools/secret_scan.py` և Control Plane validator-ը։
