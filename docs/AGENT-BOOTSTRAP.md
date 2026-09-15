# Agent bootstrap

## Codex in this WSL

Detected installation: `/usr/local/bin/codex`, CLI `0.154.0`. `CODEX_HOME` was unset; the installed CLI and its existing configuration resolve the default home to `/home/gevorg/.codex`. No global or override instruction file existed before installation. Existing `config.toml` contained `projects` and `tui` configuration and is preserved.

The installer places a short delimited map in `/home/gevorg/.codex/AGENTS.md` and a minimal supported `developer_instructions` map in `config.toml`. Neither duplicates machine policy. Both direct fresh sessions to load `/home/gevorg/house-net-control-plane`, run preflight, inspect current manifest/authority/classes and stop on mandatory failure. Developer instructions have no hardcoded policy version: it is read from the current manifest.

Idempotent installation logic lives in `bin/install-codex-bootstrap`. The resolved home is passed explicitly; the installer refuses a conflicting override rather than overwriting it. Unrelated instructions and TOML values are preserved and verified.

Verification uses the installed CLI's `codex debug prompt-input` in a fresh process outside the repository to inspect the actual model-visible instruction chain, plus a clean read-only `codex exec` probe where possible. Results belong in the audit record. No claim is made that instructions are an unbypassable deterministic hook.

## Claude Code

`command -v claude` found no Claude Code in this WSL. No installation or managed `/etc/claude-code` changes are made.

**CLAUDE LOCAL ENFORCEMENT: PENDING — CLAUDE CODE NOT PRESENT IN THIS WSL.**

Repository `CLAUDE.md` and `templates/CLAUDE.md` are ready. If the owner later installs Claude Code, a separately reviewed installation should use the then-supported Linux managed instruction/settings mechanism, a SessionStart context hook and a fail-closed UserPromptSubmit gate. SessionStart must not be described as a hard block. Verify both passing and failing prompts before claiming enforcement.

## Future repositories

Read `house-net-control.json`, resolve the trusted control plane, run its current preflight, then inspect classification and applicable rules. Validate the target's lock against the trusted registry. Never copy the full policy into AGENTS.md or CLAUDE.md. Repository templates contain placeholders and confer no creation approval.

## References

- [Official Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
