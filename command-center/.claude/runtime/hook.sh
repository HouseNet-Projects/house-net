#!/usr/bin/env bash
# Command-center hook launcher — the ONLY way settings.json starts a hook.
#   hook.sh <hook.py> <event>      runs .claude/hooks/<hook.py> under the project interpreter (<root>/.venv)
# Steady state needs NO python on PATH: the venv interpreter is invoked by absolute path. A PATH python is used only
# as a stdlib-only launcher when the venv is missing (python_runtime.py then bootstraps it or fails closed).
R="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
[ -f "$R/.claude/runtime/python_runtime.py" ] || R="$(cd "$(dirname "$0")/../.." && pwd)"
P=""
for c in "$R/.venv/Scripts/python.exe" "$R/.venv/bin/python"; do
  if [ -x "$c" ]; then P="$c"; break; fi
done
if [ -z "$P" ]; then
  P="$(command -v python || command -v python3)"
  [ -n "$P" ] || { echo "Command-center runtime: no .venv and no python launcher on PATH — run: py -3 .claude/runtime/python_runtime.py bootstrap" >&2; exit 2; }
fi
exec "$P" "$R/.claude/runtime/python_runtime.py" hook "$R/.claude/hooks/$1" "${@:2}"
