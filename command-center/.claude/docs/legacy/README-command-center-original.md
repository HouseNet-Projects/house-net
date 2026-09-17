# Command-center

**Command-center is Gev's operational workspace for Sales & Operations, managed with Deputy — AI Chief of Staff for Sales & Operations.**
HouseNet ՍՊԸ · ամեն աշխատանքային օրը սկսվում է այստեղից։

Ի՞նչ է սա մեկ նախադասությամբ՝ մեկ հսկվող միջավայր ընթացիկ գործի, գործող բիզնես-հենքի, առաջադրանքների, անելիքների, օրագրի, հում աղբյուրների, ավարտվածի, արխիվի և Deputy-ի runtime-ի (skills, governance, tests, state, audit) համար։

> Այս ֆայլը մարդու ուղեցույցն է։ **Մեքենայական հեղինակությունը** `.claude/policy/workspace_policy.json`-ն է (կառուցվածք, անվանում, identity)։ Եթե երկուսը հակասեն՝ policy-ն է ճիշտ, և `validate_workspace.py`-ը ձախողվում է մինչև README-ն ուղղվի։

---

## Արմատում (ընդամենը 5 ֆայլ)

| Ֆայլ | Ինչի համար |
|:---|:---|
| **[WORKSPACE/](WORKSPACE/)** | 🏠 **ԳԵՎ-Ի ԱՇԽԱՏԱՆՔԱՅԻՆ ՊԱՆԱԿԸ** — ամեն օր բացվում է միայն սա։ Ներսում՝ վեց տիրույթ և երեք կենդանի ռեեստր։ Ոչ մի տեխնիկական ֆայլ այստեղ չի հայտնվում։ |
| **[Tasks.xlsx](WORKSPACE/Tasks.xlsx)** | 🎯 Միակ կենդանի առաջադրանքների ռեեստրը։ Գև-ը կարգավիճակ փոխում է ուղիղ այստեղ. Deputy-ն կարդում է այն ամեն սեսիա։ |
| **[Journal.md](WORKSPACE/Journal.md)** | Ինչ արվեց ամեն օր։ Նոր օրը՝ վերևում։ Ամեն տեղափոխում/վերանվանում գրանցվում է այստեղ։ |
| **[Actions.md](WORKSPACE/Actions.md)** | Ներքին անելիքներ՝ փաստաթղթերի և համակարգի վրա։ |
| **[CLAUDE.md](CLAUDE.md)** | Deputy-ի վարքի կանոնագիրը (ուղեցույց, ոչ հարկադրանք)։ |
| **README.md** | Այս ֆայլը։ |

## Պանակներ (fixed contract)

| Պանակ | Պատասխանատվություն |
|:---|:---|
| **[00_Inbox/](WORKSPACE/00_Inbox/)** | 📥 Մուտքի սեղան։ Ամեն ինչ, ինչ չգիտես ուր դնել՝ գցի այստեղ. Deputy-ն դասավորում է։ Կայուն վիճակ՝ դատարկ, բացի [Input.md](WORKSPACE/00_Inbox/Input.md)-ից (հում տեքստի տեղը)։ |
| **[01_Active/](WORKSPACE/01_Active/)** | Ընթացիկ գործ՝ `Sales/` · `Operations/` · `People/` · `Systems/`։ Միայն այն, ինչ հիմա մշակվում, ստուգվում կամ կատարվում է։ |
| **[02_Reference/](WORKSPACE/02_Reference/)** | Հաստատված, **դեռ գործող** ճշմարտություն (օր.՝ Staffing-plan)։ Նույն 4 ենթապանակները։ |
| **[03_Completed/](WORKSPACE/03_Completed/)** | Ավարտված deliverable-ներ, որոնք այլևս ընթացիկ ճշմարտություն չեն։ |
| **[04_Sources/](WORKSPACE/04_Sources/)** | Հում ապացույց՝ `Whatsapp/` (export-ներ), `Screenshots/`, `Imports/`։ Ոչ մի կոդ, ոչ մի մշակված deliverable։ |
| **[05_Archive/](WORKSPACE/05_Archive/)** | Հնացած տարբերակներ, սևագրեր, հին implementation։ Պատմություն է, ոչ ճշմարտություն։ Ոչինչ չի ջնջվում։ |
| **`.claude/`** | Deputy runtime՝ `hooks/` (brief, skill gate, workspace guard) · `docs/` (Role, Job-description, audits) · `policy/` (contract + validator) · `skills/` (Skill System) · `tools/` (helper programs) · `tests/` · `state/` · `audit/`։ |

## Անվանման ստանդարտ

Բիզնես ֆայլերն ու պանակները՝ անգլերեն, `First-word-hyphenated[-vN.N][-YYYY-MM-DD].ext`։
Օրինակներ՝ `Billing-roadmap-v2-2026-09-07.docx` · `Staffing-plan-2026-09-07.xlsx` · `Sales-strategy-2026-09-09.docx` · `Open-questions.md`։
Առանց բացատի, փակագծի, «(2)», «final/new/copy/fixed»; ամսաթիվը միայն `YYYY-MM-DD`, տարբերակը միայն `vN`/`vN.N`, տարբերակը ամսաթվից առաջ, ընդլայնումը փոքրատառ։
Տեխնիկական բացառություններ (policy-ում)՝ `.claude`, `CLAUDE.md`, `README.md`, `settings.json`, Python `snake_case.py`, runtime-ի գեներացված ֆայլեր։

