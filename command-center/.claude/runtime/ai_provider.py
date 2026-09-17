"""Provider-neutral Deputy AI boundary using the authenticated Claude Code CLI.

This intentionally never reads or uses ANTHROPIC_API_KEY. Claude Code owns the
interactive Max-plan session and billing boundary; Deputy only invokes the CLI.
"""
from __future__ import annotations
import json, os, shutil, subprocess

PROVIDER = "claude-code-max"

def status() -> dict:
    cli = shutil.which("claude")
    if not cli:
        return {"provider": PROVIDER, "state": "NOT_INSTALLED", "api_key_required": False}
    try:
        p = subprocess.run([cli, "auth", "status", "--json"], capture_output=True, text=True, timeout=8)
        if p.returncode == 0:
            try:
                raw = json.loads(p.stdout or "{}")
                return {"provider": PROVIDER, "state": "READY", "api_key_required": False,
                        "account": raw.get("email") or raw.get("account")}
            except json.JSONDecodeError:
                return {"provider": PROVIDER, "state": "READY", "api_key_required": False}
        return {"provider": PROVIDER, "state": "AUTH_REQUIRED", "api_key_required": False}
    except (OSError, subprocess.TimeoutExpired):
        return {"provider": PROVIDER, "state": "UNAVAILABLE", "api_key_required": False}

def ask(prompt: str, *, timeout: int = 90) -> dict:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"status": "BLOCKED", "reason": "API-key path is disabled; authenticate Claude Code instead.", "provider": PROVIDER}
    st = status()
    if st.get("state") != "READY":
        return {"status": "DEGRADED", "provider": PROVIDER, "provider_state": st.get("state"), "reason": "Claude Code Max session is not ready."}
    cli = shutil.which("claude")
    try:
        p = subprocess.run([cli, "-p", prompt, "--output-format", "json"], capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0:
            return {"status": "FAILED", "provider": PROVIDER, "reason": "Claude Code request failed."}
        try: result = json.loads(p.stdout or "{}")
        except json.JSONDecodeError: result = {"text": p.stdout.strip()}
        return {"status": "OK", "provider": PROVIDER, "result": result}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "provider": PROVIDER, "reason": "Claude Code request timed out."}
    except OSError:
        return {"status": "UNAVAILABLE", "provider": PROVIDER}
