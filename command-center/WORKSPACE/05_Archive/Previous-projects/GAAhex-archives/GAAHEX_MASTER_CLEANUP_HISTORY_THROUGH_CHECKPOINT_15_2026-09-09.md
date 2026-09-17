# GAAhex Master Cleanup — From Initial Stabilization to Production Cutover

Date: 2026-09-09  
Current checkpoint: **#11**  
Purpose: durable cleanup/remediation ledger showing what was wrong, what changed, what was deliberately removed, what was later corrected, and what still requires real external/runtime certification.

> Evidence rule: this document distinguishes **CONFIRMED** facts from gaps in recovered history. It does not reconstruct missing checkpoint details by inference.

---

# EN

## 0. Starting point — why the cleanup began

The authoritative cleanup thread started as a **stabilization of the existing GAAhex system**, not a rewrite and not a replacement architecture.

Known initial problem classes recorded at the start:

- duplicate/conflicting authentication and security paths;
- import-time side effects and circular-import risk;
- inconsistent settings/configuration;
- broken or partial database initialization;
- migration/schema drift;
- mixed sync/async execution paths;
- missing or misleading tests;
- likely dead integrations and stale modules.

Operating rule from the start: inspect first, patch second; preserve working behavior; make local fixes; keep a cleanup ledger; validate after each logical batch.

## 1. Early cleanup layer / Checkpoints #1–#3

**CONFIRMED boundary:** Checkpoint #4 explicitly started from **Checkpoint #3 / Local Operator**.

**Historical limitation:** the exact item-by-item split of Checkpoints #1, #2 and #3 is not fully recoverable from the currently retrievable original-chat record. This file therefore does **not** invent that split.

The durable cleanup contract records these early/current cleanup outcomes, but this ledger does not assign them to a specific one of #1/#2/#3 unless evidence exists:

- runtime navigation made backend-registry authoritative, with a parity-checked frontend fallback;
- Left Nav reduced to real ISP operating domains instead of speculative/department-folder structure;
- Studio runtime surface reduced to backend-backed/persisted controls; local-only prototype editors removed;
- analytics/dashboard picker limited to chart types with real renderers;
- fake/sample operational data removed from user-facing Workspace/NOC/Profile/Login/header surfaces;
- LLM-backed AI changed to fail closed when no healthy provider is configured; deterministic text is not presented as an AI answer;
- authorization UI changed to fail closed when capability discovery fails;
- profile requests scoped to the submitting user and avatar changes persisted through the real API;
- temporary remediation/TODO material consolidated into durable documentation rather than acting as competing truth.

The exact checkpoint allocation inside #1–#3 remains **UNKNOWN**, not guessed.

## 2. Checkpoint #4 — real Import/Export, fake sentinels removed

**CONFIRMED:** 

- implemented real CSV/JSON/XLSX import validation and atomic generic-record ingestion;
- connected import files to the first-class Attachment/link lifecycle;
- reused the canonical record-create gate instead of a parallel import write path;
- implemented durable export jobs using the shared CSV/JSON/XLSX/PDF rendering path;
- stored generated exports through `StorageBackend` as first-class Attachments;
- corrected generated export category to canonical `AttachmentCategory=DOCUMENT`;
- removed fake Import/Warehouse implementation sentinels and deploy-shape gates;
- treated Warehouse / Inventory / Procurement as shipped capabilities rather than “pending” placeholders;
- removed/replaced obsolete 503-era import/warehouse remediation tests.

Validation at the checkpoint boundary: Python AST 659 files / 0 errors, architecture drift PASS, diff integrity PASS, stale Import/Warehouse sentinel refs 0. Full dependency-backed suites were not claimed in that sandbox.

## 3. Checkpoint #5 — staff Import UX, capability truth, notification migration truth

**CONFIRMED:**

- added staff-facing Import action to generic entity lists;
- completed real upload flow: create job → Attachment upload → link → validate → atomic start → record refresh;
- hid Import unless the user has entity-create + `import.run` + `attachment.upload` (or explicit admin configuration authority);
- capability snapshot now includes effective non-entity permission keys;
- capability discovery remains fail closed;
- notification digest schema treated as shipped contract — missing migration now fails loudly instead of recording fake `SUCCESS`;
- removed legacy “not merged yet” capability/digest test scaffolding;
- aligned SMTP comments/config with tenant-owned SMTP/MailAccount architecture;
- no active Twilio/SendGrid dependency remained in the checked runtime truth.