## Ինչպես ենք աշխատում

- **Ամեն ինչ, ինչ ձեռքդ ընկնում է** → գցի `00_Inbox/`։ Deputy-ն տանում է ճիշտ տեղը, վերանվանում, գրանցում Journal-ում։
- **Դու** աշխատում ես `Tasks.xlsx`-ում՝ փոխում ես կարգավիճակներ, գրում մեկնաբանություններ։
- **Սկրիպտ, .bat, ոչ մի բան չես գործարկում** — վերակառուցում պետք լինի, ասում ես Deputy-ին։
- **Deputy-ն** ամեն սեսիա բացելիս տալիս է Deputy Daily Brief-ը՝ workspace-ի վիճակ, մուտք, ժամկետանց/այսօր, սպասումներ, խոստումներ։ Դերը՝ [.claude/docs/Role.md](.claude/docs/Role.md)։

## Հարկադրանք (մեխանիկական, ոչ միայն տեքստ)

| Շերտ | Ինչ է անում |
|:---|:---|
| SessionStart | `hooks/brief.py`՝ workspace validation + Deputy Daily Brief (Skill Engine-ով, աուդիտված) |
| Ամեն հաղորդագրություն | `hooks/gate.py`՝ intent → skill resolution → gate ticket |
| Գրող գործիքից առաջ | `hooks/gate.py` (skill gate) + `hooks/workspace_guard.py` (ուղի/անուն policy-ով) → deny |
| Գրող գործիքից հետո | `workspace_guard.py`՝ ամբողջ ծառի validation, խախտումը՝ բարձրաձայն |
| Release/certify | `skill.py release` = workspace validation → build → certify (բոլոր suite-երը, ներառյալ `test_workspace`) → validate → eval |

Հրամաններ՝ `python .claude/policy/validate_workspace.py` · `python .claude/skills/skill.py release` · `python .claude/skills/skill.py status`։

## Դիմացկունություն — GitHub + մեկ վերականգնման բանալի = ամբողջական Command-center

**Օրենք.** Կարևոր լոկալ-միայն ճշմարտություն չկա։ Այն, ինչ վաղը պետք է Deputy-ին կամ Գև-ին, կա՛մ (1) ուղիղ versioned է Git-ում, կա՛մ (2) versioned է որպես գաղտնագրված վերականգնման artifact, կա՛մ (3) դետերմինիստիկ վերակառուցվում է versioned բովանդակությունից։ Միայն ephemeral կամ մեքենային կապված տվյալն է լոկալ։

Նոր համակարգիչ →
```
git clone https://github.com/ohanyan88-cmd/Command-center.git
cd Command-center
python bootstrap.py            # կամ py -3 bootstrap.py — idempotent, ոչինչ չի ջնջում/չի վերագրում
```
`bootstrap.py`՝ արմատ · նախապայմաններ (Python ≥3.11, git, gpg) · կանոնական պանակներ · `.venv` + pinned կախվածություններ · գաղտնագրված credential-ների վերականգնում (եթե բանալին կա) · Deputy-ի դիմացկուն state-ի import · boundary hooks · Business Model rebuild (sources → extract → build → validate → certify) · workspace + tree-manifest validation · checksums · business/integration certification · skill validation (`--release`՝ ամբողջական release) · վերջնական READY/NOT READY։

| Ինչ | Որտեղ | Ինչպես է վերականգնվում |
|:---|:---|:---|
| `CLAUDE.md · README.md · Tasks.xlsx · Journal.md · Actions.md · bootstrap.py`, `00_Inbox…05_Archive` (բոլոր բիզնես փաստաթղթերը, աղբյուրները, արխիվները) | Git (VERSION_DIRECTLY) | clone. դատարկ պանակները՝ `.gitkeep`-ով |
| Business Operating Model՝ core `bm_*.py` **և** overlay `overlay/ov_*.py` | Git (VERSION_DIRECTLY, Գև-ի որոշմամբ) | clone → `build_business_model.py` (generated json/md՝ REGENERATE) |
| Deputy-ի դիմացկուն հիշողություն՝ commitments, decisions, audit, actions, observations | Git՝ `.claude/state/durable/*.jsonl` (`state_snapshot.py export`՝ `skill.py sync`-ում և release-ում ավտոմատ) | bootstrap → `state_snapshot.py import` (idempotent, op_id-ով, կրկնություն չկա) |
| Արտաքին համակարգերի credential-ներ (`~/.command-center/integrations/*.json`) | Git՝ `.secure/credentials.gpg` (GnuPG AES-256) + `.secure/manifest.json` (անուններ/checksum, ոչ արժեք) | bootstrap → `secure_recovery.py restore`, **միայն** վերականգնման բանալով |
| Runtime (`.venv`), generated model/certification | REGENERATE | bootstrap |
| SQLite store, journal, locks, integration cache/health, audit mirror, `settings.local.json`, `desktop.ini` | EPHEMERAL / MACHINE_LOCAL | չի versioned, վերստեղծվում է |

**Մեկ արտաքին գաղտնիք՝ վերականգնման բանալին** `~/.command-center/recovery.key` (կամ `COMMAND_CENTER_RECOVERY_KEY_FILE`)։ Երբեք Git-ում, log-ում, audit-ում, տերմինալում։ Գև՝ պահիր պատճենը password manager-ում կամ արտաքին սարքի վրա (ֆայլի բովանդակությունը՝ մեկ տող)։ Առանց բանալու՝ ամեն ինչ վերականգնվում է, բացի արտաքին credential-ներից (ինտեգրումները մնում են NOT_CONFIGURED և դա ասվում է բարձրաձայն)։

