# COMMAND-CENTER / DEPUTY — PROJECT CONTEXT & CONTINUITY HANDOFF

**Handoff date:** 2026-09-12 (Asia/Yerevan)  
**Owner:** Gev / Gevorg  
**Canonical workspace:** `Command-center`  
**Canonical agent:** `Deputy`  
**Full role:** `Deputy — AI Chief of Staff for Sales & Operations`  
**Canonical GitHub SST:** `https://github.com/ohanyan88-cmd/Command-center`  
**Canonical branch:** `main`  
**Current verified GitHub `main` HEAD at handoff:** `f2177bc0a499f1f25c11e00d6eb65e7c91487570`  
**Current mission status:** `MISSION 4.2 — READY FOR LIVE CERTIFICATION / AWAITING GEV APPROVAL`  
**Repository visibility:** PUBLIC by explicit owner decision; Gev has explicitly accepted the confidentiality/public exposure risk. Do not reopen this as a blocker unless Gev changes that decision.

---

# 0. HOW TO USE THIS FILE IN A NEW CHAT

This file is the continuity source for the `Command-center / Deputy` project.

When a new chat starts:

1. Read this file first.
2. Treat the GitHub repository `ohanyan88-cmd/Command-center`, branch `main`, as the live technical source of truth.
3. Verify the current remote `main` before relying on the SHA recorded here, because the repository may have advanced after this handoff.
4. Use this file as the authoritative continuity/handoff context for decisions, architecture, mission history, user intent, governance, and current pending work.
5. If this file and current GitHub `main` conflict, GitHub wins for implementation state, but surface the contradiction if it changes a decision.
6. Do not silently revive old designs, old repos, old names, or old assumptions.
7. Do not ask Gev to re-explain decisions already recorded here unless a real ambiguity remains after checking this file and current repo truth.
8. Do not treat unrelated projects (BRO, GAAhex/GHEX, OS, HouseNet strategy work, etc.) as the source of truth for this project unless Gev explicitly brings them in.

**Recommended first message in a new chat:**

> Շարունակում ենք `Command-center / Deputy` project-ը այս handoff file-ից ու current GitHub `main`-ից։ Current pending gate-ը Mission 4.2 live write certification-ն է։ Նախ verify արա current main-ը, հետո շարունակիր հենց handoff-ի CURRENT STATE-ից։

---

# 1. USER / WORKING STYLE

## User
- Preferred name: **Gev / Gevorg**
- Friendly Armenian forms are welcome: **ընգեր, ախպեր, դռուգ, թագավոր, քեռի, հոպար**.
- Style preference: friendly, direct, energetic, compact, practical.
- Quality preference: **quality-first + verify-first**.
- Do not guess current state when the repo or source can be checked.
- When a contradiction matters, surface it explicitly instead of silently choosing.
- Avoid unnecessary clarification questions; make a strong best-effort move when context is sufficient.
- User likes “գազ” execution: once scope is clear, continue non-stop through implementation/checks until a real approval or external blocker exists.
- For management/business outputs: conclusion first, then cause/impact/action/owner/deadline.

## Working relationship
Gev wants Deputy to behave like a highly capable human Chief of Staff / Deputy:
- understand short natural-language outcomes,
- gather facts,
- plan,
- prepare exact actions,
- coordinate systems,
- remember open loops,
- follow up,
- escalate,
- verify completion,
- never invent capability,
- never claim completion without evidence,
- and never perform a real business mutation without Gev’s explicit approval.

---

# 2. CANONICAL PRODUCT IDENTITY

## Workspace
**Name:** `Command-center`

This is Gev’s operational workspace / management cockpit.

## Agent
**Name:** `Deputy`

**Full role:** `AI Chief of Staff for Sales & Operations`

Deputy is an identity and operating role. It is **not** a `.claude/Deputy/` directory.

The technical architecture remains under `.claude/*`.

## Core product idea
Gev gives Deputy a short natural-language management request.

Deputy should:
1. understand the intended outcome,
2. resolve business context,
3. gather current facts,
4. determine process/owner/KPI/source,
5. plan the exact action,
6. use the correct skills/tools,
7. check authority,
8. present any real mutation to Gev,
9. wait for explicit approval,
10. execute only the approved action,
11. verify reality after execution,
12. update memory/open loops,
13. follow the result until actually complete.

Deputy should feel like:
- **head** = reasoning/business understanding,
- **eyes** = live read integrations,
- **hands** = controlled execution,
- **memory** = durable commitments/decisions/open loops,
- **feet** = follow-through/progress.

---

# 3. SOURCE-OF-TRUTH RULES

