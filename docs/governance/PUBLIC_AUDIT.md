# Public audit surface / Հանրային աուդիտի մակերես

HouseNet's canonical source of truth is the private/publicly readable repository `HouseNet-Projects/house-net` on its `main` branch. Governance is machine-enforced by the root control contract, Control Plane validators, runtime Action Runtime gates and required CI checks.

HouseNet-ի կանոնական աղբյուրը `HouseNet-Projects/house-net` պահոցն է և նրա `main` branch-ը։ Կառավարումը մեքենայորեն enforced է արմատային control contract-ով, Control Plane validator-ներով, runtime Action Runtime gate-երով և պարտադիր CI ստուգումներով։

## Audit entrypoints / Աուդիտի մուտքեր

- Root governance: `house-net-control.json`
- Enforcement map: `docs/governance/enforcement-matrix.json`
- Documentation taxonomy: `docs/document-index.json`
- Root gate: `python tools/validate_house_net.py`
- Control Plane gate: `python control-plane/bin/validate-control-plane --json`
- LFS integrity: `git lfs fsck`
- CI: `.github/workflows/house-net-ci.yml`

## Ownership / Սեփականություն

`control-plane/` owns governance; `design-system/` owns brand and document standards; `command-center/` owns Deputy runtime and operational state; `knowledge/` owns curated durable knowledge; `vault/` owns secret references and recovery metadata.

`control-plane/`-ը կառավարման սեփականատերն է, `design-system/`-ը՝ բրենդի և փաստաթղթերի ստանդարտների, `command-center/`-ը՝ Deputy runtime-ի և օպերացիոն վիճակի, `knowledge/`-ը՝ ընտրված կայուն գիտելիքի, իսկ `vault/`-ը՝ գաղտնի հղումների և վերականգնման metadata-ի։

External writes are permitted only through the single Command Center Action Runtime with exact owner approval and independent verification. Public audit output must never contain credentials, tokens, private keys or secret-bearing URLs.

Արտաքին գրումները թույլատրվում են միայն Command Center-ի միակ Action Runtime-ով՝ Գևի ճշգրիտ հաստատմամբ և անկախ verification-ով։ Հանրային աուդիտի արդյունքը երբեք չպետք է պարունակի գաղտնաբառեր, token-ներ, private key-եր կամ գաղտնի URL-ներ։

Current provider notes: Tasks and Telegram read are certified; Outlook/Office host certification and Bitrix read configuration remain external gates; MikroBILL remains owner-deferred. These states do not change repository governance.

Ընթացիկ provider նշումներ․ Tasks և Telegram read-ը certified են, Outlook/Office host certification-ը և Bitrix read configuration-ը արտաքին gate-եր են, իսկ MikroBILL-ը մնում է owner-deferred։ Այս վիճակները չեն փոխում պահոցի governance-ը։