**Երկու ուղի, մեխանիկապես տարանջատված (policy `durability.live_data`, 1.7.0).**

| Ինչ փոխվեց | Դաս | Ուղի |
|:---|:---|:---|
| `Tasks.xlsx` տող (create/assign/due/status/close/reopen/note), `Journal.md`, `00_Inbox/Input.md`, բիզնես փաստաթուղթ, որը մոդելի extraction աղբյուր չէ, `.claude/state/durable/*`, `durable_checksums.json` | LIVE DATA / DOCUMENT / DURABLE_STATE / INTEGRITY_META | **`skill.py sync`** — classify → durable state export → ստատիկ մոդելը դեռ վկայագրվա՞ծ է (առանց rebuild) → checksums refresh → commit միայն այդ ուղիները → push → origin ստուգում |
| Կոդ, policy, hooks, skills, tests, `bm_*.py`/overlay, extraction աղբյուր (S01…S16 բացի S09-ից), ռեեստրի **կառուցվածք** (sheet/header) | PRODUCT / MODEL_SOURCE / RELEASE_ARTIFACT | **`skill.py release`** (rebuild → certify → validate → eval → checksums) |
| Անհայտ ուղի | UNKNOWN | fail closed — ոչինչ չի sync-վում |

`Tasks.xlsx`-ը **LIVE OPERATIONAL SOURCE** է (S09 · `source_kind: LIVE_REGISTER` · `fingerprint_scope: STRUCTURE`)՝ մոդելը կապված է միայն նրա կառուցվածքին (թերթ + header բլոկ), տողերը կարդացվում են live՝ INT-TASKS-ով (retrieved_at/freshness ամեն ընթերցման)։ Տողի փոփոխությունը core fingerprint-ը չի փոխում, STALE_MODEL չի առաջացնում, rebuild/certification/release չի պահանջում։ Drift-ը ամեն սեսիա երևում է Daily Brief-ում (`🔄 GitHub sync ✓` կամ `ՉԻ ՀԱՄԱԺԱՄԱՆԱԿԵՑՎԱԾ — SYNC_REQUIRED/RELEASE_REQUIRED/UNCLASSIFIED`), `tree_manifest.py drift`-ով՝ ձեռքով։

Կանոնական ծառի պայմանագիր՝ `.claude/policy/workspace_tree_manifest.json` (գեներացվում է policy-ից `tree_manifest.py build --write`-ով, validator-ը ստուգում է համապատասխանությունը և ֆիզիկական գոյությունը), checksum-ներ՝ `.claude/policy/durable_checksums.json`։ Parity՝ `tree_manifest.py snapshot` աղբյուրում և վերականգնվածում → `tree_manifest.py parity a b`։ Scanner-ի սեմանտիկա (2.0)՝ **արգելում է միայն RESTRICTED** (credential, token, գաղտնաբառ, private key, բանալի, connection string); բիզնես տեղեկատվությունը (անուններ, աշխատավարձ, փաստաթղթեր) CONFIDENTIAL awareness է՝ versioned Գև-ի որոշմամբ։ `.secure/`՝ գաղտնագրված artifact-ի պանակն է։ Ժամանակավոր staging-ի պանակ այլևս չկա՝ 2026-09-14-ին ամբողջ նյութը դասակարգվեց տաքսոնոմիայում ([migration manifest](WORKSPACE/05_Archive/Migration-2026-09-14/Migration-manifest-2026-09-14.md))։

Business Operating Model՝ `.claude/business/`, երկու շերտ. **CORE** (INTERNAL, versioned)՝ `bm_*.py` authoring, `bm_schema.py`, `bm_targets.py`, `build_business_model.py`, `certify_business.py` — դերեր առանց վարձատրության, գործընթացներ, ownership ըստ ԴԵՐԻ, KPI-ներ, վերահսկվող targets/thresholds, playbooks, routines, gaps, աղբյուրների metadata, մարդիկ միայն `@P` token-ներով; **SENSITIVE OVERLAY** (CONFIDENTIAL, միայն լոկալ)՝ `overlay/ov_*.py` → `overlay.json` (անուն ↔ token, դեր ↔ մարդ, աշխատավարձ, առևտրային թվեր, ապացույցներ)։ Գեներացված `*.json`/`Business-model.md`/`certification.json`՝ լոկալ։ Pipeline՝ sources → extract → validate → core → overlay → fingerprint → certify (schema 2.0, model_version, source snapshot; STALE_MODEL/SOURCE_MISSING հայտնաբերում)։ Սահմանը մեխանիկական է՝ `.claude/policy/data_classification.json` (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) + `sensitive_scan.py` (pre-commit/pre-push hooks, validator, certification)։ Engine-ը ամեն governed գործարկման մեջ ներարկում է business context (playbook, KPI, process, owner ROLE → CURRENT PERSON միայն CONFIRMED assignment-ով, sources, model identity, gap codes՝ OWNER_UNKNOWN · KPI_DEFINITION_MISSING · PROCESS_UNDEFINED · TARGET_UNKNOWN · APPROVAL_RULE_UNKNOWN · SOURCE_CONFLICT · STALE_MODEL · SOURCE_CHANGED · SOURCE_MISSING · BUSINESS_CONTEXT_MISSING)։ Չատից եկած գիտելիքը միայն OBSERVATION է (state store), core-ը չի փոխում. promotion՝ OBSERVATION → PROPOSED → CONFIRMED → APPROVED → SUPERSEDED։ Private Git-ը secrets database չէ. սահմանը գործում է անկախ repo-ի visibility-ից։