Validation: backend compileall PASS, TS/TSX syntax 315 files / 0 diagnostics, architecture drift PASS, diff integrity PASS.

## 4. Checkpoint #6 — payment model separated and made fail closed

**CONFIRMED:**

- established hosted/redirect local-provider checkout as the canonical ISP online-payment path;
- separated optional vaulted/direct-card charging behind its own independent feature switch;
- removed the false production requirement for Stripe when vaulted-card payments are disabled;
- applied hosted-checkout feature gating to initiation, callbacks, reconcile and scheduler automation;
- replaced production-disabled apparent-success behavior with `DisabledCheckoutGateway`;
- required callback provider key to match the active provider;
- production boot validates supported provider, merchant credentials, HTTPS callback base and explicit go-live confirmation;
- provider initiation failure/empty redirect becomes explicit `502 + FAILED`, never apparent success;
- zero-balance invoices cannot create checkout orders;
- Stripe webhook/vault-card surface is controlled by the vaulted-card feature gate, not by the local checkout switch;
- added/updated kill-switch and production-contract regression coverage.

Validation: backend compileall PASS, architecture drift PASS, diff integrity PASS. Full runtime suites were not claimed in the sandbox.

## 5. Checkpoint #7 — preserved boundary, exact delta not reconstructed

**CONFIRMED:** Checkpoint #8 names Checkpoint #7 as its direct baseline.

The exact #6→#7 delta is not recoverable from the authoritative chat material currently available to this cleanup reconstruction. It is intentionally marked **UNKNOWN** rather than reverse-inferred from Checkpoint #8.

## 6. Checkpoint #8 — production deployment hardening

**CONFIRMED:**

- payment production protocol hardened again: environment affirmation alone is insufficient; provider code must also be explicitly promoted after real merchant-contract review;
- removed demo-loop runtime/test archaeology; production bootstrap no longer seeds fake business data;
- RADIUS lifecycle tightened: activation requires backend readiness; suspend/terminate disconnect active sessions before local state transition;
- production Compose redesigned as a standalone stack, not a development overlay;
- only Caddy exposes host ports 80/443; DB, Redis, backend, frontends and ClamAV stay internal;
- admin frontend added to production Compose and served by Caddy;
- customer portal gained a production Dockerfile and is served at `/customer/`; `/portal/*` remains portal API namespace;
- one-shot `db-role` synchronizes restricted `gaahex_app` from deployment secrets;
- Alembic no longer invents/embeds the app-role password; safe NOLOGIN fallback only;
- one-shot `migrate` must exit successfully before backend startup;
- production Redis auth/persistence and ClamAV added;
- backend healthcheck changed to DB-aware `/api/health/ready`;
- backup/restore scripts aligned to separate owner/app-role credentials and RLS verification.

Local structural/YAML/shell gates passed; Docker build and real provider/hardware certification remained external.

## 7. Checkpoint #9 — release edge, API namespace, preflight and smoke

**CONFIRMED intended work:**

- canonicalized public staff API under `/api/*`; portal API remains `/portal/*`;
- set production frontend to same-origin API base;
- updated Caddy edge routing for staff API, portal API, admin SPA and customer SPA;
- added dependency-free production preflight;
- example production env correctly returns NO-GO while placeholders remain;
- preflight parses dotenv/Compose inline comments;
- added read-only HTTPS production smoke: edge, admin SPA, customer portal, health/readiness, staff login, `/api/auth/me`, capabilities and nav.

### Important later correction

Checkpoint #9 initially reported the public-route contract as PASS. During Checkpoint #10 recovery, the FULL tree proved that an automated namespace replacement had created **27 active `/api/api/*` occurrences across 17 frontend source/test files**.

This was a real regression, not missing code. Checkpoint #10:

- removed every double prefix;
- corrected the affected route expectation(s);
- strengthened `tools/check_public_route_contract.py` so `/api/api/*` is a hard failure;
- negative-tested the gate by deliberately injecting a bad double-prefix fixture, confirming FAIL, then restoring and confirming PASS.

