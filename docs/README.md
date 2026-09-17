# HouseNet documentation index / HouseNet փաստաթղթերի ցուցիչ

This index is navigation, not a second policy authority. Machine behavior is governed by the root `house-net-control.json`, Control Plane policy, runtime guards, validators and CI.

Այս ցուցիչը նավիգացիա է, ոչ թե երկրորդ քաղաքականության աղբյուր։ Մեքենայական վարքը կառավարվում է արմատի `house-net-control.json`-ով, Control Plane-ի քաղաքականությամբ, runtime guard-երով, validator-ներով և CI-ով։

The machine-readable inventory is [`docs/document-index.json`](document-index.json). Every documentation-like artifact is classified there by category, owner, authority, currentness, purpose and machine-consumption status.

Մեքենայաընթեռնելի ամբողջական ցուցակը [`docs/document-index.json`](document-index.json)-ն է։ Յուրաքանչյուր փաստաթուղթ այնտեղ ունի դաս, սեփականատեր, հեղինակավոր լինելու նշում, ընթացիկություն, նպատակ և մեքենայական օգտագործման կարգավիճակ։

## Where to start

- Governance and enforcement: `house-net-control.json`, `control-plane/policy/`, `docs/governance/enforcement-matrix.json`, `tools/validate_house_net.py`
- Deputy runtime and operational state: `command-center/.claude/`
- Durable knowledge: `knowledge/`
- Secret references and recovery metadata: `vault/`
- Brand and document standards: `design-system/`
- Migration provenance: `docs/governance/MONOREPO_MIGRATION_MANIFEST.md`

## Enforcement

Critical rules are mapped to executable validators, runtime gates, tests and CI in `docs/governance/enforcement-matrix.json`. Run `python tools/validate_house_net.py` and the Control Plane validator before reviewing a change.

Կրիտիկական կանոնները executable validator-ների, runtime gate-երի, թեստերի և CI-ի հետ կապված են `docs/governance/enforcement-matrix.json`-ում։ Փոփոխություն վերանայելիս գործարկիր `python tools/validate_house_net.py` և Control Plane validator-ը։