## Live աղբյուրներ — ինտեգրման շերտ (ՄԻԱՅՆ ԿԱՐԴԱԼ)

`.claude/integrations/` — Deputy-ի «աչքերը»։ Ամեն արտաքին համակարգ **անվստահելի աղբյուր է, մինչև վկայագրվի**. CONNECTION AVAILABLE ≠ DATA TRUSTED ≠ BUSINESS FACT CONFIRMED։ Ճանապարհը միշտ նույնն է՝ BUSINESS SKILL → BUSINESS QUERY → `layer.query(id, op)` → adapter (ֆիքսված read op) → նորմալացված envelope (source_system, source_record_id, retrieved_at, source_updated_at, freshness LIVE/CACHED/STALE/UNAVAILABLE, classification, authority, confidence, provenance) → skill։ Vendor schema-ն skill-ին չի հասնում։

| Integration | Համակարգ | Auth | Կարդում է | Գրում է | Վիճակ |
|:---|:---|:---|:---|:---|:---|
| `INT-TASKS` | Tasks.xlsx (կանոնական ռեեստր) | լոկալ ֆայլ | tasks.list | tasks.create/update/assign/close/reopen/note (միայն Action Runtime-ով, Գև-ի հաստատմամբ) | certify-ով |
| `INT-OL-CAL` | Outlook desktop օրացույց (սեփականատիրոջ housenet.am mailbox) | Windows session + integrity-pinned `outlook_read.ps1` | calendar.events | calendar.create/update/cancel (Action Runtime) | certify-ով |
| `INT-OL-MAIL` | Outlook desktop փոստ | նույնը | mail.list · mail.search (header + ≤600 նիշ preview) | mail.draft (provider-side) · mail.send (Action Runtime) | certify-ով |
| `INT-B24` | Bitrix24 REST | read-scoped inbound webhook (repo-ից դուրս) | crm.deals/leads/stages/activities · tasks.list · users · identity — GET-only allowlist | tasks.create · crm.deal.update · crm.activity.create (Action Runtime; NOT_CONFIGURED մինչև webhook) | DECLARED, մինչև webhook |
| `INT-MB` | MikroBill | UNKNOWN (interface չի գույքագրված) | — | tariff.change · subscriber.suspend՝ **WRITE NOT CERTIFIED** (R3) | **DEFERRED by Gev (2026-09-12)** — աշխատանք չկա, nag չկա |
| `INT-TG` | Telegram (official Bot API; long polling, optional webhook; **Business/Secretary mode** as a second inbound source) | bot token repo-ից դուրս (`CC_INT_TG_*` / `~/.command-center/integrations/INT-TG.json`), allowlist chat/user ids | identity (getMe = expected username) · chat.messages (allowlist, dedupe by update id, offset persisted, attachment METADATA only) | chat.send · chat.reply (Action Runtime; provider acceptance ≠ VERIFIED_WRITE → `NO_INDEPENDENT_READBACK`, PARTIAL մինչև Գև-ը տեսնի) | IMPLEMENTED → NOT_CONFIGURED մինչև bot token |
| `INT-WA` | WhatsApp Business (official Cloud API; verified + HMAC-signed webhook) | access token · phone number id · verify token · app secret · allowed numbers (repo-ից դուրս) | identity (business phone) · chat.messages / chat.statuses՝ signed webhook-ից (handshake, signature, tenant, replay, dedupe, malformed rejection) | chat.send_text · chat.send_template (Action Runtime; async delivery status → `AWAITING_PROVIDER_STATUS` → reconcile → VERIFIED) | IMPLEMENTED → NOT_CONFIGURED մինչև credentials |

Telegram Business (Secretary Mode)՝ նույն `INT-TG`-ն է, ոչ նոր ինտեգրում։ Երկու inbound աղբյուր մեկ update stream-ով՝ `BOT_CHAT` (գրում են բոտին) և `BUSINESS` (գրում են Գև-ին, բոտը դիտում է միայն Գև-ի ընտրած private չատերը)։ Business հաղորդագրությունը ապացույց է միայն երբ կապը ակտիվ է, նույն connection-ից է և ուղարկողը Deputy-ի սեփական `business_allowed_user_ids`-ում է. Telegram-ի scope-ը Deputy-ի authority չէ։ Կապից առաջվա պատմությունը հասանելի չէ և երբեք չի ձևացվում։ `rights.can_reply`-ը provider capability է, ոչ authority. դուրս գրելը մնում է Action Runtime քարտով, իսկ կապի փոփոխությունը՝ `STALE_CONFLICT`։ Read receipt/mark-read, edit, delete, pin՝ չեն կատարվում։

Activation view (արժեքներ երբեք չեն տպվում, միայն պակասող դաշտերի ԱՆՈՒՆՆԵՐԸ)՝ `python .claude/integrations/integration.py readiness`; ակտիվացման ճշգրիտ մուտքերը՝ [.claude/docs/Activation-inputs.md](.claude/docs/Activation-inputs.md)։ Ամեն ինտեգրման համար մնում է միայն `CONFIGURE → IDENTITY VERIFY → REAL READ → LIVE CERTIFY → OPTIONAL CONTROLLED WRITE CERTIFY`։