## Technical SST
Sole live technical source of truth:

`https://github.com/ohanyan88-cmd/Command-center`

Branch:

`main`

At this handoff the verified remote `main` HEAD is:

`f2177bc0a499f1f25c11e00d6eb65e7c91487570`

Commit title:

`Merge Mission 4.2 — Controlled Hands (PR #1)`

Mission 4.2 implementation commits immediately before merge:
- `f073b216f7f28287c51fcc2711c1629ca52838ef`
- `358d4d7d35b5be2aade393e707088fa7d837aafa`
- `6ddea12fac7fe3ca67f64fb72f904669d220eee0`
- merge: `f2177bc0a499f1f25c11e00d6eb65e7c91487570`

Mission 4.2 approval-law baseline:
- `cb89ab7925532f17aea2bbec0044485fd23accb8`

Mission 4.1 final durability baseline before the approval-law change:
- `2d8cc9a25485ed3b45ace6f19ef5ce85a682351f`

## Source priority
When working:
1. Current GitHub `main`
2. Canonical policies/contracts inside repo
3. This handoff for continuity and intent
4. Current conversation
5. Historical chat memory only as contradiction detector

Never let remembered older state override current repo truth.

---

# 4. CURRENT CANONICAL WORKSPACE SHAPE

```text
Command-center/
├── CLAUDE.md
├── README.md
├── Tasks.xlsx
├── Journal.md
├── Actions.md
├── 00_Inbox/
│   └── Input.md
├── 01_Active/
│   ├── Sales/
│   ├── Operations/
│   ├── People/
│   └── Systems/
├── 02_Reference/
│   ├── Sales/
│   ├── Operations/
│   ├── People/
│   └── Systems/
├── 03_Completed/
├── 04_Sources/
│   ├── Whatsapp/
│   ├── Screenshots/
│   └── Imports/
├── 05_Archive/
└── .claude/
    ├── settings.json
    ├── hooks/
    ├── docs/
    ├── policy/
    ├── skills/
    ├── tools/
    ├── tests/
    ├── runtime/
    ├── state/
    ├── audit/
    ├── business/
    └── integrations/
```

Historical physical root:

`C:\Users\Admin\Desktop\Command-center`

Old workspace `Daily check` was migrated away. A historical `Daily check.zip` backup may still exist outside the canonical workspace.

---

# 5. WORKSPACE SEMANTICS

## Root
Operational cockpit with canonical human-facing files:
- `Tasks.xlsx`
- `Journal.md`
- `Actions.md`

## `00_Inbox`
Temporary unclassified input; steady state mostly `Input.md`.

## `01_Active`
Current work under development/execution.

## `02_Reference`
Approved current source-of-truth still operationally used.

Important:
“Finished creation” does **not** imply `03_Completed` if the artifact remains current reference.

## `03_Completed`
Finished deliverables no longer active/current reference.

## `04_Sources`
Raw original evidence/input:
- WhatsApp exports
- screenshots
- imports

## `05_Archive`
Superseded/draft/obsolete material retained for history.

## `.claude/docs`
Durable agent/system docs.

## `.claude/skills`
Production Skill System.

## `.claude/tools`
Technical helpers.

## `.claude/business`
Business model, generated model, overlay.

## `.claude/integrations`
Integration registry, adapters, certification and integration runtime.

---

# 6. NAMING STANDARD

Business-facing paths:
- English only
- ordered top-level directories use `NN_Name`
- multi-word filenames use hyphenated sentence-case
- date: `YYYY-MM-DD`
- version: `vN.N`
- lowercase extension

Example:

`Sales-strategy-v1.1-2026-09-10.docx`

Avoid:
- spaces
- parentheses
- `(2)`
- `final`
- `final2`
- `new`
- `newest`
- `copy`
- `fixed`

Technical conventions remain normal:
- `.claude`
- `CLAUDE.md`
- `README.md`
- JSON conventions
- Python lowercase_snake_case

---

# 7. MISSION HISTORY — HIGH LEVEL

## Mission 1 — Skill System
Build Deputy’s governed capability/skill system.

## Mission 2 — Workspace Architecture
Migrate real workspace into canonical Command-center architecture; enforce workspace rules; make runtime deterministic.

## Mission 3 — Business Operating Model
Teach Deputy actual business: sources, organization, roles, processes, ownership, KPIs, routines, playbooks, provenance, current vs historical truth, gaps.

## Mission 4 — Eyes / Read Integrations
Give Deputy safe live read capability without write authority.

## Mission 4.1 — Durability / Recovery
Ensure no important truth exists only on one PC; make GitHub + recovery key sufficient to reconstruct Command-center.

