# Installation verification

## English

This file records observed evidence, not policy authority. Final live verification is completed after the initial executable baseline is published.

- Source SHA-256 verified: `a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491`.
- Namespace and account: `HouseNet-Projects`.
- Policy snapshot: `72bb4b4bded5ffda7bf6f99a4a7f4fbccb07a871`.
- Policy version: `1.0.0`; source coverage: all 30 numbered sections; 43 unique rules.
- Claude Code absent in this WSL; managed hooks pending.
- Codex bootstrap installed at `/home/gevorg/.codex/AGENTS.md` and supported `developer_instructions` in `/home/gevorg/.codex/config.toml`; the installer was run twice and the second run was idempotent. `codex debug prompt-input` in a fresh process showed the managed bootstrap, control-plane path, identity requirement, owner-approval rule and manifest lookup. A separate `codex exec` probe reached the manifest read and reported policy version `1.0.0`, then stopped when the Codex service usage limit was reached; no mutation occurred.
- Claude Code is absent from this WSL; local managed Claude hooks are pending and were not installed.
- Repository settings verified: private, `main`, squash-only merges, auto-merge off, merged-branch deletion on; Actions selected policy with `actions/*` and `HouseNet-Projects/*`, full-SHA pinning required, read-only default token, PR creation/approval disabled, same-owner private workflow access, and 30-day artifact/log retention.
- Dependabot alerts/security updates are enabled. The first control-plane CI run for commit `4dc9575acd3af9ff0b17f109fe08518c980d7f3e` passed; subsequent CI checks also passed.
- GitHub rejected private personal-account branch protection with: `Upgrade to GitHub Pro or make this repository public`. This is the documented private-plan server-side protection gap; no fake protection was configured.

---

## Հայերեն

# Տեղադրման ստուգում

Այս գրառումը փաստում է դիտարկված ապացույցը, ոչ թե policy authority-ն։ Սկզբնական source SHA-256-ը պահպանվում է՝ `a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491`։ Identity-ն և namespace-ը `HouseNet-Projects` են։ Codex bootstrap-ը տեղադրված է `/home/gevorg/.codex/AGENTS.md`-ում։ Claude Code-ը այս WSL-ում բացակայում է, ուստի managed hook-երը սպասման մեջ են։

GitHub-ը ընթացիկ personal private plan-ով մերժել է branch protection-ը՝ պահանջելով Pro կամ public repository։ Սա server-side gap է, և կեղծ protection չի ստեղծվել։

---

## Phase 1 certification · English

Certified against current `main` commit `0863d219f2f16cac2f6733e1b98a9fd554b28803` on 2026-09-15. Identity was `HouseNet-Projects`; origin was canonical; the checkout was clean; preflight passed with policy `1.1.0`, 44 unique rules, 30 source sections and one registered Class A repository. The latest main CI run `34970954420` passed, 48 tests passed, syntax checks passed, and policy validation passed.

Enforcement truth: policy/schema/source coverage, registry, snapshot consistency, bilingual document markers, negative fixtures, action pinning, workflow restrictions, and self-CI are CI enforced. Identity, canonical remote, Git baseline and remote freshness are local enforced by preflight. Codex bootstrap is agent guidance confirmed by `codex debug prompt-input`; the fresh `codex exec` probe could not initialize in this read-only runtime. Claude local enforcement is pending because Claude Code is not installed in this WSL. GitHub main branch protection is plan-limited for private personal repositories. No broken control-plane gate remains.

Fail-closed coverage includes wrong identity, missing registration, invalid classification, stale policy references, malformed JSON, duplicate rule IDs, missing English/Armenian sections, empty bilingual sections, forbidden workflow patterns and invalid registration metadata. Valid fixtures pass. The original approved source checksum remains `a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491`.

## Phase 1 certification · Հայերեն

2026-09-15-ին ստուգվել է ընթացիկ `main` commit `0863d219f2f16cac2f6733e1b98a9fd554b28803`-ի վրա։ Identity-ն `HouseNet-Projects` էր, origin-ը՝ կանոնական, checkout-ը՝ մաքուր, իսկ preflight-ը անցավ՝ policy `1.1.0`, 44 եզակի կանոն, 30 աղբյուրային բաժին և մեկ գրանցված Class A պահոց։ Main-ի վերջին CI run `34970954420`-ը green է, 48 թեստ անցել է, syntax checks-ը և policy validation-ը նույնպես անցել են։

Enforcement-ի ճշմարտություն՝ policy/schema/source coverage-ը, registry-ն, snapshot consistency-ն, երկլեզու marker-ները, negative fixtures-ը, action pinning-ը, workflow սահմանափակումները և self-CI-ն CI-ով enforced են։ Identity-ը, կանոնական remote-ը, Git baseline-ը և remote freshness-ը local preflight-ով enforced են։ Codex bootstrap-ը agent guidance է, հաստատված `codex debug prompt-input`-ով, իսկ fresh `codex exec` փորձը այս read-only runtime-ում չմեկնարկեց։ Claude-ի տեղային enforcement-ը սպասման մեջ է, քանի որ Claude Code-ը այս WSL-ում տեղադրված չէ։ GitHub main branch protection-ը plan-limited է private personal repository-ի համար։ Control-plane-ի կոտրված gate չի մնացել։

Fail-closed ստուգումները ներառում են սխալ identity, բացակայող registration, սխալ դաս, stale policy reference, սխալ JSON, duplicate rule ID, բացակայող English/Armenian բաժիններ, դատարկ bilingual section, արգելված workflow pattern և սխալ registration metadata։ Valid fixture-ները անցնում են։ Սկզբնական հաստատված source checksum-ը պահպանվում է՝ `a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491`։

## Post-remediation certification

### English

After the initial certification record, three reachable-reference defects were found during the authorized future-repository gate test and remediated without weakening policy: PR #11 updated the reusable validator pin, PR #12 aligned the distribution snapshot and registrations, and PR #13 updated the reusable gate to that aligned snapshot. Final main commit `2608841f350924befdaeb19a7756879f60a40f08` passed CI run `34974318624`; the design-system gate then passed against the registered Class B repository.

### Հայերեն

Սկզբնական certification record-ից հետո ապագա repository gate-ի ստուգման ժամանակ հայտնաբերվեցին reachable reference-ի երեք defect և ուղղվեցին՝ առանց policy-ն թուլացնելու։ PR #11-ը թարմացրեց reusable validator pin-ը, PR #12-ը համաժամացրեց distribution snapshot-ը և registrations-ը, իսկ PR #13-ը reusable gate-ը pin արեց այդ snapshot-ին։ Վերջնական main commit `2608841f350924befdaeb19a7756879f60a40f08`-ը անցավ CI run `34974318624`-ով, իսկ design-system gate-ը անցավ գրանցված Class B repository-ի վրա։
