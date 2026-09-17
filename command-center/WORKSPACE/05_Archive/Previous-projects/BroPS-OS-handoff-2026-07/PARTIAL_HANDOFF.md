# OS partial implementation handoff — 2026-07-26

## Status

**PARTIAL / NOT READY TO MERGE.** Work was stopped at the Owner's request and packaged exactly as-is. No GitHub write, push, PR update, or merge was performed.

## Base

- Intended canonical design base: `6ebeca88627640eef8effe576b3d388417cb4949` (3b-1B rev 26, docs-only successor).
- Local code tree was created from the byte-valid rev-25 archive at `bcd24fe0d5af0a33fc72ca7eaee35b8f1f12be1a` because the uploaded rev-26 archive was corrupted by PowerShell text redirection.
- Rev 26 changes only five documentation files and no code. The implementation was written against the rev-26 constants and closures supplied by the Owner, but the `source/` tree still contains the rev-25 canonical document text. Claude must first apply this implementation onto the live rev-26 branch, not replace live canonical docs with the copies in this ZIP.

## Implemented in this partial package

- New governed 3b-1B protocol family and schemas, kept separate from frozen 3b-1A protocols.
- Challenge authority store/client/service with rev-26 lifecycle constants, idempotency, expiry, retention, quotas, retry behavior, and exact challenge replay.
- Governed supervisor/signing path, model identity formula `cfg-sha256:<generation_config_sha256>`, execution allowlist, output pull lifecycle, and bounded diagnostics.
- Sidecar governed submit/output-read routing.
- Desktop-side Rust modules for strict JSON, manifest handling, governed receipt verification, migration plumbing, and governed command integration.
- Evidence-store group-write hardening.
- Immutable per-sequence staging chunk files with reconciliation/corruption handling.
- New Python tests and contract schemas.

## Verified here

- `63 passed in 5.89s` for the selected governed/bridge regression set. See `logs/python_tests.txt`.
- Python `compileall` over `engine/runtime`, `engine/tools`, and `bridge`: GREEN.
- `tools/check_coordination.py`: GREEN.
- `tools/check_capabilities.py`: GREEN, 66 commands consistent.
- `git diff --check`: GREEN.

## Not verified / known remaining work

1. Rust/Tauri compile and Rust unit tests were not run because this sandbox did not have a usable Rust toolchain.
2. Frontend npm typecheck/build/tests were not run because `node_modules` were unavailable and dependency installation was not completed.
3. No exact-head GitHub CI was run for these changes.
4. The implementation has not received a full zero-trust code audit.
5. Rev-26 canonical docs must be preserved from live GitHub when applying the patch.
6. This package is focused on the 3b-1B trust-chain implementation. It is not the promised full Phase 0–10 production application completion.

## Safe apply workflow for Claude

1. Fetch the live `feat/wave-3b1-isolated-signer` branch and verify HEAD is at or descends from `6ebeca88627640eef8effe576b3d388417cb4949`.
2. Create a new worktree/branch from that live HEAD.
3. Apply `_HANDOFF/IMPLEMENTATION.patch` with `git apply --3way`.
4. Resolve conflicts in favor of the live rev-26 canonical docs. Do not copy the five older documentation files from `source/` over GitHub.
5. Run formatting, Rust tests/check/clippy, frontend typecheck/build/tests, all Python/engine/bridge tests, isolation proof, and full CI.
6. Perform a consolidated zero-trust audit and remediate all findings before requesting merge approval.
7. Do not merge without Gev's explicit exact-head approval.