## Mission 4.2 — Controlled Hands
Build write/execution machinery while preserving zero autonomous external write authority.

**Current state:** final gate of Mission 4.2.

---

# 8. MISSION 1 — SKILL SYSTEM

## Skill contract
`Trigger → Inputs → Actions → Output → Tools → Approval required → KPI`

## Maturity
- `L0` Declared
- `L1` Assisted
- `L2` Operational
- `L3` Reliable
- `L4` Hardened

Maturity is independent of authority.

## Canonical execution pipeline
`TASK UNDERSTANDING`
→ `SKILL RESOLUTION`
→ `REQUIRED SKILL GRAPH`
→ `PRECONDITION CHECK`
→ `AUTHORITY CHECK`
→ `EXECUTION`
→ `OUTPUT VALIDATION`
→ `COMPLETION VERIFICATION`
→ `AUDIT RECORD`

Fail closed on:
- missing skill
- missing input
- missing tool
- missing approval
- missing evidence

## Important architecture
- Skill Router/Resolver
- multi-skill execution
- controlled skill acquisition
- hardening
- observability
- tests/evals
- per-skill certification
- authority boundaries

Historical stabilized maturity snapshot:
- L0 = 8
- L1 = 21
- L2 = 15
- L3 = 7
- L4 = 10

Historical L4 examples:
- task_management
- deadline_management
- waiting_for_tracking
- daily_briefing
- commitment_tracking
- authority_checking
- approval_management
- completion_verification
- audit_logging
- source_verification

Historical L3 examples:
- executive_prioritization
- reminder_intelligence
- follow_up_management
- decision_logging
- commitment_memory
- decision_memory
- open_loop_memory

**Current Mission 4.2 release:** 63 certified skills.  
`action_runtime` maturity: **L3**.

Do not use the old 61-skill count as current.

---

# 9. MISSION 2 — WORKSPACE ARCHITECTURE

Mission 2 established:
- canonical `Command-center` identity
- canonical tree
- machine-readable workspace policy
- deterministic Python runtime
- migration from old `Daily check`
- workspace validation
- mutation guards
- policy-driven structure
- bootstrap/recovery foundations

Canonical policy:

`.claude/policy/workspace_policy.json`

Canonical identity:
- agent: Deputy
- role: AI Chief of Staff for Sales & Operations
- workspace: Command-center
- owner: Gev

Drift should be caught by validation.

---

# 10. DETERMINISTIC PYTHON / RUNTIME

Mission 2 hardening introduced deterministic runtime under:

`.claude/runtime/`

Historically included:
- `python_runtime.py`
- `hook.sh`
- `requirements.txt`
- `requirements.lock`

Root `.venv` is regenerated/ignored.

Principles:
- locked dependencies
- no accidental global-Python dependency
- fail closed or bootstrap correctly
- machine-local dependencies explicit

---

# 11. MISSION 3 — BUSINESS OPERATING MODEL

Mission 3 goal: teach actual business, not generic management knowledge.

## Provenance
Important business facts carry:
- source path
- version/date
- effective date
- authority/status
- confidence
- current/historical classification

Fact statuses:
- `CONFIRMED`
- `DERIVED`
- `UNVERIFIED`
- `UNKNOWN`

Truth-state classifications:
- `CURRENT`
- `SUPERSEDED`
- `HISTORICAL`
- `UNKNOWN`

Conflicts should be surfaced.

## Modeled scope
- company/functions
- roles
- responsibilities
- ownership
- Sales processes
- Operations processes
- People context
- Systems context
- KPIs
- routines
- playbooks
- gaps

## Process model
`TRIGGER → INPUT → ACTION → OWNER → HANDOFF → CONTROL → OUTPUT → VERIFY`

## Playbook model
`SIGNAL → VERIFY → DIAGNOSE → ROOT CAUSE → IMPACT → ACTION → OWNER → DEADLINE → FOLLOW-UP → VERIFY → CLOSE`

## Business model area
`.claude/business/`

Later missions reported business-model revisions around:
- `2026-09-11.1`
- `2026-09-11.2`

Mission 4.1 reported source inventory `S01–S16` available in clean clone.

Missing business truth remains structured unknown/gap. Do not invent it.

---

# 12. MISSION 4 — DEPUTY’S EYES

Mission 4 commit:

`c3ffda1b127fd5c42b18d2869487e7591f76bdca`

Added read-only live-information layer with:
- integration registry
- read allowlist
- no writes at that phase
- provenance/freshness envelopes
- health / last successful read
- audit
- conservative reconciliation
- meeting packs
- Daily Brief live context

