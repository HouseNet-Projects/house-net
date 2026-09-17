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
mkdir -p "$BACKUP_DIR"
render(){ sed -e "s|@USER@|$USER_NAME|g" -e "s|@ROOT@|$ROOT_DIR|g" -e "s|@VENV@|$VENV|g" -e "s|@BIND@|$BIND|g" -e "s|@PORT@|$PORT|g" -e "s|@INTERVAL@|$INTERVAL|g" -e "s|@BACKUP@|$BACKUP_DIR|g" -e "s|@ENV@|$ENV_FILE|g" "$1"; }
if [ "$(id -u)" -ne 0 ]; then OUT=${DEPUTY_UNIT_DIR:-$ROOT_DIR/.generated-systemd}; mkdir -p "$OUT"; echo "rendered units to $OUT (run as root to install)"; fi
for n in deputy-api.service deputy-worker.service deputy-backup.service deputy-backup.timer; do render "$(dirname "$0")/$n" > "$OUT/$n"; done
if [ "$(id -u)" -eq 0 ]; then install -d -m 0750 "$(dirname "$ENV_FILE")"; touch "$ENV_FILE"; chmod 0640 "$ENV_FILE"; systemctl daemon-reload; systemctl enable --now deputy-api.service deputy-worker.service; systemctl enable deputy-backup.timer; fi
echo "Deputy services configured: user=$USER_NAME root=$ROOT_DIR bind=$BIND port=$PORT backup=$BACKUP_DIR"
