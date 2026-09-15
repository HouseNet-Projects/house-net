# Installation verification

## English

This file records observed evidence, not policy authority. Final live verification is completed after the initial executable baseline is published.

- Source SHA-256 verified: `a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491`.
- Namespace and account: `HouseNet-Projects`.
- Policy snapshot: `72bb4b4bded5ffda7bf6f99a4a7f4fbccb07a871`.
- Policy version: `1.0.0`; source coverage: all 30 numbered sections; 43 unique rules.
- Claude Code absent in this WSL; managed hooks pending.
- Codex bootstrap installed at `/home/gevorg/.codex/AGENTS.md` and supported `developer_instructions` in `/home/gevorg/.codex/config.toml`; the installer was run twice and the second run was idempotent. `codex debug prompt-input` in a fresh process showed the managed bootstrap, control-plane path, identity requirement, owner-approval rule and manifest lookup. A separate `codex exec` probe reached the manifest read and reported policy version `1.0.0`, then stopped when the Codex service usage limit was reached; no mutation occurred.
- Claude Code is absent from this WSL; local managed Claude hooks are pending and were not installed.
- Repository settings verified: private, `main`, squash-only merges, auto-merge off, merged-branch deletion on; Actions selected policy with `actions/*` and `HouseNet-Projects/*`, full-SHA pinning required, read-only default token, PR creation/approval disabled, same-owner private workflow access, and 30-day artifact/log retention.
- Dependabot alerts/security updates are enabled. The first control-plane CI run for commit `4dc9575acd3af9ff0b17f109fe08518c980d7f3e` passed; subsequent CI checks also passed.
- GitHub rejected private personal-account branch protection with: `Upgrade to GitHub Pro or make this repository public`. This is the documented private-plan server-side protection gap; no fake protection was configured.

---

## Հայերեն

# Տեղադրման ստուգում

Այս գրառումը փաստում է դիտարկված ապացույցը, ոչ թե policy authority-ն։ Սկզբնական source SHA-256-ը պահպանվում է՝ `a15b6b22aeecc7beaaf2f13e9de20e45b1a49be24c6ba280a5b3ac364f034491`։ Identity-ն և namespace-ը `HouseNet-Projects` են։ Codex bootstrap-ը տեղադրված է `/home/gevorg/.codex/AGENTS.md`-ում։ Claude Code-ը այս WSL-ում բացակայում է, ուստի managed hook-երը սպասման մեջ են։

GitHub-ը ընթացիկ personal private plan-ով մերժել է branch protection-ը՝ պահանջելով Pro կամ public repository։ Սա server-side gap է, և կեղծ protection չի ստեղծվել։
