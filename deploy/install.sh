#!/usr/bin/env bash
# Render/install host-adaptable Deputy services. No secrets are written by this script.
set -euo pipefail
ROOT_DIR=${DEPUTY_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
USER_NAME=${DEPUTY_USER:-$(id -un)}
VENV=${DEPUTY_VENV:-$ROOT_DIR/command-center/.venv}
BIND=${DEPUTY_BIND:-127.0.0.1}; PORT=${DEPUTY_PORT:-8765}; INTERVAL=${DEPUTY_WORKER_INTERVAL:-900}
BACKUP_DIR=${DEPUTY_BACKUP_DIR:-$ROOT_DIR/command-center/.secure/backups}
OUT=${DEPUTY_UNIT_DIR:-/etc/systemd/system}; ENV_FILE=${DEPUTY_ENV_FILE:-/etc/house-net/deputy.env}
for x in "$ROOT_DIR" "$VENV"; do test -d "$x" || { echo "missing directory: $x" >&2; exit 2; }; done
case "$BIND" in *[!a-zA-Z0-9:._-]*) echo 'invalid bind address' >&2; exit 2;; esac

# Materialize and validate governed LFS inputs before touching running services.
# A pointer or corrupt workbook must fail deployment before a restart can take
# a healthy Deputy offline.
preflight_lfs_inputs(){
  if [ -f "$ROOT_DIR/.gitattributes" ] && grep -q 'filter=lfs' "$ROOT_DIR/.gitattributes"; then
    command -v git-lfs >/dev/null 2>&1 || { echo 'git-lfs is required for this deployment' >&2; exit 2; }
    git -C "$ROOT_DIR" lfs pull >/dev/null
    while IFS= read -r rel; do
      [ -n "$rel" ] || continue
      file="$ROOT_DIR/$rel"
      [ -f "$file" ] || { echo "missing LFS input: $rel" >&2; exit 2; }
      if head -c 64 "$file" | grep -q 'version https://git-lfs.github.com/spec/v1'; then
        echo "LFS pointer was not materialized: $rel" >&2; exit 2
      fi
      case "$rel" in
        *.xlsx|*.xlsm)
          python3 - "$file" <<'PY'
import sys, zipfile
p=sys.argv[1]
try:
    with zipfile.ZipFile(p) as z:
        required={"[Content_Types].xml","xl/workbook.xml"}
        missing=required-set(z.namelist())
        if missing: raise ValueError("missing XLSX members: " + ",".join(sorted(missing)))
except Exception as e:
    raise SystemExit(f"invalid XLSX input {p}: {e}")
PY
          ;;
      esac
    done < <(git -C "$ROOT_DIR" lfs ls-files --name-only)
  fi
}
preflight_lfs_inputs
if [ "$(id -u)" -eq 0 ]; then
  # Services run as USER_NAME; keep the backup target writable without broad permissions.
  install -d -o "$USER_NAME" -g "$(id -gn "$USER_NAME")" -m 0750 "$BACKUP_DIR"
else
  mkdir -p "$BACKUP_DIR"
fi
render(){ sed -e "s|@USER@|$USER_NAME|g" -e "s|@ROOT@|$ROOT_DIR|g" -e "s|@VENV@|$VENV|g" -e "s|@BIND@|$BIND|g" -e "s|@PORT@|$PORT|g" -e "s|@INTERVAL@|$INTERVAL|g" -e "s|@BACKUP@|$BACKUP_DIR|g" -e "s|@ENV@|$ENV_FILE|g" "$1"; }
if [ "$(id -u)" -ne 0 ]; then OUT=${DEPUTY_UNIT_DIR:-$ROOT_DIR/.generated-systemd}; mkdir -p "$OUT"; echo "rendered units to $OUT (run as root to install)"; fi
for n in deputy-api.service deputy-worker.service deputy-backup.service deputy-backup.timer; do render "$(dirname "$0")/$n" > "$OUT/$n"; done
if [ "$(id -u)" -eq 0 ]; then install -d -m 0750 "$(dirname "$ENV_FILE")"; touch "$ENV_FILE"; chmod 0640 "$ENV_FILE"; systemctl daemon-reload; systemctl enable --now deputy-api.service deputy-worker.service; systemctl enable deputy-backup.timer; fi
echo "Deputy services configured: user=$USER_NAME root=$ROOT_DIR bind=$BIND port=$PORT backup=$BACKUP_DIR"