This incident is kept here intentionally: a green gate is evidence only if the gate actually covers the failure class.

## 8. Checkpoint #10 — FULL recovery checkpoint + host certification

**CONFIRMED:**

- rebuilt Checkpoint #10 from the owner-supplied FULL #9 snapshot, not from delta-only packages;
- preserved **1718 / 1718** #9 baseline files; missing baseline files: **0**;
- repaired the `/api/api/*` regression described above;
- added `scripts/production-certify.py`, a fail-closed target-host/runtime certification orchestrator;
- added dependency-free certifier regression tests and host-certification runbook;
- certifier covers preflight, Docker/Compose, image build, stack startup, one-shot DB-role/migration success, service health, Caddy validation, authenticated HTTPS smoke, backup checksums, uploads archive integrity and scratch restore verification;
- `--skip-backup-restore` cannot produce GO;
- a `--fresh` first-bootstrap run cannot produce final GO until one-time bootstrap credentials are rotated/removed and a non-fresh certification passes.

Structural verification on the recovered FULL tree:

- production-certifier stdlib tests 3/3 PASS;
- route contract PASS;
- architecture drift PASS;
- Python compile 670 files / 0 errors;
- TS/TSX syntax 332 files / 0 parse errors;
- Python internal dangling imports 0;
- frontend relative dangling imports 0;
- Alembic 129 revisions / 1 root / 1 head / 0 missing parents;
- production Compose required paths 0 missing;
- production shell/YAML gates PASS.

Docker host runtime, full dependency-backed frontend/backend suites and live ISP/provider/hardware certification remained intentionally unclaimed in the sandbox.

## 9. Checkpoint #11 — release identity + cutover/rollback safety

**CONFIRMED implementation in this checkpoint:**

- release identity no longer depends on Git/GitLab/GitHub metadata;
- added deterministic FULL-source `RELEASE-SNAPSHOT.json` with file-by-file SHA-256 and tree SHA-256;
- production certification now refuses a missing/changed/unexpected release tree and records release identity in its JSON evidence;
- corrected a Checkpoint #10 drift-baseline regression: #10 had accidentally zeroed ratchet baselines while the source still contained the existing 33 alive guards / 6 raw buttons / 3 raw inputs / 26 clickable divs; #11 restores the truthful #9 ratchet counts so the gate again prevents increases instead of falsely failing the unchanged tree;
- added two-phase production cutover flow: `prepare` then `execute`;
- `prepare` requires the previous **FULL release ZIP**, explicitly rejecting tiny/delta archives;
- previous archive ZIP integrity/path safety/full-tree shape is validated before it can be used as rollback evidence;
- current live service health, live Alembic revision and previous-release migration head are cross-checked;
- authenticated pre-cutover smoke must pass;
- a fresh pre-cutover DB/uploads backup is checksum-verified and scratch-restored before deployment;
- cutover plan captures previous container image IDs, Compose project identity, release fingerprint and verified restore-point evidence;
- execution fails if source, previous archive, DB revision or running-container baseline drifted after `prepare`;
- target host certification is executed as the deployment gate;
- automatic application rollback is allowed only when schema/config conditions prove it safe;
- if live DB revision changed during a failed cutover, automatic DB rollback is refused. The verified pre-cutover backup is surfaced for controlled DR/forward-fix instead of silently risking data/schema corruption.

## 10. Deliberate removals — absence does not mean loss

The cleanup intentionally removed/replaced several classes of code and scaffolding:

- global Twilio/SendGrid adapter/config assumptions; email is tenant SMTP/MailAccount and SMS is a local-operator adapter;
- demo-loop/fake production business data;
- fake Import/Warehouse implementation sentinels;
- obsolete 503-era tests for capabilities that are now implemented;
- “not merged yet” test scaffolding after the shipped contract became real;
- local-only prototype/editor surfaces that were not backed by runtime persistence;
- fake deterministic “AI” answers when no LLM provider is healthy.

These are intentional cleanup outcomes, not missing checkpoint content.

## 11. Still external / not truthfully certifiable from source alone

- live payment merchant contract/callback/signature certification;
- selected local mobile-operator SMS contract/credentials;
- tenant SMTP production accounts;
- FreeRADIUS + live NAS behavior;
- OLT vendor/model/firmware command behavior;
- real AI provider/data-governance policy;
- target-host Docker/TLS/runtime result until the production certifier/cutover flow actually runs there.