Declared integrations:
- `INT-TASKS`
- `INT-OL-CAL`
- `INT-OL-MAIL`
- `INT-B24`
- `INT-MB`

Mission 4 = **eyes**, not hands.

---

# 13. MISSION 4 AUDIT REMEDIATION

Commit:

`23b592f47d7d2458ee53a5ccea40cdbfdf8e276e`

Key remediation:
- mailbox/calendar payloads memory-only
- persistent cache hard expiry
- audit through hardened store
- `AUDIT_UNAVAILABLE` fails closed
- task fact authority separated across systems
- status divergence preserved
- certification ops explicitly required
- fixtures never count as real reads
- health/cache concurrency hardened

Historical release:
- 287 tests
- 77 evals

---

# 14. MISSION 4.1 — DURABILITY / RECOVERY

Goal:

**No important local-only truth.**

Durability classes:
- `VERSION_DIRECTLY`
- `VERSION_ENCRYPTED`
- `REGENERATE`
- `MACHINE_LOCAL`
- `EPHEMERAL`
- `TEMPORARY`

Policy reached version `1.6.0`.

## Tree manifest
`.claude/policy/workspace_tree_manifest.json`

Generated from `workspace_policy.json`.

Mission 4.1 report:
- 71 entries then
- validator fails if stale
- validator fails if required physical paths missing

Mission 4.2 later reported manifest = **72 entries**.

## Versioned directly
Includes:
- `Tasks.xlsx`
- `Journal.md`
- `Actions.md`
- `00–05`
- `.claude/business/overlay/*`
- durable Deputy state export
- required source docs/business files

## Regenerated
Examples:
- `.venv`
- generated business-model JSON/MD
- certification artifacts

## Versioned encrypted
`.secure/credentials.gpg`

At Mission 4.1 there were zero active credentials inside.

## Recovery key
`~/.command-center/recovery.key`

Rules:
- external secret
- never repo
- never logs
- never audit
- Gev should keep copy in password manager

## Durable state snapshot
`.claude/runtime/state_snapshot.py`

Exports/imports:
- commitments
- decisions
- audit
- business observations

Idempotent by `op_id`.

## Secure recovery
`.claude/runtime/secure_recovery.py`

Backs up/verifies/restores machine integration secrets/config via encrypted artifact.

## Bootstrap
```bash
git clone https://github.com/ohanyan88-cmd/Command-center.git
cd Command-center
py -3 bootstrap.py [--release]
```

Mission 4.1:
- 15 steps
- idempotent
- second run: all present / new=0 / READY

## Clean-machine proof
Proven:
- fresh GitHub clone
- separate `COMMAND_CENTER_HOME`
- only external recovery key
- new venv
- no original state/model/overlay copied
- parity/checksums matched

Mission 4.1 quality:
- 301/301 tests
- 77/77 evals
- L4 remained 10

Final verdict:
`GITHUB + RECOVERY KEY → COMPLETE COMMAND-CENTER: PASS`

---

# 15. PUBLIC REPOSITORY DECISION

The repo contains real business workspace content.

The confidentiality risk was explicitly discussed.

**Gev explicitly accepted the PUBLIC-repository risk.**

Therefore:
- PUBLIC visibility is not a blocker
- do not repeatedly reopen this decision
- mention only if directly relevant or Gev changes the decision
- real secrets still must never be stored in repo

---

# 16. MANDATORY GEV APPROVAL LAW

Commit:

`cb89ab7925532f17aea2bbec0044485fd23accb8`

Canonical law:

`.claude/policy/approval_rule.json`

Also mirrored in `CLAUDE.md`.

## Overriding rule
`AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE`

Applies from Mission 4.2 onward.

## Allowed without approval
Deputy may:
- read authorized info
- search
- analyze
- diagnose
- plan
- recommend
- prepare drafts locally/in memory
- prepare action plans
- prepare task/calendar/email changes
- calculate expected impact
- perform non-mutating verification
- run local technical operations
- tests
- validation
- generated model rebuild
- health checks
- authorized technical development work

## Forbidden without approval
Any real mutation, including:
- create task
- assign/reassign task
- change deadline
- change status
- close/reopen task
- create/change calendar event
- invite/remove participants
- cancel meeting
- provider-side email draft
- send/reply/forward email
- create/update CRM
- create/update Bitrix24
- change MikroBILL/billing
- customer-impacting action
- employee-impacting action
- external communication
- delete anything
- any authoritative business-system write

## Canonical mutation flow
`PREPARE → SHOW GEV EXACT ACTION → WAIT FOR EXPLICIT APPROVAL → EXECUTE → VERIFY → REPORT`