Կանոններ՝ ընթերցող շերտի `write_ops` ամեն տեղ դատարկ է (գրելը միայն ստորև նկարագրված Action Runtime-ով է). գրող intent-ը (SEND_EMAIL, CREATE_EVENT, UPDATE_DEAL, DELETE_TASK, CHANGE_TARIFF, UPDATE_CUSTOMER…) կառուցվածքով արգելվում է՝ `layer.capability()` → AUTHORITY_EXCEEDED/WRITE_DISABLED, gate/engine → `action_runtime` (ոչ թե գործիք). աղբյուրների հեղինակությունը **կոնֆիգուրացված է** (`registry.FACT_AUTHORITY`, նաև core `sources.json → live_sources`), նույն մակարդակի երկու live աղբյուրի անհամաձայնություն = SOURCE_CONFLICT (չի միաձուլվում). freshness-ը միշտ երևում է, թարմության կանոն չկա՝ չի հորինվում. health (AVAILABLE · DEGRADED · UNAVAILABLE · AUTH_FAILED · PERMISSION_DENIED · SCHEMA_CHANGED · NOT_CONFIGURED) + վերջին հաջող ընթերցում՝ `.claude/state/integrations_health.json`, Daily Brief-ը անհասանելի կրիտիկական աղբյուրը **բարձրաձայն** է ասում. փոստից քաղվածը միայն CANDIDATE_OPEN_LOOP է (ACTION · DECISION · DELEGATE · MONITOR · FYI · IGNORE), ոչ մշտական փաստ. secrets՝ `~/.command-center/integrations/<ID>.json` կամ `CC_<ID>_<KEY>` env, երբեք repo/audit (LEAK_PREVENTED). աուդիտում՝ ինչ հարցվեց (op, param keys, count), ոչ payload։ Վկայագրում՝ `python .claude/integrations/integration.py certify` → DECLARED → CONFIGURED → CONNECTED → VERIFIED_READ → RELIABLE_READ (≥10 իրական ընթերցում ≥2 օրում), ապացույցներով (auth, scope, write_rejected, schema, freshness, failure matrix, provenance, sensitive boundary). `skill.py release`-ը այն սպառում է։ Հրամաններ՝ `integration.py status | query <id> <op> | probe | brief | capability "<intent>"`։

## Խելք — Live Sales & Operations Intelligence (Mission 5)

`.claude/skills/intelligence.py` — մեկ կանոնական pipeline՝ `LIVE READS → NORMALIZE → PROVENANCE/FRESHNESS → CURRENT STATE → CHANGE DETECTION → EXCEPTIONS → CAUSE DISCIPLINE → IMPACT → PRIORITY → RECOMMENDATION → OWNER → DEADLINE → GEV ACTION → MANAGEMENT OUTPUT`։ Բիզնես մոդելը ասում է՝ ինչ է նշանակում (owner, KPI, process, playbook), live ինտեգրումները՝ ինչ է կատարվում հիմա։

| Հարց (բնական լեզու) | Հմտություն | Պատասխան |
|:---|:---|:---|
| «էսօր ինչ կա», «ով ա ուշացրել», «ինչ task-եր են կախված», «ինչ խնդիր ունենք վաճառքում», «operations-ում ինչ ա վառվում», «ինչ action ես առաջարկում», `what needs my attention today?` | `management_snapshot` | ֆոկուսված snapshot՝ exceptions (severity → urgency → impact → deadline → dependency), 7 հարցի management պատասխան, ACTION → OWNER → DEADLINE → VERIFY, Gev-ի հերթ, visibility |
| «ինչն ա վատ գնում», «ինչից պիտի անհանգստանամ», `give me the exceptions only` | `exception_review` | միայն ապացուցված exception-ներ; չերևացող համակարգերը՝ առանձին («no exception» ≠ «ամեն ինչ լավ է») |
| «ինչ փոխվեց երեկվանից», `what changed since yesterday?` | `change_review` | NEW · CHANGED · RESOLVED · WORSENED · NEEDS_GEV durable checkpoint-ի դիմաց (աղմուկը ճնշված) |
| «ինձնից ինչ ա սպասում», «ինչ որոշում ա սպասում», «ինչ եմ ես մոռացել» | `decision_queue` | APPROVAL · DECISION · ESCALATION · OWNER NEEDED · PRIORITY CONFLICT · MISSING BUSINESS TRUTH — ինչու հենց Գև, ինչ է պետք, երբ, հետևանքը |
| «սարքի առավոտվա brief-ը», «էսօր ինչ meeting ունեմ» | `daily_briefing` (+`management`) | TOP LINE · CHANGES · SALES · OPERATIONS · TASKS · CALENDAR · MAIL · RISKS · ACTIONS · GEV |
| «end of day», «weekly review», «ինչ կարևոր mail ունեմ» / «what's open» | `end_of_day_control`, `weekly_executive_review`, `open_loop_memory` (+`management`) | EOD՝ planned/completed/slipped/moved/unverified/escalation/Gev; weekly՝ outcomes/missed/recurring/risks/decisions/bottlenecks; open loops + mail intelligence |