---

# HY — Հայերեն ամփոփ պատմություն

## Սկիզբը

Cleanup-ը սկսվել է ոչ թե որպես rewrite, այլ գործող GAAhex-ը անվտանգ, համահունչ, bootable ու ստուգելի դարձնելու աշխատանք։ Սկզբնական հաստատված խնդիրներն էին՝ auth/security duplicate ճանապարհներ, import-time side effect/circular import, config անհամապատասխանություն, DB init/migration drift, sync/async խառնաշփոթ, misleading tests, dead/stale integrations/modules։

## #1–#3

Հաստատ գիտենք, որ #4-ի baseline-ը եղել է **#3 / Local Operator**։ #1/#2/#3-ի մանրամասն բաժանումը ամբողջությամբ չի վերականգնվում սկզբնական չատի հասանելի հատվածից, դրա համար այստեղ չենք հորինում։ Early cleanup-ի հաստատված ընդհանուր արդյունքներից են՝ backend-authoritative navigation, իրական ISP domain-ներով Left Nav, backend-backed Studio, կեղծ/sample runtime data-ի մաքրում, AI-ի fail-closed վարք, capability failure-ի fail-closed UI, իրական profile persistence/scoping, ժամանակավոր remediation docs-ի consolidation։

## #4

Import/Export-ը fake sentinel-ից դարձավ իրական համակարգ՝ CSV/JSON/XLSX validation, atomic ingestion, Attachment lifecycle, durable export jobs, CSV/JSON/XLSX/PDF renderer, first-class export Attachment-ներ։ Fake Import/Warehouse sentinel-ները և հին 503-era tests-ը հանվեցին։

## #5

Ավելացավ իրական staff Import UX և permission gate-ը։ Capability snapshot-ը սկսեց տալ նաև non-entity permission key-երը։ Notification digest migration-ի բացակայությունը այլևս fake SUCCESS չէր տալիս՝ loud failure էր։ Հին “not merged yet” scaffolding-ը հանվեց։ SMTP semantics-ը նստեց tenant SMTP/MailAccount ճարտարապետության վրա։

## #6

Payment model-ը բաժանվեց ճիշտ ձևով՝ local hosted/redirect checkout-ը canonical ISP ճանապարհ, vaulted/direct-card-ը՝ առանձին optional capability։ Production-disabled payment-ը այլևս fake success չի տալիս։ Provider/callback/merchant/HTTPS/go-live contract-ները fail-closed դարձան։ Initiation failure → `502 + FAILED`, zero-balance checkout-ը փակվեց։

## #7

#8-ը հաստատ ցույց է տալիս, որ #7-ը եղել է իր անմիջական baseline-ը, բայց #6→#7 exact delta-ն սկզբնական չատի retrieve-ից չի վերականգնվում։ Չենք գուշակում։

## #8

Production deploy-ը կարծրացավ՝ standalone Compose, միայն Caddy-ի 80/443 host exposure, ներքին DB/Redis/backend/frontends/ClamAV, restricted `gaahex_app`, mandatory migrations, Redis auth/persistence, ClamAV, DB-aware health, production customer portal, backup/restore role separation։ Demo production data-ն հանվեց, RADIUS lifecycle-ը խստացվեց։

## #9

API edge-ը canonical դարձավ `/api/*`, portal API-ն մնաց `/portal/*`, ավելացան production preflight և HTTPS smoke։ Բայց հետո պարզվեց՝ route gate-ը իրականում double-prefix failure class-ը չէր բռնում։

## #10

#9 FULL snapshot-ից վերականգնվեց ամբողջ tree-ը՝ **1718/1718 ֆայլ պահպանված, 0 կորուստ**։ Գտնվեց ու ուղղվեց **27 `/api/api/*` occurrence՝ 17 ֆայլում**, gate-ը negative-test-ով ուժեղացվեց։ Ավելացավ real host/runtime certifier՝ Docker/Compose/build/migrate/health/Caddy/smoke/backup/restore GO/NO-GO շղթայով։

## #11

