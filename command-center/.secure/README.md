# .secure — encrypted recovery artifacts

- `credentials.gpg` — GnuPG symmetric AES-256 archive of the active external-system credential files (`~/.command-center/integrations/*.json`). Committed. Useless without the recovery key.
- `manifest.json` — artifact version, creation time, format, per-file sha256, restore paths, expected credential names and PRESENT/ABSENT status. Never secret values.

Recovery key: `~/.command-center/recovery.key` (or `COMMAND_CENTER_RECOVERY_KEY_FILE`). Never in Git, never printed, never in audit/state. Keep a copy in a password manager or on an external device.

Commands: `python .claude/runtime/secure_recovery.py backup | verify | restore [--force] | status` — `bootstrap.py` runs restore automatically when the key is present.
