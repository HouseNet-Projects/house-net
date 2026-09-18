"""Provider-neutral Deputy AI boundary using the authenticated Claude Code CLI.

This intentionally never reads or uses ANTHROPIC_API_KEY. Claude Code owns the
interactive Max-plan session and billing boundary; Deputy only invokes the CLI.
"""
from __future__ import annotations
import json, os, shutil, subprocess

PROVIDER = "claude-code-max"

def _auth_state(raw: dict) -> str:
    if not raw.get("loggedIn"):
        return "AUTH_REQUIRED"
    if raw.get("authMethod") not in ("claude.ai", "claude_app"):
        return "WRONG_PROVIDER"
    if raw.get("apiProvider") not in (None, "firstParty"):
        return "WRONG_PROVIDER"
    if raw.get("subscriptionType") not in (None, "pro", "max", "team", "enterprise"):
        return "WRONG_PROVIDER"
    return "READY"

def status() -> dict:
    cli = shutil.which("claude")
    if not cli:
        return {"provider": PROVIDER, "state": "NOT_INSTALLED", "api_key_required": False}
    try:
        p = subprocess.run([cli, "auth", "status", "--json"], capture_output=True, text=True, timeout=8)
        if p.returncode == 0:
            try:
                raw = json.loads(p.stdout or "{}")
                state = _auth_state(raw)
                return {"provider": PROVIDER, "state": state, "api_key_required": False,
                        "auth_method": raw.get("authMethod"), "subscription": raw.get("subscriptionType"),
                        "api_provider": raw.get("apiProvider")}
            except json.JSONDecodeError:
                return {"provider": PROVIDER, "state": "AUTH_REQUIRED", "api_key_required": False}
        return {"provider": PROVIDER, "state": "AUTH_REQUIRED", "api_key_required": False}
    except (OSError, subprocess.TimeoutExpired):
        return {"provider": PROVIDER, "state": "UNAVAILABLE", "api_key_required": False}

def _answer(raw):
    if isinstance(raw, str): return raw.strip()
    if isinstance(raw, dict):
        for key in ("result", "text", "answer", "message", "content"):
            if key in raw:
                value = _answer(raw[key])
                if value: return value
    if isinstance(raw, list):
        parts = [_answer(x) for x in raw]
        return "\n".join(x for x in parts if x).strip()
    return ""

def ask(prompt: str, *, context=None, timeout: int = 90) -> dict:
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
        answer = _answer(result)
        if not answer:
            return {"status": "EMPTY_RESPONSE", "provider": PROVIDER, "provider_state": "READY", "reason": "Claude returned no answer."}
        return {"status": "OK", "provider": PROVIDER, "provider_state": "READY", "answer": answer,
                "result_meta": {"model": result.get("model") if isinstance(result, dict) else None}}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "provider": PROVIDER, "reason": "Claude Code request timed out."}
    except OSError:
        return {"status": "UNAVAILABLE", "provider": PROVIDER}