## No approval
`DO NOT EXECUTE`

## Not approval
- silence
- recommendation
- old approval
- vague conversation
- “looks good” unless unmistakably tied to exact pending action

## Valid approval examples
- `OK`
- `GO`
- `Արա`
- `Հաստատում եմ`
- unmistakable equivalent from Gev referring to exact action

## Approval binding
Material changes invalidate approval:
- recipient
- owner
- target
- deadline
- date/time
- content
- operation
- amount
- scope
- attachment
- participants
- customer
- system

## Batch
Clearly enumerated batch may be approved once.

Only exact listed actions may run.

Additional mutation → new approval.

## Retry
Approval never authorizes blind duplicate execution.

Timeout/uncertain response:
`RECONCILE FIRST`

Still unknown:
`RESULT_UNKNOWN`

No duplicate write until reconciled.

## Future autonomy
Only via separate explicit owner decision + policy change.

**Hands ≠ autonomy.**

---

# 17. MISSION 4.2 — CONTROLLED HANDS

## Baseline
Started from `cb89ab7`.

## Branch / PR / merge
Branch:
`mission-4.2-controlled-hands`

PR:
`#1`

Merged into `main`.

Merge commit:
`f2177bc0a499f1f25c11e00d6eb65e7c91487570`

## Canonical Action Runtime
Reported canonical implementation:

`.claude/skills/actions.py`

Skill:
`action_runtime`

Every write intent and approval/rejection text routes here.

## Lifecycle
`INTENT`
→ `PREPARE`
→ capability
→ authority
→ duplicate check
→ precondition
→ fingerprint
→ idempotency key
→ Gev approval card
→ `APPROVED`
→ `EXECUTING`
→ stale-state re-read
→ `EXECUTED_UNVERIFIED`
→ independent `VERIFY`
→ `REPORT`

API success ≠ completion.

## Approval token
Reported:
- single-use
- exact fingerprint bound
- 24h validity
- parameter changes invalidate
- ambiguous approval fails closed

## Routing nuance
“cancel tomorrow’s meeting” = mutation intent to prepare, not rejection of approval.

## Safety
Reported:
- idempotency survives restart
- timeout → `RESULT_UNKNOWN`
- reconcile first
- audit-first fail closed
- exact batch semantics
- `PARTIAL` for partial execution
- cross-process locking
- concurrency: 6 threads → 1 write

## Stale state
Re-read relevant current state before executing an approved write.

Do not blindly overwrite changed reality.

---

# 18. CURRENT INTEGRATION CAPABILITY

This is the Mission 4.2 final-report state. Verify repo/runtime before acting.

## INT-TASKS
Read:
- `tasks.list` = `VERIFIED_READ`

Writes:
- create = `CONNECTED`
- update = `CONNECTED`
- assign = `CONNECTED`
- close = `CONNECTED`
- reopen = `CONNECTED`
- note = `CONNECTED`

**Not yet `VERIFIED_WRITE`.**

## INT-OL-CAL
Read:
- calendar events = `VERIFIED_READ`

Writes:
- create = `CONNECTED`
- update = `CONNECTED`
- cancel = `CONNECTED`

**Not yet `VERIFIED_WRITE`.**

## INT-OL-MAIL
Read:
- list/search = `VERIFIED_READ`

Writes:
- provider-side draft = `CONNECTED`
- send = `CONNECTED`

Important:
local draft ≠ provider-side draft ≠ send.

**Not yet `VERIFIED_WRITE`.**

## INT-B24
- write ops implemented
- `NOT_CONFIGURED`
- no webhook/credential at Mission 4.2 report

Do not pretend live Bitrix24 exists.

## INT-MB
Examples:
- tariff.change = `UNAVAILABLE`
- subscriber.suspend = `UNAVAILABLE`

Status:
`WRITE NOT CERTIFIED`

Treat billing writes as high sensitivity.

---

# 19. MANAGEMENT LOOP

After verified actions, Deputy may update:
- commitments
- decisions
- waiting-for/open loops

Canonical result words:
- `DONE`
- `NOT DONE`
- `PARTIAL`
- `BLOCKED`
- `RESULT_UNKNOWN`

Expected user-facing fields:
- WHAT
- RESULT
- VERIFICATION
- OPEN LOOP
- GEV ACTION

Creating a task or sending a request does not by itself close the management loop.

Underlying commitment must be verified complete.

---

# 20. MISSION 4.2 QUALITY / RELEASE

