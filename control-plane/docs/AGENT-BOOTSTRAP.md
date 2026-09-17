# Agent bootstrap

## English

### Execution clients in this WSL

Detected installation: installed execution-client CLI, CLI `0.154.0`. execution-client home variable was unset; the installed CLI and its existing configuration resolve the default home to `/home/gevorg/.execution-client`. No global or override instruction file existed before installation. Existing client configuration contained `projects` and `tui` configuration and is preserved.

The installer places a short delimited map in global agent instruction file and a minimal supported `developer_instructions` map in client configuration. Neither duplicates machine policy. Both direct fresh sessions to load `/home/gevorg/house-net-control-plane`, run preflight, inspect current manifest/authority/classes and stop on mandatory failure. Developer instructions have no hardcoded policy version: it is read from the current manifest.

Idempotent installation logic lives in bootstrap installer. The resolved home is passed explicitly; the installer refuses a conflicting override rather than overwriting it. Unrelated instructions and TOML values are preserved and verified.

Verification uses the installed CLI's fresh-process instruction inspection in a fresh process outside the repository to inspect the actual model-visible instruction chain, plus a clean read-only fresh-process read-only probe probe where possible. Results belong in the audit record. No claim is made that instructions are an unbypassable deterministic hook.

### provider-specific local client

local execution-client detection found no provider-specific local client in this WSL. No installation or managed `/etc/local-client-settings` changes are made.

**LOCAL EXECUTION ENFORCEMENT: PENDING — SECONDARY LOCAL CLIENT NOT PRESENT IN THIS WSL.**

Repository provider adapter instruction file and `templates/provider-adapter.md` are ready. If the owner later installs provider-specific local client, a separately reviewed installation should use the then-supported Linux managed instruction/settings mechanism, a SessionStart context hook and a fail-closed UserPromptSubmit gate. SessionStart must not be described as a hard block. Verify both passing and failing prompts before claiming enforcement.

### Future repositories

Read `house-net-control.json`, resolve the trusted control plane, run its current preflight, then inspect classification and applicable rules. Validate the target's lock against the trusted registry. Never copy the full policy into AGENTS.md or provider-adapter.md. Repository templates contain placeholders and confer no creation approval.

### References

- [Agent instruction discovery](https://docs.github.com/en/actions)
- [Agent configuration reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## Հայերեն

# Գործակալի bootstrap

Execution client-ի global քարտեզը և repository instructions-ը յուրաքանչյուր նոր session ուղղորդում են դեպի `/home/gevorg/house-net-control-plane`, ընթացիկ manifest-ը և `bin/housenet-preflight --json`։ Policy-ի ամբողջ տեքստը չի պատճենվում AGENTS.md-ում։ Եթե mandatory preflight-ը ձախողվի, գործակալը պետք է կանգ առնի և հաղորդի պատճառը։

Մարդկանց համար նախատեսված փաստաթղթերը պետք է լինեն English + Հայերեն։ Machine, code և agent bootstrap ֆայլերը կարող են մնալ English-only։ provider-specific local client-ը այս WSL-ում չկա, ուստի managed hook-երը սպասման մեջ են։
