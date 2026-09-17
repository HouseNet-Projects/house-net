# Deputy operations / Deputy-ի շահագործում

## Start, stop, restart

Install `deploy/deputy-api.service` and `deploy/deputy-worker.service` with
systemd, then use `systemctl start|stop|restart deputy-api deputy-worker`.
The services run as `gevorg`, use the canonical virtual environment, and restart
after failures. The API binds to localhost unless an explicit deployment
configuration changes it.

Տեղադրեք `deploy/deputy-api.service` և `deploy/deputy-worker.service` systemd-ի
միջոցով, ապա օգտագործեք `systemctl start|stop|restart deputy-api deputy-worker`։
Ծառայությունները աշխատում են `gevorg` օգտատիրոջ անունից և ձախողումից հետո
վերագործարկվում են։ API-ն լռելյայն կապվում է միայն localhost-ին։

## Health and readiness / Առողջություն և պատրաստվածություն

`curl http://127.0.0.1:8765/health` checks process liveness.
`curl http://127.0.0.1:8765/readiness` checks operator readiness; optional
providers remain explicit degraded states.

## Worker and diagnosis / Worker և ախտորոշում

`./.venv/bin/python worker.py --status` shows the last cycle.
`./.venv/bin/python worker.py --once` runs one prepare-only watcher cycle.

## Backup and isolated restore / Պահուստավորում և մեկուսացված վերականգնում

`./.venv/bin/python -c 'import backup_ops; print(backup_ops.backup())'` creates a
timestamped durable backup under `.secure/backups` (configurable with
`DEPUTY_BACKUP_DIR`). `backup_ops.verify(path)` checks checksums and
`backup_ops.restore_isolated(path)` verifies a copy in a temporary state
directory without touching active production state. Keep the external recovery
key separate from the encrypted credential artifact.

`DEPUTY_OPERATOR_TOKEN` is required before binding the API beyond localhost.
Never place tokens, recovery keys or provider credentials in Git or logs.