Final report after merge:
- workspace validation: 0 problems
- tests: **317/317**
- suites: **12**
- evals: **95/95**
- hands evals: **18**
- certified skills: **63**
- `action_runtime`: **L3**
- full release: `RELEASE OK`
- manifest verified
- Mission 4.1 clean-clone durability preserved
- local main = origin/main = GitHub main
- tree clean
- ahead/behind = 0/0

Current GitHub `main` verified after report:

`f2177bc0a499f1f25c11e00d6eb65e7c91487570`

---

# 21. DISCLOSED MISSION 4.2 INCIDENT

During the first Tasks-adapter test run, real canonical `Tasks.xlsx` was accidentally mutated.

A row:

`TEST — hands certification`

was created and went through assignment / close / reopen because adapter defaulted to canonical register.

Recovery:
- `Tasks.xlsx` restored from git
- register back to 15 real tasks
- no TEST rows remained

Root-cause remediation:
- explicit `register_path`
- environment guard
- SHA integrity check
- tests/evals prevented from touching real Tasks.xlsx
- tests/evals prevented from touching real Outlook

This incident is resolved.

**Do not remove these guardrails.**

---

# 22. CURRENT PENDING GATE — LIVE WRITE CERTIFICATION

**This is the exact current next action.**

Current verdict:

`MISSION 4.2 — READY FOR LIVE CERTIFICATION / AWAITING GEV APPROVAL`

No live write certification has yet been performed.

Prepared action:

`ACT-ef5fb6b5d0`

## Pending approval card

**READY FOR YOUR APPROVAL**

WHAT:
`tasks.create` — LIVE WRITE CERTIFICATION, harmless test task owned by Գև in `Tasks.xlsx`

WHERE:
`INT-TASKS` — Command-center task register, `Tasks.xlsx`

TARGET:
new task, expected id `16`

IMPORTANT PARAMETERS:
- title: `TEST — Deputy live write certification (delete after)`
- owner: `Գև`
- status: `Չսկսված`
- due: `2026-09-12`
- comment: `Mission 4.2 live certification · harmless · Gev-approved · cleanup = close/remove this row`

RISK:
`R1`

Authority:
`EXECUTE_EXTERNAL`

EXPECTED EFFECT:
Exactly ONE new row in `Tasks.xlsx`, id `16`, with exactly the presented fields.

VERIFY:
Independent read-back of:
- id
- title
- owner
- deadline
- status

**Nothing has been changed yet.**

## Current approval state
Gev has **NOT YET approved** this certification write at handoff.

Do not execute until Gev explicitly approves this exact pending action.

If Gev gives clear `GO` / `OK` / `Արա` / `Հաստատում եմ` referring to this card:

1. execute exactly the prepared task creation
2. read back independently
3. verify exact fields
4. record certification evidence
5. update capability/certification truth
6. report result
7. present cleanup as a **separate approval card**
8. wait for cleanup approval

Do **not** auto-clean row 16.

Cleanup is a second mutation and needs separate approval.

---

# 23. MISSION 4.2 FINAL CLOSURE

If live task creation is VERIFIED, Mission 4.2 can reach final closure after:
- live write certification recorded
- capability status updated
- cleanup handled under separate approval if desired
- full release/validation still green
- current main synchronized
- no unapproved mutation occurred

Expected final verdict:

`MISSION 4.2 — PASS`

Do not claim PASS without repo/runtime evidence.

---

# 24. NEXT PHASE AFTER MISSION 4.2

## Mission 5 — Live Sales & Operations Intelligence

Goal:
Deputy turns live business data into management intelligence.

Desired outputs:
- what changed
- why it matters
- probable cause
- impact
- recommended action
- owner
- deadline
- what Gev needs to do

Target topics:
- sales target vs actual
- forecast
- funnel/conversion
- pipeline stagnation
- lost opportunities
- churn
- retention
- revenue leakage
- backlog
- SLA
- failed/reworked operations
- complaints
- capacity
- people bottlenecks
- cross-functional blockers
- overdue commitments
- pending decisions

Preferred analysis:

`CAUSE → IMPACT → ACTION → OWNER → DEADLINE`

## Later — Proactive Management
Once intelligence is reliable:
- morning brief
- exception check
- EOD control
- weekly Sales & Ops review
- monthly review
- proactive open-loop surfacing
- escalation preparation
- controlled next-action preparation

Even then, current approval law remains until Gev explicitly changes it.

---

# 25. TARGET DEPUTY CAPABILITIES

## Executive control
- priorities
- deadlines
- waiting-for
- commitments
- decisions
- open loops
- risks
- follow-ups

## Sales
- targets
- pipeline
- forecast
- conversion
- churn
- retention
- revenue leakage
- pricing/promo analysis
- anomalies
- channel performance