Ազնվության կանոններ (թեստերով)՝ ամեն փաստ կրում է source · record id · retrieved_at · freshness (LIVE/CACHED/STALE/UNAVAILABLE/NOT_CONFIGURED/FIXTURE/SUPPLIED); STALE-ը երբեք current չէ, CACHED-ը նշված է, fixture/supplied = `truth_mode NON_PRODUCTION`; պատճառը միայն CONFIRMED CAUSE / SUPPORTED HYPOTHESIS (ապացույցի ազդանշանով) / UNKNOWN; owner/deadline/թիվ չեն հորինվում (UNKNOWN, OWNER NEEDED, UNAVAILABLE / NOT CONNECTED + պակասող capability-ն անունով); Bitrix24/MikroBILL-ի sales/ops չափումները UNAVAILABLE են, մինչև ինտեգրումը միացվի (framework-ը պատրաստ է, fixture-ներով թեստավորված)։ Առաջարկը ոչինչ չի փոխում. «արա» = Action Runtime-ի քարտ։ Շարունակականություն՝ `.claude/state/durable/checkpoints.jsonl` (ստորագրություններ) և `loops.jsonl` (հղումներ, ապացույցով փակվող) — live համակարգերը մնում են հեղինակավոր։ Թեստեր՝ `test_intelligence` (19), eval բաժին H (13, հայերեն + անգլերեն)։

## Գործառնական շերտ — ACTIVATION-READY OPERATING LAYER (2026-09-12)

Նույն Store-ի, նույն Action Runtime-ի և նույն Mission 5 pipeline-ի վրա (երկրորդ հիշողություն/runtime/հաստատում չկա)՝

| Հարց | Հմտություն | Ինչ է անում |
|:---|:---|:---|
| «Տելեգրամում ինչ կա», «ում պիտի պատասխանեմ», «վաթսափից ինչ follow-up կա» | `channel_intelligence` (`skills/channels.py`) | Telegram/WhatsApp ապացույցը մեկ ինտեգրման շերտով՝ պատասխանի սպասող հարցումներ · խոստումների թեկնածուներ · Գև-ի պարտք follow-up-ներ · escalation-ներ · միջալիքային կրկնօրինակներ (մեկ loop, շատ evidence) · prompt-injection դրոշներ. չկարգավորված ալիքը՝ NOT_CONFIGURED պակասող դաշտերի անուններով, ոչ «նորություն չկա» |
| «ով ինչ ա խոստացել», «ով ա ամենաշատ խոստում ուշացնում», «վաղը ումից ինչ եմ սպասում» | `commitment_memory` (`skills/commitments.py`) | խոստումների engine՝ mail/Telegram/WhatsApp/ժողովի նոթեր/Գև-ի խոսք → STRONG vs WEAK, due UNKNOWN-ը մնում է UNKNOWN, lifecycle OPEN/DUE_SOON/OVERDUE/FULFILLED/CANCELLED/SUPERSEDED/UNVERIFIED, փակում միայն ապացույցով, task ինքնաբերաբար չի ստեղծվում |
| «ինչ որոշեցինք դրա մասին», «էս որոշումը դեռ ուժի մեջ ա՞» | `decision_memory` (`skills/decisions.py`) | որոշման հիշողություն՝ ինչ/երբ/ով/ինչու/այլընտրանք/owner/effective/review/status/supersedes; Գև-ի խոսքը՝ CONFIRMED, դրսինը՝ CANDIDATE; հակասությունները ցույց են տրվում, ոչինչ լուռ չի վերագրվում |
| «էս մարդը որ բաժնից ա», «ում ա 4.1-ը» | `people_resolver` (`skills/people.py`) | մարդ ↔ դեր ↔ email ↔ Outlook ↔ Bitrix ↔ Telegram ↔ WhatsApp. մեկ արտաքին id երբեք լուռ երկու մարդու չի; երկիմաստը՝ UNKNOWN / NEEDS CONFIRMATION; հղումը հաստատում է միայն Գև-ը |
| «էս KPI-ն ումն ա», «էս KPI-ի target-ը ինչ ա» | `kpi_intelligence` (`skills/kpis.py`) | KPI binding բիզնես-մոդելից՝ սահմանում · բանաձև · owner դեր → մարդ · APPROVED target (այլապես TARGET_UNKNOWN) · աղբյուր → ինտեգրում · արժեքի հասանելիություն (UNAVAILABLE երբ աղբյուրը միացած չէ/deferred) · provenance. Mission 5 sales չափումները սպառում են այս binding-ները |
| «պատրաստի ինձ էս meeting-ին» · «ժողովից ինչ մնաց բաց» | `meeting_preparation` (+pack) · `meeting_notes` | pre-meeting pack՝ մասնակիցների խոստումներ (lifecycle), թեմայի որոշումներ (ուժի մեջ՞), KPI-ներ, բաց alert-ներ, հարցեր; post-meeting՝ ՄԻԱՅՆ տրված նոթերից՝ որոշման/խոստման թեկնածուներ, բաց հարցեր, action draft-ներ — ամեն ինչ CANDIDATE, ոչինչ չի գրվում |
| «էսօր ինչ նոր escalation կա» | `alert_review` (`skills/alerts.py`) | Mission 5 exception-ների alert-ներ՝ dedupe · new/escalated/open · ack · suppress · resolve (ապացույցով) · reopen; դուրս ուղարկելը՝ Action Runtime հաստատում |
| `find …` | `information_retrieval` (+`skills/documents.py`) | document brain՝ վերակառուցվող ինդեքս (path/title/hash/date/type/authority/current/sections), դետերմինիստիկ որոնում, բիզնես-մոդելի փաստերն առաջինը, հակասող current փաստաթղթերը՝ CONFLICT |
| «ուղարկի», «տելեգրամով ուղարկի», `send on whatsapp` | `action_runtime` | chat.send / chat.reply / chat.send_text / chat.send_template — միայն հաստատման քարտով |