Ավելացավ source-control-ից անկախ FULL snapshot identity՝ file-by-file hash + tree hash։ Production cutover-ը դարձավ երկփուլ՝ `prepare` → `execute`։ Նախորդ FULL ZIP-ը պարտադիր rollback evidence է, delta ZIP-ը մերժվում է։ Cutover-ից առաջ live smoke + իրական backup + scratch restore են պահանջվում։ Failure-ի դեպքում app rollback-ը թույլատրվում է միայն երբ schema/config-ը ապացուցված անվտանգ է։ Schema-ն արդեն փոխվել է՝ DB rollback-ը ավտոմատ չի արվում։

## Միտումնավոր ջնջվածները կորուստ չեն

Twilio/SendGrid global assumptions, demo-loop/fake business data, Import/Warehouse fake sentinels, obsolete 503/not-merged scaffolding, local-only prototype surface-ներ և fake AI answers-ը cleanup-ի ընթացքում **ճիշտ ջնջված/փոխարինված** բաներ են։

## Դեռ արտաքին validation պահանջող բաները

Live merchant/payment contract-ներ, local SMS operator, tenant SMTP, FreeRADIUS/NAS, OLT hardware/firmware, AI provider policy և իրական target-host runtime-ը source ZIP-ից «PASS» չենք հայտարարում։

## 12. Checkpoint #12 — operations continuity + backup/DR hardening

**CONFIRMED implementation:**

- kept Checkpoint #11 as a FULL baseline; no baseline source file was removed;
- corrected backup checksum sidecars from host-absolute paths to basename-relative portable records;
- changed off-site replication to verify local artifacts before transfer and removed destructive `rsync --delete` behavior;
- added cryptographic off-site evidence that binds the remote verification to the exact latest dump/uploads hashes;
- added a fail-closed backup-chain auditor for freshness, DB TOC, checksum integrity, coherent DB/uploads timestamps and off-site evidence;
- strengthened scratch restore verification so RLS cannot “pass” without proving positive visibility for a real restored tenant;
- corrected the RLS session probe to run `SET LOCAL` inside an explicit transaction and use clean numeric psql output;
- made off-site replication/evidence a default requirement of host certification and cutover preparation; skipping it is diagnostic/PARTIAL only;
- added a read-only periodic production operations audit for exact release identity, Compose/service health, Caddy validation, authenticated HTTPS smoke and backup-chain health;
- added dry-run-first systemd installer plus persistent nightly backup and 15-minute ops-audit timers;
- kept secret env files outside the release tree and required root ownership with no group/other permissions before unit installation;
- added the production operations runbook and synchronized the backup/cutover/host-certification docs with the code.

The important design change is that a successful deployment is no longer the end of the safety model. GAAHEX now has an explicit recurring evidence loop between releases: **backup → off-site copy → cryptographic evidence → restore/RLS proof → operational audit**.

### Checkpoint #12 verification boundary

Source-level/std-lib validation can prove that the gates exist and are internally consistent. It cannot truthfully claim that the real target host, SSH backup host, systemd timers, TLS edge, monitoring channel or external ISP/provider systems have passed. Those remain host/external certification gates.

---

## #12 — Production operations continuity / Հայերեն

Checkpoint #12-ում cleanup-ը deploy-ից հետո էլ շարունակական safety loop դարձավ։ #11 FULL baseline-ից ոչ մի source ֆայլ չի հանվել։ Backup checksum-ները դարձան portable basename-only, off-site rsync-ից հանվեց `--delete`-ը, local artifact-ը նախ ստուգվում է և միայն հետո արտագրվում, իսկ remote verification-ից հետո գրվում է exact hash-երով evidence։

Ավելացավ backup-chain audit՝ dump freshness/checksum/TOC, local uploads archive-ի integrity և նույն timestamp, off-site evidence match։ Restore verification-ը այլևս zero-row soft pass չի ընդունում․ restore-ից վերցնում է իրական tenant, գտնում populated tenant-scoped table և պարտադիր ապացուցում է `gaahex_app`-ի no-GUC block, own-tenant positive visibility և cross-tenant zero visibility։ `SET LOCAL` probe-ը explicit transaction-ի մեջ է։