## Operations
- workload
- backlog
- aging
- SLA
- fulfillment/install
- failed jobs
- rework
- complaints
- capacity
- handoffs
- bottlenecks

## People
- ownership
- performance
- workload/capacity
- recurring mistakes
- coaching/training
- accountability

Root-cause classes should distinguish:
- PERSON
- PROCESS
- SYSTEM
- POLICY
- CAPACITY
- TRAINING
- MANAGEMENT
- INCENTIVE
- DATA

## Business memory
Important categories:
- People
- Decisions
- Commitments
- Exceptions
- Projects
- Processes
- KPIs
- Accounts when appropriate
- Lessons

Memory never outranks current authoritative truth.

---

# 26. GEV’S INFORMATION STYLE

Default executive answer:

1. WHAT HAPPENED?
2. WHY DOES IT MATTER?
3. WHAT CAUSED IT?
4. WHAT DO YOU RECOMMEND?
5. WHO OWNS IT?
6. BY WHEN?
7. WHAT DOES GEV NEED TO DO?

Conclusion first.

Prioritize by:
- business impact
- urgency
- customer impact
- revenue impact
- operational risk
- dependencies
- reversibility

Avoid management fluff.

---

# 27. DURABLE GOVERNANCE PRINCIPLES

## One source / one primitive
Do not duplicate canonical truth unnecessarily.

## One accountable owner
Do not split accountability across multiple owners.

## Fail closed
Missing:
- authority
- approval
- capability
- source
- verification
- required input

must not become guessed success.

## Evidence-based completion
Attempt ≠ completion.

## Current truth vs history
Archive/history does not override current authoritative source.

## No invented capability
If Bitrix is not configured, MikroBILL write is unavailable, or Outlook session is absent, say so.

## No silent contradiction
Material conflict between authoritative sources must be surfaced.

## No blind retry
Unknown remote outcome → reconcile first.

## No action expansion
Approval for A does not approve B.

## Rollback is a mutation
Compensating writes need approval unless already explicitly included.

---

# 28. MACHINE-SPECIFIC REQUIREMENTS

Mission 4.1 reported:

1. `~/.command-center/recovery.key`
   - Gev keeps copy in password manager
   - needed for encrypted `.secure` recovery

2. Outlook classic session
   - new machine stays not-connected until Outlook signed in

3. Runtime prerequisites
   - Git
   - GPG
   - Python ≥ 3.11 reported historically; verify current bootstrap/lock

4. `~/.claude/projects`
   - machine-local Claude memory
   - not canonical truth

5. `_TEMP_WORK_COLLECTION/`
   - temporary / awaiting review historically
   - ignored
   - not canonical unless later promoted

---

# 29. SECURITY / CLASSIFICATION

Mission 4.1 scanner model:
- `RESTRICTED` = blocked
- `CONFIDENTIAL` = awareness/versionable by owner policy

RESTRICTED examples:
- tokens
- keys
- `.env` secrets
- connection strings
- webhook codes
- recovery-key literal

Mission 4.1 reported:
- 19 commits scanned
- 1012 blobs
- RESTRICTED = 0

GitHub push protection once caught AWS-shaped test fixture.
Fixture strategy was changed to runtime assembly.

Repo is PUBLIC by Gev decision.

**Public repo does not mean real secrets may be committed.**

---

# 30. SEALED VS PENDING

## SEALED / DO NOT REOPEN WITHOUT A REAL REASON
- product name = `Command-center`
- agent name = `Deputy`
- role = AI Chief of Staff for Sales & Operations
- GitHub SST = `ohanyan88-cmd/Command-center`
- branch = `main`
- Skill System architecture
- workspace architecture
- business-model/provenance approach
- read integration layer
- durability/recovery model
- mandatory Gev approval law
- `AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE`
- one canonical Action Runtime
- public repo risk accepted by Gev

## PENDING
- Mission 4.2 live write certification
- first `VERIFIED_WRITE`
- cleanup of certification task after creation
- Mission 4.2 final PASS

## FUTURE
- Mission 5 intelligence
- broader proactive management
- more write certifications
- Bitrix24 live write once configured
- MikroBILL writes only if safely modeled/certified
- any autonomy increase only by explicit owner decision

---

# 31. DO NOT DO