Routines (`skill.py routine morning|midday|eod|weekly`)՝ գոյություն ունեցող հմտությունների կոմպոզիցիա, on demand; scheduler-ը `NOT_CONFIGURED` է, մինչև իրական trigger-ը (`--from-scheduler` heartbeat)։ Prompt-injection օրենք՝ արտաքին տեքստը (mail/chat/փաստաթուղթ) ՏՎՅԱԼ է, ոչ հրահանգ. ոչ մի արտաքին ուղարկող չի կարող քարտ հաստատել (`EXTERNAL_SOURCE_REFUSED`), ոչ մի ինքնաբերական արտաքին ուղարկում չկա։ Տվյալների նվազեցում՝ chat warehouse չկա (ids, sender ref, timestamp, ≤300 նիշ excerpt, attachment metadata՝ լոկալ `channel_events`, երբեք versioned)։

## Ձեռքեր — Action Runtime (Mission 4.2, AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE)

`.claude/skills/actions.py` + `action_runtime` հմտություն + `.claude/integrations/capabilities.py` և write adapter-ներ (`adapter_tasks_write.py`, `adapter_outlook_write.py` + integrity-pinned `outlook_write.ps1`, `adapter_bitrix24_write.py`)։ Օրենքը՝ `.claude/policy/approval_rule.json` (մեկ տեղում, չի կրկնօրինակվում)։

```
INTENT → PREPARE (capability · authority · duplicate · precondition · fingerprint · idempotency key)
      → ԳԵՎ-Ի ՔԱՐՏ  «READY FOR YOUR APPROVAL … Nothing has been changed yet. Approve?»
      → APPROVAL  միայն OK / GO / Արա / Հաստատում եմ  (մեկանգամյա տոկեն · 24ժ · կապված ճշգրիտ fingerprint-ին · batch = ճշգրիտ ցանկ)
      → EXECUTE  (actions.lock · stale-state վերընթերցում → STALE_CONFLICT · audit-first, AUDIT_UNAVAILABLE = չի կատարվում)
      → VERIFY   (անկախ read-back; API success ≠ ավարտ)  → REPORT  DONE / NOT DONE / PARTIAL / BLOCKED / RESULT_UNKNOWN
```

| Վիճակ | Նշանակում է |
|:---|:---|
| APPROVAL_REQUIRED / DENIED | պատրաստ է կամ մերժված կանոնով (CAPABILITY_UNAVAILABLE · NOT_CONFIGURED · AUTHORITY_EXCEEDED · DUPLICATE · ALREADY_EXISTS · TARGET_NOT_FOUND) — ոչինչ չի փոխվել |
| APPROVED → EXECUTING → EXECUTED_UNVERIFIED → VERIFIED | տոկենը սպառվում է առաջին կատարումից; VERIFIED = read-back-ը համընկնում է հաստատված գործողությանը |
| REJECTED | Գև-ը մերժեց, կամ թիրախը փոխվել էր քարտից հետո (STALE_CONFLICT), կամ տոկենը՝ ժամկետանց/այլ գործողության |
| RESULT_UNKNOWN | provider-ը չպատասխանեց → RECONCILE FIRST (FOUND → verify, ABSENT → retry թույլատրելի, UNDETERMINED → Գև-ի որոշում); կույր retry չկա |
| PARTIAL | batch-ի մի մասն է կատարվել — ազնիվ ցուցակ, rollback չի ձևացվում |

Հնարավորությունների ռեեստր (`capabilities.table()`)՝ DECLARED → IMPLEMENTED → CONFIGURED → CONNECTED → VERIFIED_READ → **VERIFIED_WRITE** (միայն `.claude/state/durable/write_certifications.json`-ից՝ Գև-ի հաստատած իրական գրառում) / UNAVAILABLE։ Idempotency-ն restart-ից հետո էլ պահպանվում է (`.claude/state/durable/actions.jsonl` → hardened store)։ Թեստեր՝ `test_actions` (governance · idempotency/failure · verification · Tasks adapter temp copy-ի վրա · capability/routing), eval բաժին G (18 վարքային սցենար)։ Թեստերն ու eval-ները **երբեք** իրական Tasks.xlsx-ին կամ Outlook-ին չեն դիպչում (env `COMMAND_CENTER_TASKS_XLSX` + sha guard, FakeProvider)։

Python runtime՝ դետերմինիստիկ. ամեն hook, CLI, test, eval և release աշխատում է `<root>/.venv`-ով (`.claude/runtime/` — `python_runtime.py` shim, `hook.sh` launcher, `requirements.txt` manifest + `requirements.lock`), PATH-ի `python`-ը դեր չունի։ `.venv`-ը git-ում չէ. վերակառուցում՝ `py -3 .claude/runtime/python_runtime.py bootstrap`։

---

## Փոխադրելիություն — GitHub + վերականգնման բանալի = ամբողջ workspace-ը

