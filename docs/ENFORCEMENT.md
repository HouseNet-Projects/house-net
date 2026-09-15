# Enforcement

| Layer | What it does | What it cannot claim |
| --- | --- | --- |
| Codex global and repository instructions | Maps each fresh session to current policy and preflight | Behavioral guidance is not an unbypassable hook |
| Local preflight | Nonzero exit on wrong identity, integrity/registration failure, wrong remote, Git baseline drift, dirty or stale checkout | Does not automatically intercept every direct tool invocation |
| Claude repository maps | Provides the canonical lookup procedure | Claude Code is not installed in this WSL; no local managed hooks installed |
| GitHub CI | Runs schema, policy, coverage, content/workflow validation, tests and syntax checks | A green check is not owner approval; CI alone cannot prevent merges |
| Reusable gate | Executes pinned trusted validator and registry against caller content | Must be explicitly installed in a future approved repository; not globally automatic |
| GitHub server protection | Plan-dependent main-branch merge restrictions | Unsupported private-plan features must remain identified as gaps |

## Approval boundary

Creation, configuration, reclassification, production automation and exact destructive actions require owner authority. Policy files and templates do not create authorization. Existing authorization remains valid for the action it covers; do not repeatedly ask for approval of the same work.

## Content validation

Enforced tripwires include missing registration, wrong classification/namespace/version/commit, incomplete rule applicability, unapproved registration, missing applicable files, malformed JSON/YAML, duplicate keys, missing CI for Class A, broad workflow write permissions, unjustified job write permissions, unreviewed external action references, mutable remote references, privileged PR triggers, direct event interpolation in shell, inherited reusable secrets, symlink escapes and recognizable private keys/GitHub tokens in tracked content.

Remote SHA pinning is this critical gate's concrete baseline. The owner policy's preference is not silently made universal: a future justified exception requires a reviewed design and a validator change before adoption. Arbitrary shell scripts, encrypted data, unknown secret formats and real-world approval intent are not fully machine-verifiable.

## Recovery

Do not auto-fix a failed preflight. Report the failing check. For an authorized control-plane update, inspect changes and use a clean fast-forward to approved remote `main`; never reset away local work. During an explicitly approved implementation task, the working tree will be dirty; validate offline before committing and run the full preflight once synchronized. Roll back software through a reviewed revert PR, not force push. Never rotate secrets or rewrite history automatically.

## Live verification

The installation's observed settings, server capability response and session evidence are recorded in [audit/VERIFICATION.md](../audit/VERIFICATION.md). Current account UI-only defaults remain outside this repository's authority and were not changed.
