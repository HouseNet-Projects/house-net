# -*- coding: utf-8 -*-
"""INTEGRATION READINESS — one honest activation view per integration, built from the existing primitives (registry declarations,
int_secrets config presence, health, certification.json, capabilities): implementation · configuration (missing FIELD NAMES only,
never values) · live identity · read certification · write certification · deferral. Nothing here connects to a provider.

    python .claude/integrations/integration.py readiness"""
import sys, pathlib, json, importlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
import registry, health, int_secrets as _secrets, capabilities as C

ACTIVATION_FIELDS = {
 "INT-TG": {"required": ["bot_token", "allowed_chat_ids"], "optional": ["allowed_user_ids", "expected_bot_username", "mode (polling|webhook)", "webhook_secret", "observe_unknown"]},
 "INT-WA": {"required": ["access_token", "phone_number_id", "verify_token", "app_secret", "allowed_numbers"], "optional": ["business_account_id", "expected_display_phone", "webhook_host", "webhook_port", "webhook_path", "observe_unknown"]},
 "INT-B24": {"required": ["webhook_url", "portal_domain"], "optional": []},
 "INT-MB": {"required": [], "optional": []}, "INT-TASKS": {"required": [], "optional": []}, "INT-OL-CAL": {"required": [], "optional": []}, "INT-OL-MAIL": {"required": [], "optional": []},
}

def _cert():
    p = HERE / "certification.json"
    try: return json.loads(p.read_text(encoding="utf-8")).get("integrations", {}) if p.exists() else {}
    except ValueError: return {}

def row(iid):
    spec = registry.get(iid) or {}; h = health.get(iid) or {}; cert = _cert().get(iid, {}); af = ACTIVATION_FIELDS.get(iid, {"required": [], "optional": []})
    try: importlib.import_module(spec["adapter"]); implemented = bool(spec.get("read_ops")) or bool(C.WRITE_OPS.get(iid))
    except Exception: implemented = False
    cfg = {}
    try: cfg = _secrets.load_config(iid) if spec.get("auth", {}).get("secrets") or af["required"] else {}
    except Exception: cfg = {}
    missing = [f for f in af["required"] if not str(cfg.get(f.split(" ")[0]) or "").strip()]
    configured = not missing and (not spec.get("auth", {}).get("secrets") or all(cfg.get(s) for s in spec["auth"]["secrets"]))
    deferred = spec.get("deferred")
    ident = "NOT VERIFIED"
    if h.get("last_success"): ident = f"VERIFIED (last real read {h['last_success'][:16]})"
    if deferred: ident = "DEFERRED"
    read_state = cert.get("state") or ("DEFERRED" if deferred else ("CONFIGURED" if configured else ("IMPLEMENTED" if implemented else "DECLARED")))
    if deferred: read_state = "DEFERRED"
    wc = C._write_certs().get(iid, {}); writes = {op: ("VERIFIED_WRITE" if wc.get(op) else C.capability(iid, op)["level"]) for op in C.WRITE_OPS.get(iid, {})}     # a Gev-approved live certification stands even when the provider is not reachable right now
    out = {"integration_id": iid, "system": spec.get("system"), "implementation": ("READY" if implemented else "MISSING") if not deferred else "DEFERRED", "configuration": "DEFERRED" if deferred else ("OK" if configured else "MISSING"),
           "missing": [] if deferred else missing, "optional": af["optional"], "live_identity": ident, "read": read_state if read_state in ("VERIFIED_READ", "RELIABLE_READ") else ("NOT CERTIFIED" if not deferred else "DEFERRED"),
           "read_state": read_state, "write": {op: ("CERTIFIED" if lvl == "VERIFIED_WRITE" else "NOT CERTIFIED") for op, lvl in writes.items()} or None, "deferred": deferred,
           "expected_identity": spec.get("expected_identity"), "unblock": None if configured or deferred else spec.get("unblock")}
    if iid == "INT-WA": out["callback"] = f"VERIFIED (handshake {h['callback_verified_at'][:16]})" if h.get("callback_verified_at") else "NOT VERIFIED"
    if iid == "INT-B24": out["portal_expected"] = (spec.get("expected_identity") or {}).get("portal_domain")
    if iid == "INT-TG": out["transport"] = str(cfg.get("mode") or "polling") if cfg else "polling (default)"
    return out

def table(): return [row(iid) for iid in registry.ids()]

def scheduler_status():
    """Proactive routines need a real trigger; until one is installed and verified (heartbeat), the scheduler is NOT_CONFIGURED — nothing runs in the background."""
    p = health.state_dir() / "scheduler_heartbeat.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except ValueError: d = {}
    return {"status": "CONFIGURED" if d.get("last_run") else "NOT_CONFIGURED", "last_run": d.get("last_run"), "routine": d.get("routine"), "note": "no background delivery exists; routines run when invoked (skill.py routine <name>) or by an external scheduler that reports a heartbeat"}

def render(rows=None):
    L = []
    for r in rows or table():
        L.append(f"{r['integration_id']}")
        L.append(f"  implementation: {r['implementation']} · configuration: {r['configuration']}" + (f" · missing: {', '.join(x.upper() for x in r['missing'])}" if r["missing"] else ""))
        if r.get("portal_expected"): L.append(f"  portal expected: {r['portal_expected']}")
        if r.get("transport"): L.append(f"  transport: {r['transport']}")
        L.append(f"  live identity: {r['live_identity']}")
        if "callback" in r: L.append(f"  callback: {r['callback']}")
        L.append(f"  read: {r['read']}" + (f" ({r['read_state']})" if r["read"] == "NOT CERTIFIED" else ""))
        if r["write"]: L.append("  write: " + " · ".join(f"{op} {s}" for op, s in r["write"].items()))
        if r["deferred"]: L.append(f"  deferred by {r['deferred'].get('by')} since {r['deferred'].get('since')} — no activation requested")
    s = scheduler_status(); L.append(f"SCHEDULER: {s['status']}" + (f" (last run {s['last_run']})" if s.get("last_run") else " — routines run on demand; install a trigger and it reports a heartbeat"))
    return "\n".join(L)
