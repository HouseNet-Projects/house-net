"""Provider-neutral Deputy AI boundary using the authenticated Claude Code CLI.

This intentionally never reads or uses ANTHROPIC_API_KEY. Claude Code owns the
interactive Max-plan session and billing boundary; Deputy only invokes the CLI.
"""
from __future__ import annotations
import json, os, shutil, subprocess
import re

PROVIDER = "claude-code-max"
TOOL_REQUEST_PREFIX = "DEPUTY_TOOL_REQUEST"
MAX_TOOL_RESULT_CHARS = 12000

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


def parse_tool_request(answer: str) -> dict | None:
    """Parse the deliberately narrow read/prepare request envelope.

    Claude never receives a provider write tool. A request is accepted only
    when it names one of Deputy's registered read tools and contains a short
    query. Markdown fences are tolerated for provider robustness.
    """
    if not isinstance(answer, str):
        return None
    allowed = {"search_work", "search_open_loops", "search_observations", "search_approvals", "search_context"}
    text = answer.strip().replace("```json", "").replace("```", "").strip()
    candidates = [text]
    match = re.search(r"DEPUTY_TOOL_REQUEST\s*[:]?\s*(\{.*\})", text, flags=re.S)
    if match:
        candidates.insert(0, match.group(1))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("type") in ("tool_request", TOOL_REQUEST_PREFIX):
            tool = value.get("tool")
            query = str(value.get("query") or "").strip()
            if tool in allowed and query:
                return {"tool": tool, "query": query, "limit": max(1, min(int(value.get("limit", 8)), 12))}
    return None


def ask_agent(prompt: str, *, context=None, tool_executor=None, timeout: int = 90, max_iterations: int = 4) -> dict:
    """Run bounded governed reasoning with read/prepare-only tool requests."""
    trace = []
    current = prompt + (
        "\n\nIf the evidence is insufficient, request one registered read tool by returning only "
        "DEPUTY_TOOL_REQUEST {\\\"type\\\":\\\"tool_request\\\",\\\"tool\\\":\\\"search_work\\\",\\\"query\\\":\\\"...\\\"}. "
        "Never request or perform an external write."
    )
    for iteration in range(max(1, min(int(max_iterations), 6))):
        result = ask(current, context=context, timeout=timeout)
        answer = result.get("answer", "")
        request = parse_tool_request(answer)
        if result.get("status") != "OK" or not request:
            result["agent_trace"] = trace
            result["agent_iterations"] = iteration + 1
            return result
        if not tool_executor:
            result["status"] = "DEGRADED"
            result["reason"] = "Deputy read tool executor is unavailable."
            result["agent_trace"] = trace
            result["agent_iterations"] = iteration + 1
            return result
        signature = (request["tool"], request["query"], request["limit"])
        if any(x.get("signature") == signature for x in trace):
            result["status"] = "DEGRADED"
            result["reason"] = "Deputy stopped a repeated read request."
            result["answer"] = "I could not obtain additional distinct evidence safely."
            result["agent_trace"] = trace
            result["agent_iterations"] = iteration + 1
            return result
        try:
            tool_result = tool_executor(request)
            serialized = json.dumps(tool_result, ensure_ascii=False, default=str)
            serialized = serialized[:MAX_TOOL_RESULT_CHARS]
            trace.append({"tool": request["tool"], "query": request["query"], "result_count": len(tool_result.get("records", [])) if isinstance(tool_result, dict) else 0,
                          "signature": signature, "iteration": iteration + 1, "status": "OK"})
        except Exception as exc:
            serialized = json.dumps({"status": "UNAVAILABLE", "reason": type(exc).__name__})
            trace.append({"tool": request["tool"], "query": request["query"], "result_count": 0,
                          "signature": signature, "iteration": iteration + 1, "status": "UNAVAILABLE"})
        current = prompt + "\n\nDeputy read tool result (evidence only):\n" + serialized + \
            "\n\nContinue reasoning. Do not expose private reasoning or raw tool payloads. Return a final human answer, or one new DEPUTY_TOOL_REQUEST if another distinct read is essential."
    result = result if 'result' in locals() else {"status": "EMPTY_RESPONSE", "provider": PROVIDER}
    result["status"] = "DEGRADED" if result.get("status") == "OK" else result.get("status")
    result["reason"] = "Deputy stopped after the bounded read-tool limit." 
    result["agent_trace"] = trace
    result["agent_iterations"] = max(1, min(int(max_iterations), 6))
    return result