Host certification/cutover-ը հիմա off-site recovery evidence էլ է պահանջում։ Ավելացվել է 15-րոպեանոց read-only production ops audit և dry-run-first systemd installer՝ nightly backup + periodic audit timer-ներով։ Root-only secret env-երը release tree-ից դուրս են մնում։

Այսինքն հիմա շղթան դարձել է՝ **exact FULL release → certify → cutover → backup → off-site evidence → restore/RLS proof → շարունակական ops audit**։ Իրական production-ready պիտակը դեռ կախված է target host-ի իրական execution-ից, ոչ source ZIP-ի գոյությունից։

## 13. Checkpoint #13 — FINAL SOURCE CLEANUP

**CONFIRMED implementation:**

- closed an import-time backend boot blocker in `attachments.py`: `ATTACHMENT_CATEGORIES` was used but not imported;
- repaired FastAPI route ordering so fixed reports/notifications/dashboards and `/api/org-tree` routes register before the generic `/api/{slug}` records surface;
- added an import-time route-order invariant so any future fixed `/api/*` route placed after the generic records router fails fast instead of becoming a hidden 404/422;
- fixed the startup tenant-audit warning by replacing cross-tenant owner reads in the workflow-overlap scan with per-tenant fan-out and explicit tenant filters; the finding now carries tenant identity so boot emission needs no second unscoped lookup;
- ran the tenant-filter analyzer across the FULL tree, found nine more new unscoped guarded-model queries, and fixed them forward; final result is zero new violations across 121 guarded models;
- changed canonical W1..W5 workflow rows from executable placeholder progress to DRAFT templates, added migration `gx26090903`, required ACTIVE lifecycle for execution, and made workflow-condition parsing strictly fail-closed;
- removed phantom MinIO/S3 attachment-storage configuration whose runtime modules did not exist; this release advertises local attachment storage only and preflight/backup/certification/cutover agree on that truth;
- aligned the CustomerUser model with the existing DB unique `(tenant_id,email)` invariant;
- removed a payment-receipt exception swallow and followed the canonical `payment_order_id` relation;
- removed duplicate GitHub CI definitions and kept one internally consistent source CI path with hard lint/security/import/test gates;
- retained source history truth: the earlier #9 `/api/api/*` false-PASS incident remains documented rather than rewritten away.

### User-run runtime findings folded into #13

Two final defects were surfaced while attempting a real test outside the sandbox and were treated as release blockers rather than dismissed as environment differences:

1. `attachments.py` raised `NameError` during `app.main` import because `ATTACHMENT_CATEGORIES` was missing from imports.
2. `records.router` registration order shadowed fixed API endpoints. Observed failures included notification reads, report summary, dashboard CRUD and `/api/org-tree` returning 404/422 from the generic record handlers.

Those findings directly produced permanent source gates: explicit application import and route-order invariants.

### Source verification boundary

Checkpoint #13 passes every dependency-free/static/structural gate executable in this environment: 33/33 new regression tests, route/drift/tenant-filter gates, Python/TypeScript syntax, internal/relative import integrity, Alembic graph and production shell/YAML checks. Full dependency-backed backend/frontend/runtime certification remains the next target-host step and is not retroactively claimed from source inspection.

---

## #13 — FINAL SOURCE CLEANUP / Հայերեն

#13-ը source-side cleanup-ի վերջնական checkpoint-ն է։ Քո իրական test-ի ժամանակ բռնած երկու blocker-ը մտել են հենց source contract-ի մեջ՝ `ATTACHMENT_CATEGORIES` missing import-ը այլևս backend import-ը չի ջարդում, իսկ generic `records.router`-ը հիմա վերջին `/api` router-ն է։ Reports/notifications/dashboards և `/api/org-tree` fixed route-երը դրանից առաջ են, և boot-time invariant-ը նորից սխալ հերթ դնելու դեպքում import-ի պահին կկանգնեցնի app-ը։

Startup tenant-audit warning-ը bypass-ով չենք թաքցրել։ Workflow overlap scan-ը հիմա tenant-ները հերթով է անցնում ու `WorkflowDef`/`EntityDef` query-ները explicit `tenant_id` filter-ով է անում։ Դրան գումարած full tenant analyzer-ը գտավ ևս 9 query, որոնք նույնպես tenant-bound դարձան։ Վերջնական analyzer արդյունքը՝ 0 նոր violation / 121 guarded model։

