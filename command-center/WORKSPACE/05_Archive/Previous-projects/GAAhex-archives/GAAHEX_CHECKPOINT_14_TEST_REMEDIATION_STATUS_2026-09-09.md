# GAAHEX Master Cleanup — Checkpoint #14 (FULL TEST REMEDIATION)

Date: 2026-09-09
Baseline: Checkpoint #13 FULL final-source snapshot.
Trigger: user-run dependency-backed verification reported backend `25 failed / 1878 passed / 2 errors` and frontend typecheck `3 errors`.
Scope: fix the reported failures without weakening production fail-closed contracts; harden tests/tooling so the same failure classes cannot silently recur.

## Baseline preservation

- Checkpoint #13 release manifest contained **1738 tracked source files**.
- Before sealing #14: **0 Checkpoint #13 files are missing**.
- Added source files: `gx26090904_ticket_customer_ref.py`, `deploy/postgres/dev-app-role.sql`, and `tools/test_checkpoint14_stdlib.py`.
- No Git/GitLab/GitHub metadata is required for release identity; the FULL archive remains the authority.

## Reported issues remediated

### 1. Mock payment IDs collided

`uuid7().hex[:8]` used the timestamp-heavy UUIDv7 prefix and could collide under rapid calls. The mock gateway now uses `secrets.token_hex(4)` for 8-hex synthetic suffixes. A dependency-free runtime probe generated 5,000 rapid IDs with 5,000 unique values, and payment protocol tests now pin rapid uniqueness.

### 2. Mock card expiry ignored requested metadata

The mock gateway now accepts deterministic `__exp_MM_YYYY` token metadata and stores it in `VaultResult`; Stage-8 test helpers now encode their requested month/year instead of discarding them. This makes the expired-payment-method branch executable.

### 3. GXL corpus parsed named guards as expressions

Named transition-guard registry keys (for example `conversion:lead_order_exists`) are explicitly excluded from GXL-expression corpus validation. Both corpus tests now use the same `NAMED_GUARDS` boundary.

### 4. Production deploy-contract tests leaked global settings

- production helper fixtures explicitly disable unrelated hosted checkout unless that test is about payments;
- an autouse per-test snapshot/restore protects the module-level Pydantic `settings` singleton from order-dependent mutation leakage;
- the CI/test RLS role bootstrap now repairs an existing NOLOGIN `gaahex_app` role by adding LOGIN/password in the test environment.

### 5. OLT required-state authority was inconsistent

`feature_gate.is_required()` is now the single required-policy authority consumed by install-board runtime and tests. The stale test that expected required+unmapped OLT provisioning to fall back to dev mode now asserts fail-closed `FeatureDisabledError`, no driver call and no false activation.

### 6. Outbound happy-path tests had no provider

Production messaging remains fail-closed. Tests that claim an email/SMS happy path now explicitly opt into deterministic in-process test transports: a fake SMTP gateway and the registered `test_operator` SMS adapter. No production mock fallback was added.

### 7. AI chat fail-closed boundary was too broad

No-provider `/api/ai/chat` now returns a deterministic **answer-only local** response. It never proposes or executes actions. LLM-backed summarize/ask surfaces remain 503 without a provider. Router documentation now states this split accurately.

### 8. Ticket entity field gap + noisy ownership diagnostics

- baseline ticket EntityDef now includes a `customer` reference field;
- migration `gx26090904` backfills the field on existing databases;
- the ownership seeder now distinguishes expected first-class typed records (INFO) from genuine missing/unimplemented registry records (WARNING), instead of conflating both in one 11-name warning.

This intentionally does **not** fabricate EntityDefs for features that do not have a real implementation. Genuine gaps such as an unimplemented `Announcement`/`AI Insight` registry surface remain visible rather than being hidden for a green log.

### 9. Windows-only test failures

- FreeRADIUS protocol construction is skipped where Python lacks `select.poll()` (Windows limitation of `pyrad`), not reported as a product failure;
- oversized logo-validation parametrization uses short pytest IDs, avoiding the Windows 32,767-character environment-variable limit.

### 10. Frontend typecheck contract

- TypeScript library surface updated to ES2022 for `Array.at` / `String.replaceAll` while keeping the emitted target unchanged;
- `ChannelAccountInput` now carries optional `config`, matching the backend tenant-channel-account JSON contract.

### 11. Local RLS setup gap

Added `deploy/postgres/dev-app-role.sql` and README instructions for the local/test-only `gaahex_app/gaahex_app` LOGIN role. Production migration remains NOLOGIN/password-free and production still uses `sync-app-role.sh` + deployment secret.

### 12. `gate:lint-changed` vacuous pass outside Git

The gate now returns non-zero with explicit **UNVERIFIED** when source has no Git worktree or the base diff cannot be resolved. A FULL checkpoint ZIP therefore cannot falsely report “no changed files” as a successful lint verification. In repository CI, the normal Git-backed gate can still run against a verified base.

## Additional hardening from this pass

- `.gitlab-ci.yml` now runs the #14 dependency-free contract suite in addition to prior source gates.
- Payment protocol tests directly pin rapid mock-token uniqueness and requested-expiry behavior.
- Ownership boot diagnostics no longer classify known first-class typed tables as registry warnings.

## Verification completed here

- Checkpoint #14 dependency-free source contracts: **14 / 14 PASS**.
- Existing Checkpoint #13 final-source contracts: **17 / 17 PASS**.
- Production-certifier stdlib suite: **4 / 4 PASS**.
- Release identity/cutover stdlib suite: **5 / 5 PASS**.
- Backup/operations stdlib suite: **7 / 7 PASS**.
- Combined dependency-free regression matrix: **47 / 47 PASS**.
- Public route contract: PASS.
- Architecture drift: PASS; existing ratchet debt did not increase.
- Tenant-filter analyzer: PASS — 0 new violations across 121 guarded models.
- Python compile/AST: PASS.
- TypeScript/TSX syntax parse: **332 / 332 PASS**.
- Python internal import integrity: **1483 checked / 0 dangling**.
- Frontend relative import integrity: **1514 checked / 0 dangling**.
- Alembic graph: **131 revisions / 1 root / 1 head / 0 missing parent**, head `gx26090904`.
- Production YAML and shell syntax: PASS.
- Mock ID helper runtime probe: **5,000 calls / 5,000 unique**, correct 8-hex format.
- Mock expiry helper runtime probe: requested expiry, default expiry and invalid-month fallback behave as designed.
- `gate:lint-changed` on this non-Git FULL snapshot: **UNVERIFIED with exit 2**, which is the intended non-vacuous result.

## Dependency-backed execution boundary

This environment cannot honestly rerun the user's full backend/frontend suites:

- backend pytest stops during conftest import because `uuid_utils` is not installed here; other full runtime dependencies are also absent;
- frontend `node_modules` is absent and package installation is network-blocked; local `npm run typecheck` therefore fails on missing React/type packages rather than the three source errors reported by the user;
- the available Node runtime is 22.16, while the project CI/runtime contract uses Node 24.

Therefore **the user-run 25/1878/2 + 3-error suite must be rerun in the complete environment** to produce the dependency-backed green proof. This checkpoint fixes the reported root causes and hardens their contracts, but does not invent a full-suite PASS from an environment that cannot execute it.

## Verdict

Checkpoint #14 is the FULL remediation snapshot for the concrete failures discovered after #13. It preserves the complete #13 source baseline, fixes the reproducible source/test/tooling defects without weakening production fail-closed behavior, and seals the fixes with dependency-free regression contracts.

Production/cutover remains gated on a clean dependency-backed rerun and target-host certification.
