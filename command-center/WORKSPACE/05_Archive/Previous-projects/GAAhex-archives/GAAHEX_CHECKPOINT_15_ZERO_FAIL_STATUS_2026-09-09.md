# GAAHEX Master Cleanup — Checkpoint #15 (FULL ZERO-FAIL GATE HARDENING)

Date: 2026-09-09
Baseline: Checkpoint #14 FULL test-remediation snapshot.
Scope: preserve every #14 release file; make the dependency-backed “zero real failures” proof a single deterministic, fail-closed command; remove runtime-version ambiguity before the page-by-page product audit.

## Baseline preservation

- Checkpoint #14 release manifest contained **1741 tracked source files**.
- Before sealing #15: **0 Checkpoint #14 files are missing**.
- New release files: `tools/zero_fail_gate.py`, `tools/test_checkpoint15_zero_fail.py`, `docs/runbooks/ZERO-FAIL-TEST-GATE.md`, and strict Node-runtime `.npmrc` files for both frontends.
- Existing source changes are limited to the two frontend package manifests/lockfiles, README verification/setup guidance, and the active source CI contract/comment.
- Release identity remains FULL-snapshot based and does not require Git/GitLab/GitHub metadata.

## What #15 changes

### 1. One canonical zero-fail command

`python tools/zero_fail_gate.py`

The gate has three non-overlapping outcomes:

- exit `0` — **ZERO-FAIL PASS**: every requested dependency-free and dependency-backed gate executed and passed;
- exit `1` — **FAIL**: a gate executed and failed;
- exit `2` — **BLOCKED**: the environment cannot execute the proof. Missing dependencies, wrong runtime versions, missing DB URLs/services or missing frontend installs are never converted into a pass.

### 2. The full gate covers the actual product test surfaces

After source contracts pass, full mode requires and executes:

1. backend `app.main` import/boot contract;
2. complete backend pytest suite;
3. migration-backed invariants;
4. admin frontend TypeScript typecheck;
5. admin frontend unit tests;
6. admin frontend production build;
7. customer portal unit tests;
8. customer portal production build.

A failure in any item blocks the release.

### 3. Runtime version drift is fail-closed

Both frontend packages now declare Node `>=24 <25`, their package locks carry the same root engine contract, and `.npmrc` enables `engine-strict=true`.

This prevents a Node 22 workstation from silently becoming a second test authority while the delivery/runtime contract uses Node 24.

### 4. FULL checkpoint installs are explicit

The zero-fail runbook and README use `npm ci --ignore-scripts` for FULL checkpoint archives. This avoids treating the absence of Git metadata as a product failure through the Husky `prepare` hook.

### 5. Reported #14 failure classes remain permanent gates

Checkpoint #14’s regression contracts stay mandatory for:

- mock payment ID uniqueness;
- requested mock expiry metadata;
- named GXL guards;
- production settings isolation/payment-gate ordering;
- OLT fail-closed required-state authority;
- explicit messaging test transports;
- providerless local answer-only AI chat;
- ticket `customer` registry/migration parity;
- Windows-specific portability boundaries;
- ES2022/channel frontend type contract;
- local RLS role bootstrap;
- non-Git lint-changed false-green prevention.

## Verification completed in this environment

- Canonical `zero_fail_gate.py --source-only`: **ZERO-FAIL PASS**.
- Dependency-free unit/contract matrix: **52 / 52 PASS** (4 production-certifier + 5 release/cutover + 7 operations + 17 final-source + 14 checkpoint-14 + 5 checkpoint-15).
- Public route contract: PASS.
- Tenant-filter analyzer: PASS — 0 new violations / 121 guarded models.
- Architecture drift: PASS; ratchet debt did not increase.
- Complete Python compileall surface: PASS.
- #14 baseline preservation before seal: **1741 / 1741 preserved, missing 0**.

## Full dependency-backed boundary here

Running `python tools/zero_fail_gate.py` in this sandbox returns **BLOCKED / exit 2**, not PASS, because the environment does not match the required proof environment:

- Python 3.13.5 is available; the canonical backend test runtime is Python 3.12;
- Node 22 is available; the project now strictly requires Node 24;
- backend packages including `asyncpg`, `uuid_utils`, `stripe`, `pyrad`, `aiosmtplib`, `aioimaplib`, and `asyncssh` are absent;
- `frontend/node_modules` and `frontend-portal/node_modules` are absent and network installation is unavailable;
- `DATABASE_URL` / `OWNER_DATABASE_URL` and disposable PostgreSQL test services are not present.

This is an **environment BLOCK**, not a claimed application PASS or application FAIL.

## Verdict

Checkpoint #15 makes “zero real failures” an executable release contract instead of a conversational claim. All failure classes reported against #13 remain fixed and source-gated, and the constrained environment is green only for the proof it can actually execute.

The next authoritative action is to run `python tools/zero_fail_gate.py` in the complete Python-3.12 / Node-24 / PostgreSQL test environment. Only exit `0` closes the dependency-backed test phase. After that, the next program is the agreed page-by-page semantic/product audit: purpose → expected behavior → actual behavior → repair → retest.
