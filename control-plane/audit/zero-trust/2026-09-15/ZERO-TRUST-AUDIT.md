# House Net Zero-Trust Audit — 2026-09-15

## English

### Scope and authority

This evidence package is the durable audit record for the public canonical HouseNet repositories. The active machine authority is Control Plane policy **1.4.0**. The audit was verified against live GitHub APIs, repository content at the listed commits, deterministic local validators, and completed CI runs.

### Verified state

| Repository | Main commit | Visibility | CI evidence |
| :--- | :--- | :--- | :--- |
| `HouseNet-Projects/house-net-control-plane` | `860e88d5498a75f1bf5be598bcf5a1c30ee998fd` | PUBLIC | run `34997938686` GREEN |
| `HouseNet-Projects/house-net-design-system` | `7a70e4bcfbbeafa7fee8bd4d1eadc397370bfcb2` | PUBLIC | run `34996767435` GREEN |
| `HouseNet-Projects/house-net-command-center` | `3338bd65f2649e49f2fe52e50d5535b1624a7c7a` | PUBLIC | run `34997142618` GREEN |

All three `main` branches have active rulesets and classic protection: force-push and deletion blocked, linear history and conversation resolution required, squash-only merge, zero required approvals to avoid sole-owner deadlock, and required CI checks. The required checks are enforced by classic branch protection because the current ruleset API rejected the required-status-check rule shape.

### False-green defect closed

The previous checker accepted one correct marker while contradictory active claims remained. Current README bilingual status tables are generated from `release/manifest.json` and `registry/repositories.json`. The version contract validates every SemVer in each declared active region, and CI regenerates the regions then fails on `git diff`. Hero SVGs contain timeless authority language and no mutable policy version or visibility claim. Regression tests prove a conflicting active value fails the same validator used by CI.

### Governance coverage

Control Plane 1.4.0 machine-enforces canonical `house-net-*` naming, Design System adoption declarations, neutral machine authority fields, registration/classification, version authority, bilingual documents, provider-independent workflow checks, and source-policy integrity. Negative naming, design-contract, bilingual, version-drift, and protected-branch tests are present. The intentional non-compliant PR #39 was blocked and CI run `34997237407` failed with the expected missing Armenian section; it was closed without merge.

The Deputy migration remains canonical at `HouseNet-Projects/house-net-command-center`; `ohanyan88-cmd/Command-center` remains untouched legacy/reference at source SHA `d49d60bdff468b662d88d21e00458ce59646a5ca`. No knowledge or vault repository was created.

### Limits

Claude Code is not installed in this WSL, so Claude local enforcement remains pending. The GitHub ruleset endpoint does not accept required status-check rules for this account/API shape; required checks are live through classic branch protection. These are recorded platform/environment limits, not unverified claims.

## Հայերեն

### Շրջանակ և իրավասություն

Այս փաթեթը HouseNet-ի հանրային կանոնական պահոցների պահպանվող zero-trust audit գրանցումն է։ Ակտիվ մեքենայական իրավասությունը Control Plane-ի **1.4.0** քաղաքականությունն է։ Ստուգումը կատարվել է GitHub-ի կենդանի API-ներով, նշված commit-ների բովանդակությամբ, դետերմինիստական տեղային validator-ներով և ավարտված CI գործարկումներով։

### Հաստատված վիճակ

Երեք կանոնական պահոցների `main` ճյուղերն ունեն ակտիվ ruleset և classic protection․ force-push-ն ու ջնջումը արգելված են, linear history-ն ու conversation resolution-ը պարտադիր են, merge-ը միայն squash է, իսկ CI ստուգումները պարտադիր են։ Զրո review approval-ը միտումնավոր է՝ միակ սեփականատիրոջ աշխատանքը փակուղի չմտցնելու համար։ Required status check-երը աշխատում են classic branch protection-ով, քանի որ ruleset API-ի տվյալ ձևը դրանք չընդունեց։

### False-green սխալի շտկում

Նախկին checker-ը կարող էր ընդունել մեկ ճիշտ marker, երբ նույն ակտիվ մակերեսում հակասական արժեք կար։ Այժմ README-ի երկլեզու կարգավիճակի աղյուսակները գեներացվում են `release/manifest.json` և `registry/repositories.json` աղբյուրներից։ Validator-ը ստուգում է յուրաքանչյուր հայտարարված ակտիվ region-ի բոլոր SemVer արժեքները, իսկ CI-ն գեներացնում է դրանք և ձախողվում է `git diff`-ի դեպքում։ Hero SVG-ները այլևս չեն պարունակում փոփոխական policy version կամ visibility տվյալներ։ Բացասական թեստերը ապացուցում են հակասության հայտնաբերումը նույն production validator-ով։

### Սահմանափակումներ

Այս WSL-ում Claude Code տեղադրված չէ, ուստի Claude-ի տեղային enforcement-ը սպասման մեջ է։ Ruleset API-ն required status-check կանոնը չի ընդունում, սակայն classic branch protection-ը live կերպով պարտադրում է CI ստուգումները։ Այս սահմանափակումները գրանցված են որպես միջավայրային փաստեր։

### Ապացույցի ուղին

Մեքենայական evidence matrix-ը գտնվում է նույն պանակում՝ `evidence-matrix.json`։ Կանոնական աղբյուրը Control Plane-ն է, իսկ `ohanyan88-cmd/Command-center`-ը մնում է անփոփոխ legacy/reference աղբյուր։