Workflow W1..W5 placeholder-ները այլևս executable fake progress չեն՝ DRAFT են, existing DB-ների համար կա `gx26090903` migration, engine-ը միայն ACTIVE definition է աշխատեցնում, malformed condition-ը fail-closed է։ Phantom MinIO/S3 attachment provider-ները հանվել են, որովհետև implementation չկար. այս release-ը attachment storage-ի համար ազնիվ local-only contract ունի բոլոր preflight/backup/certification/cutover շերտերում։

Այս checkpoint-ից հետո source cleanup-ը փակ ենք համարում։ Հաջորդ աշխատանքը source-ի հերթական «փուլը» չէ՝ իրական dependency-backed backend/frontend + target Linux host certification/cutover-ն է։ Եթե runtime-ը կոնկրետ bug հանի, ուղղում ենք այդ bug-ը, ոչ նոր անվերջ cleanup wave ենք բացում։


## 14. Checkpoint #14 — dependency-backed test remediation

A real external test run against Checkpoint #13 surfaced the next layer that static/source certification could not prove: **25 backend failures, 1878 backend passes, 2 backend errors and 3 frontend typecheck errors**. Checkpoint #14 treats those results as authoritative runtime evidence and fixes the causes rather than weakening release gates.

**CONFIRMED remediation:**

- replaced timestamp-prefix-truncated UUIDv7 mock payment IDs with collision-resistant random 8-hex suffixes and added rapid-call uniqueness coverage;
- made mock card expiry deterministic from a documented token suffix so the expired-method Stage-8 branch is actually testable;
- excluded named transition-guard registry keys from GXL expression parsing;
- isolated the global Settings singleton between tests and made production contract helpers disable unrelated payment features by default;
- unified OLT required-state evaluation behind `feature_gate.is_required()` and changed stale dev-fallback expectations to fail-closed behavior;
- kept production SMTP/SMS fail-closed while giving happy-path tests explicit in-process transports;
- restored providerless AI chat only as deterministic local answer-only behavior; LLM-dependent surfaces remain unavailable without a provider;
- added the missing `ticket.customer` EntityDef reference plus migration `gx26090904` for existing databases;
- split ownership boot diagnostics into expected first-class typed records vs genuine registry gaps instead of hiding or conflating them;
- made FreeRADIUS and oversized-logo tests portable on Windows without misclassifying OS limitations as product failures;
- aligned frontend TypeScript libs with ES2022 APIs and aligned the channel account input type with the backend `config` JSON field;
- documented/provisioned the local-only `gaahex_app` LOGIN role while preserving production's secret-driven NOLOGIN migration posture;
- changed `gate:lint-changed` from a vacuous non-Git PASS into an explicit non-zero UNVERIFIED result;
- added a dedicated #14 dependency-free source-contract suite and wired it into the active source CI definition.

The concrete E2E entity failure is fixed; Checkpoint #14 intentionally does not manufacture fake EntityDefs for features that still lack real implementations. Those remain visible as genuine registry warnings until their owning surfaces exist.

The sandbox still cannot rerun the full dependency-backed suites because Python application dependencies and frontend `node_modules` cannot be installed here. That boundary remains explicit: the next complete-environment rerun is the authority for proving that the external failure count reaches zero.

---

## #14 — TEST REMEDIATION / Հայերեն

#13-ի իրական full test-ը բացեց այն խնդիրները, որոնք static gate-երով չէին երևում՝ backend-ում 25 fail / 1878 pass / 2 error և frontend typecheck-ում 3 error։ #14-ը հենց այդ runtime evidence-ից է աշխատում։

Mock payment ID collision-ը հանվել է random 8-hex suffix-ով, card expiry test metadata-ն հիմա իրականում անցնում է mock gateway-ին, named guard-ը GXL expression չի համարվում, global settings-ը test-երի միջև restore է արվում։ OLT-ի required policy-ն ունի մեկ authority և required+unmapped վիճակը այլևս dev fallback չի անում։ Messaging happy-path test-երը explicit test SMTP/SMS transport են ստանում՝ production fail-closed վարքը չթուլացնելով։

