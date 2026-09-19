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

## Host-adaptable deployment / Deployment անվտանգություն

Use `deploy/install.sh` on the target Linux host. It renders service units from explicit `DEPUTY_USER`, `DEPUTY_ROOT`, `DEPUTY_VENV`, `DEPUTY_BIND`, `DEPUTY_PORT`, `DEPUTY_BACKUP_DIR`, and `DEPUTY_WORKER_INTERVAL` values; it never writes a token. Put `DEPUTY_OPERATOR_TOKEN` in the referenced root-owned environment file for non-local access. The default bind is `127.0.0.1`; expose it only through an authenticated private reverse proxy or SSH/Tailscale tunnel. `/health` is liveness; `/readiness` proves Store and Action Runtime availability and reports optional integrations separately.

Օգտագործեք `deploy/install.sh`-ը թիրախային Linux հոսթում։ Այն service unit-ները ստեղծում է բացահայտ `DEPUTY_USER`, `DEPUTY_ROOT`, `DEPUTY_VENV`, `DEPUTY_BIND`, `DEPUTY_PORT`, `DEPUTY_BACKUP_DIR` և `DEPUTY_WORKER_INTERVAL` արժեքներից և երբեք token չի գրում։ Ոչ-local հասանելիության համար `DEPUTY_OPERATOR_TOKEN`-ը տեղադրեք նշված root-owned environment ֆայլում։ Անվտանգ լռելյայն bind-ը `127.0.0.1` է․ արտաքին հասանելիությունը տրամադրեք միայն նույնականացվող private reverse proxy-ով կամ SSH/Tailscale tunnel-ով։ `/health`-ը liveness է, իսկ `/readiness`-ը ստուգում է Store և Action Runtime-ը և optional ինտեգրացիաները ցույց է տալիս առանձին։

### Windows Outlook bridge (OCI)

When the OCI host cannot run Classic Outlook/MAPI, run the supported read-only Outlook bridge in Gev's signed-in Windows desktop session. Keep the bridge bound to `127.0.0.1:8766` and use a persistent reverse SSH tunnel from Windows to OCI; never open the bridge or Deputy port publicly. Set the host-only environment value `DEPUTY_OUTLOOK_BRIDGE_URL=http://127.0.0.1:8766` for the API and worker services, then restart them. The bridge exposes only fixed read operations (`/probe`, `/mail`, `/calendar`); external writes still require exact approval and the canonical Action Runtime. If the Windows session is signed out or Outlook is closed, readiness must show Outlook as unavailable/partial.

### Windows Outlook bridge (OCI) — հայերեն

Երբ OCI հոսթը չի կարող աշխատեցնել Classic Outlook/MAPI-ը, օգտագործեք Gev-ի մուտք գործած Windows desktop session-ում աշխատող միայն-կարդալու Outlook bridge-ը։ Bridge-ը պահեք միայն `127.0.0.1:8766` հասցեում և Windows-ից OCI պահեք persistent reverse SSH tunnel-ով․ bridge-ի կամ Deputy-ի port-ը հանրային մի բացեք։ API և worker service-ների host-only environment-ում սահմանեք `DEPUTY_OUTLOOK_BRIDGE_URL=http://127.0.0.1:8766` և վերագործարկեք service-ները։ Bridge-ը տրամադրում է միայն ֆիքսված read գործողություններ (`/probe`, `/mail`, `/calendar`)․ արտաքին գրառումները շարունակում են անցնել exact approval-ով և canonical Action Runtime-ով։ Եթե Windows session-ը դուրս է եկել կամ Outlook-ը փակ է, readiness-ը պետք է Outlook-ը ցույց տա unavailable/partial վիճակով։

Backup: `python backup_ops.py` is orchestrated by `deputy-backup.timer`; verify with `backup_ops.verify(path)` and certify restore only with `backup_ops.restore_isolated(path)`. Retention preserves the newest seven valid sets and never prunes the newest known-good set. Live systemd installation and remote browser access remain host-certification gates until run on the production host.

Պահուստավորում․ `deputy-backup.timer`-ը գործարկում է backup orchestration-ը, ստուգումը կատարեք `backup_ops.verify(path)`-ով, իսկ restore certification-ը՝ միայն `backup_ops.restore_isolated(path)`-ով։ Պահպանվում են վերջին յոթ վավեր set-երը և վերջին known-good set-ը չի ջնջվում։ Live systemd տեղադրումը և remote browser հասանելիությունը մնում են host-certification gate-եր մինչև production host-ում փորձարկվելը։