Ամեն արժեքավոր ֆայլ Git-ում է, ներառյալ երկուական բիզնես փաստաթղթերը՝ Word, Excel, PowerPoint, PDF, պատկերներ, HTML, ZIP արխիվներ և հին նախագծերի փաթեթներ։ Նոր համակարգչում աշխատանքը սկսելու համար ձեռքով ոչինչ պատճենել պետք չէ։

```bash
git clone https://github.com/ohanyan88-cmd/Command-center.git
cd Command-center
git lfs install && git lfs pull        # երկուական բիզնես ֆայլերը
python bootstrap.py                    # runtime, durable state, credentials, certification
```

**Windows-ում՝ երկար ուղիներ։** Արխիվային անվանատարածքը կրում է հին նախագծերի բնօրինակ, երկար ֆայլանունները։ Եթե clone-ը դնես շատ խորը պանակում, Windows-ի 260-նիշ սահմանը կարող է տալ `Filename too long`։ Լուծումը՝ `git config --global core.longpaths true`, կամ պարզապես clone արա կարճ ուղու վրա (օր.՝ `C:\Command-center`)։ `bootstrap.py`-ը զգուշացնում է այս մասին։

**Git LFS-ը պարտադիր է։** Office փաստաթղթերը, PDF-երը, արխիվները և git bundle-ները պահվում են LFS-ով, որովհետև GitHub-ը մերժում է 100 ՄԲ-ից մեծ սովորական blob-երը, իսկ այս workspace-ում այդպիսիք կան։ Կանոնները՝ [.gitattributes](.gitattributes)-ում՝ `*.docx *.xlsx *.xlsm *.pptx *.pdf *.zip *.7z *.bundle`։ Պատկերները դիտմամբ մնում են սովորական Git-ում՝ ընդհանուր ծավալը փոքր է, իսկ LFS-ի թողունակությունը ամեն clone-ի վրա ծախսվում է։ Եթե նոր մեքենայում LFS չկա, `bootstrap.py`-ը կանգնում է հստակ հրահանգով, և եթե LFS օբյեկտները ներբեռնված չեն՝ ասում է `git lfs pull`։

**Git-ից դուրս մնում է միայն այն, ինչը վերարտադրելի է կամ գաղտնիք է.** `.venv`, `__pycache__`, մեքենայական աղբ, ephemeral runtime state (canonical durable export-ը՝ `.claude/state/durable/`, versioned է), վերարտադրվող business-model և integration JSON-ները, և plaintext credential-ները։ Վերջիններս ապրում են միայն `.secure/credentials.gpg`-ում, բանալին՝ repo-ից դուրս։

Ամբողջ 2026-09-14 վերակազմակերպումը՝ ո՞ր ֆայլը որտեղից ուր գնաց, ի՞նչ hash-ով և ինչո՞ւ, գրված է [05_Archive/Migration-2026-09-14/Migration-manifest-2026-09-14.md](WORKSPACE/05_Archive/Migration-2026-09-14/Migration-manifest-2026-09-14.md)-ում։

---

## Երկու արմատ — մի՛ խառնիր

**`WORKSPACE/`** — Գև-ի բիզնես արմատը. `00_Inbox · 01_Active · 02_Reference · 03_Completed · 04_Sources · 05_Archive` + `Tasks.xlsx · Journal.md · Actions.md`։ Այն ամենը, ինչ Գև-ը բացում, կարդում, խմբագրում կամ որպես բիզնես նյութ օգտագործում է։

**Repository root** — Deputy-ի տեխնիկական պատյանը. `.claude/` (engine), `.secure/` (գաղտնագրված վերականգնում), `.venv/` (վերագեներացվող), `bootstrap.py`, `CLAUDE.md`, `README.md`, `.gitignore`, `.gitattributes`։ Գև-ը այստեղ մտնելու կարիք չունի։

Բիզնես արմատի անունը հայտարարված է **մեկ տեղում**՝ `.claude/policy/workspace_policy.json → business_root`, և լուծվում է `.claude/policy/paths.py`-ով։ Validator-ը, guard-ը, tree manifest-ը, sync-ը, skill-երը, ադապտերները և թեստերը բոլորն անցնում են այդ մեկ resolver-ով, այնպես որ երկու արմատը այլևս չեն կարող միմյանց մեջ մտնել։

## HARD SCOPE LOCK

Deputy-ն փոխում է **միայն այն, ինչ Գև-ի ընթացիկ հանձնարարությունն է պահանջում**։ Ճանապարհին նկատած սխալը, ավելի գեղեցիկ ճարտարապետությունը, «մի բան էլ մաքրենք»-ը՝ **REPORT ONLY**։ Կանոնը՝ `workspace_policy.json → scope_lock`, շարժիչը՝ `.claude/policy/scope.py`, պահվում է gate ticket-ի վրա (`ticket['scope']`)։ Default-ը **DENY** է. առանց հաստատված Scope Contract-ի ոչ մի ֆայլ չի փոխվում։ Երեք դարպաս՝ **mutation gate** (`gate.py` PreToolUse), **action runtime** (`actions.py prepare` → `OUT_OF_SCOPE`) և **scope-diff gate** (`scope.py --staged`, git pre-commit hook-ում) — մեկ scope-ից դուրս ուղի = HARD FAIL, ոչ commit, ոչ push, ոչ PR։ Deputy-ն ինքն իրեն scope ընդլայնել չի կարող. ենթահամակարգը մտնում է պայմանագիր միայն **Գև-ի սեփական հաղորդագրության** ապացույցով։
