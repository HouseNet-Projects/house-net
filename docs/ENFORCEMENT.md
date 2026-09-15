# Enforcement

## English

| Layer | What it does | What it cannot claim |
| --- | --- | --- |
| Execution-client global and repository instructions | Maps each fresh session to current policy and preflight | Behavioral guidance is not an unbypassable hook |
| Local preflight | Nonzero exit on wrong identity, integrity/registration failure, wrong remote, Git baseline drift, dirty or stale checkout | Does not automatically intercept every direct tool invocation |
| Optional provider-adapter maps | Provides the canonical lookup procedure | provider-specific local client is not installed in this WSL; no local managed hooks installed |
| GitHub CI | Runs schema, policy, coverage, content/workflow validation, tests and syntax checks | A green check is not owner approval; CI alone cannot prevent merges |
| Reusable gate | Executes pinned trusted validator and registry against caller content | Must be explicitly installed in a future approved repository; not globally automatic |
| GitHub server protection | Plan-dependent main-branch merge restrictions | Unsupported private-plan features must remain identified as gaps |

### Approval boundary

Creation, configuration, reclassification, production automation and exact destructive actions require owner authority. Policy files and templates do not create authorization. Existing authorization remains valid for the action it covers; do not repeatedly ask for approval of the same work.

### Content validation

Enforced tripwires include missing registration, wrong classification/namespace/version/commit, incomplete rule applicability, unapproved registration, missing applicable files, malformed JSON/YAML, duplicate keys, missing CI for Class A, broad workflow write permissions, unjustified job write permissions, unreviewed external action references, mutable remote references, privileged PR triggers, direct event interpolation in shell, inherited reusable secrets, symlink escapes and recognizable private keys/GitHub tokens in tracked content.

Remote SHA pinning is this critical gate's concrete baseline. The owner policy's preference is not silently made universal: a future justified exception requires a reviewed design and a validator change before adoption. Arbitrary shell scripts, encrypted data, unknown secret formats and real-world approval intent are not fully machine-verifiable.

### Recovery

Do not auto-fix a failed preflight. Report the failing check. For an authorized control-plane update, inspect changes and use a clean fast-forward to approved remote `main`; never reset away local work. During an explicitly approved implementation task, the working tree will be dirty; validate offline before committing and run the full preflight once synchronized. Roll back software through a reviewed revert PR, not force push. Never rotate secrets or rewrite history automatically.

### Live verification

The installation's observed settings, server capability response and session evidence are recorded in [audit/VERIFICATION.md](../audit/VERIFICATION.md). Current account UI-only defaults remain outside this repository's authority and were not changed.

---

## Հայերեն

# Enforcement

Execution client-ի և պահոցի instruction-ները ուղղորդում են ընթացիկ policy-ին, բայց չեն հանդիսանում շրջանցման ենթակա hard hook։ Local preflight-ը non-zero է վերադարձնում սխալ identity-ի, remote-ի, integrity-ի, registry-ի, Git baseline-ի կամ հնացած checkout-ի դեպքում։ provider-specific local client-ը այս WSL-ում տեղադրված չէ։

GitHub CI-ն ստուգում է schema-ները, policy coverage-ը, content-ը, workflow-ները, syntax-ը և tests-ը։ Reusable gate-ը կիրառելի է միայն ապագայում հաստատված պահոցներում և պահանջում է pinned trusted revision։ GitHub server protection-ը սահմանափակված է ընթացիկ personal private plan-ով, ուստի անհասանելի հնարավորությունները չեն ներկայացվում որպես enforced։

Պարտադիր հաստատումները ներառում են պահոցի ստեղծումը, configuration-ը, reclassification-ը, production automation-ը և հստակ destructive գործողությունները։ Content validator-ը ստուգում է registration-ը, namespace-ը, դասը, version-ը, commit-ը, required files-ը, workflow permissions-ը և human-facing EN + HY պայմանագիրը։ Failed preflight-ը չի auto-fix արվում․ պետք է հաղորդել պատճառը և օգտագործել հաստատված PR կամ revert։