AI chat-ը provider չունենալիս միայն deterministic answer-only local mode ունի, իսկ LLM-dependent endpoint-ները շարունակում են 503։ Ticket EntityDef-ին ավելացվել է `customer` ref և existing DB-ի համար `gx26090904` migration։ Ownership startup log-ը expected first-class record-ները INFO է առանձնացնում իսկ իրական registry gap-ը WARNING է պահում՝ fake entity չսարքելով։

Windows-ի `select.poll`/huge pytest-id խնդիրները portable են դարձել, frontend-ը ES2022 lib contract ունի և channel input-ի `config` field-ը backend-ի հետ համընկնում է։ Local RLS test role-ի setup-ը փաստաթղթավորված/սքրիփթավորված է, իսկ non-Git `gate:lint-changed`-ը այլևս կեղծ կանաչ չի տալիս՝ UNVERIFIED exit 2 է։

Այս միջավայրում full pytest/npm rerun չենք հորինում, որովհետև անհրաժեշտ Python package-ները և `node_modules`-ը չկան ու network install-ը փակ է։ Դրա համար հաջորդ իրական complete-environment rerun-ն է dependency-backed վերջնական ապացույցը։

## 15. Checkpoint #15 — canonical zero-fail gate hardening

Checkpoint #14 fixed the concrete failures reported by the complete external test run. Checkpoint #15 changes the **proof model** so the project cannot again confuse “could not execute here” with “passed”.

**CONFIRMED implementation:**

- added `tools/zero_fail_gate.py` as the single complete-test entry point with explicit `PASS (0) / FAIL (1) / BLOCKED (2)` semantics;
- made the full gate execute backend boot/import, full backend pytest, migration invariants, staff frontend typecheck/tests/build and customer-portal tests/build;
- kept dependency-free source verification available as `--source-only`, clearly non-equivalent to the full proof;
- added `tools/test_checkpoint15_zero_fail.py` so the zero-fail harness itself is regression-tested;
- pinned both frontend package contracts to Node 24 (`>=24 <25`) and enabled npm `engine-strict`, eliminating Node-version ambiguity;
- documented FULL-checkpoint frontend installation with `npm ci --ignore-scripts`, because release ZIPs intentionally have no Git worktree and must not fail only on the Husky prepare hook;
- added the dedicated zero-fail runbook and aligned README/current CI source contracts;
- preserved every Checkpoint #14 release file.

In the constrained review sandbox, `--source-only` is green while full mode is explicitly **BLOCKED**, because the exact Python/Node/dependency/DB environment is unavailable. That is intentional: BLOCKED is no longer a false green.

Once a complete environment returns `ZERO-FAIL PASS`, cleanup/testing is considered closed and the next program becomes the page-by-page product audit already agreed with the owner.

---

## #15 — ZERO-FAIL GATE / Հայերեն

#14-ը ուղղեց իրական full-test report-ի կոնկրետ bug-երը։ #15-ում փոխեցինք արդեն verification-ի մեխանիզմը, որ «էս միջավայրում չկարողացա վազացնել» վիճակը երբեք չդառնա PASS։

Ավելացել է մեկ canonical command՝ `python tools/zero_fail_gate.py`։ `0` նշանակում է ամբողջ requested suite-ը իրականում անցել է, `1`՝ իրական gate failure կա, `2`՝ environment-ը չի կարող proof-ը կատարել և release-ը BLOCKED է։ Full mode-ը ներառում է backend boot/import + ամբողջ pytest + migration invariants + staff frontend typecheck/test/build + customer portal test/build։

Երկու frontend-ներն էլ հիմա Node 24 hard contract ունեն, npm engine-strict է, իսկ FULL ZIP-ի install-ը documented է `npm ci --ignore-scripts` ձևով, որ Git metadata չունենալը product failure չդառնա։

Այս sandbox-ում dependency-free source gate-ը ZERO-FAIL PASS է, իսկ full gate-ը ազնիվ BLOCKED է՝ Python 3.12/Node 24/dependencies/Postgres environment չլինելու պատճառով։ Լիարժեք test machine-ում միայն exit 0-ն է փակելու testing phase-ը։ Դրանից հետո գնում ենք էջ առ էջ՝ էջի նպատակը → պետք է ինչ անի → իրականում ինչ է անում → ինչն է սխալ → fix → retest։