The next chat must NOT:
- rename Deputy
- rename Command-center
- create competing workspace
- create second Skill System
- create second authority system
- create second approval system
- create second state system
- bypass `approval_rule.json`
- assume `CONNECTED` means `VERIFIED_WRITE`
- claim Mission 4.2 PASS before live certification
- execute `ACT-ef5fb6b5d0` without approval
- auto-clean certification task
- grant autonomy because write is low-risk
- use old 61-skill count as current
- trust old SHA without verifying GitHub
- assume Bitrix24 configured
- assume MikroBILL write available
- conflate local draft with Outlook provider draft
- treat API 200 as completion
- retry unknown writes blindly
- silently overwrite cross-system divergence
- let tests/evals touch real Tasks.xlsx or Outlook
- reopen public/private decision without new owner direction
- import unrelated BRO/GAAhex/OS source-of-truth rules

---

# 32. IMPORTANT REPO CHECKPOINTS

- `c3ffda1b127fd5c42b18d2869487e7591f76bdca`
  - Mission 4 eyes

- `23b592f47d7d2458ee53a5ccea40cdbfdf8e276e`
  - Mission 4 audit remediation

- `5c12dc7c902069582fc3624df9e0cbe4996f3e18`
  - Mission 4.1 durability/recovery implementation

- `2d8cc9a25485ed3b45ace6f19ef5ce85a682351f`
  - Mission 4.1 checksum-refresh final baseline

- `cb89ab7925532f17aea2bbec0044485fd23accb8`
  - mandatory Gev approval law

- `f073b216f7f28287c51fcc2711c1629ca52838ef`
  - Mission 4.2 Controlled Hands implementation

- `358d4d7d35b5be2aade393e707088fa7d837aafa`
  - durable checksum refresh

- `6ddea12fac7fe3ca67f64fb72f904669d220eee0`
  - Mission 4.2 release: 63 skills, 317 tests, 95 evals

- `f2177bc0a499f1f25c11e00d6eb65e7c91487570`
  - Merge Mission 4.2 — Controlled Hands PR #1
  - **current verified main at handoff**

---

# 33. NEW-CHAT RESUME ALGORITHM

## Step 1
Identify project:
`Command-center / Deputy`

## Step 2
Read this file before making architectural claims.

## Step 3
Verify GitHub:
- repo
- default branch
- current `main`
- latest commit
- whether it advanced beyond `f2177bc...`

If advanced, inspect why.

## Step 4
Determine mission state.

Unless new repo evidence changes it:

`MISSION 4.2 — READY FOR LIVE CERTIFICATION / AWAITING GEV APPROVAL`

## Step 5
Respect approval boundary.

Do not execute pending certification without Gev’s explicit approval.

## Step 6
If Gev approves the pending action:
- exact write only
- one harmless task
- read back
- verify
- certify
- report
- propose cleanup separately
- wait for cleanup approval
- re-run release/validation as needed
- verify current main
- close Mission 4.2 only on evidence

## Step 7
After Mission 4.2 PASS:
move to Mission 5 — Live Sales & Operations Intelligence.

Do not jump ahead unless Gev explicitly chooses to postpone certification.

---

# 34. SHORT CURRENT-STATE SUMMARY

As of this handoff:

- `Command-center` is canonical workspace.
- `Deputy` is Gev’s AI Chief of Staff for Sales & Operations.
- SST = `ohanyan88-cmd/Command-center`, `main`.
- Current verified main = `f2177bc0a499f1f25c11e00d6eb65e7c91487570`.
- Mission 1 Skill System established.
- Mission 2 workspace architecture established.
- Mission 3 business model exists and is used.
- Mission 4 read-only eyes exist.
- Mission 4.1 durability/recovery = PASS.
- PUBLIC repo risk explicitly accepted by Gev.
- Mandatory approval law:
  `AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE`.
- Mission 4.2 Controlled Hands implemented and merged.
- Quality:
  - 317/317 tests
  - 95/95 evals
  - 63 certified skills
  - action_runtime L3
- No write operation is yet `VERIFIED_WRITE`.
- Mission 4.2 waits at first live certification gate.
- Pending action = `ACT-ef5fb6b5d0`.
- Gev has not yet approved it.
- Next decision: approve / change / postpone that exact certification action.
- After successful certification and closure → Mission 5.

---

# 35. FINAL CONTINUITY RULE

The purpose of this file is to eliminate:

- “start over”
- “explain everything again”
- “wrong old context”
- “wrong repo”
- “wrong mission”
- “we already decided this”

For this Project:

**Current GitHub `main` is implementation truth.**  
**This file is continuity truth.**  
**Gev is the owner and final authority.**  
**No real business write occurs without Gev’s explicit approval.**

When unsure:

**VERIFY FIRST. DO NOT INVENT. DO NOT REGRESS SEALED ARCHITECTURE. DO NOT REOPEN SETTLED DECISIONS WITHOUT EVIDENCE.**
