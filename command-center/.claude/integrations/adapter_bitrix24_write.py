# -*- coding: utf-8 -*-
"""WRITE ADAPTER INT-B24 — Bitrix24 REST mutations (tasks.task.add · crm.deal.update · crm.activity.add) with a fixed method allowlist.
Reached ONLY by the Action Runtime after Gev's approval. Verification re-reads through the GET-only read adapter (tasks.task.get / crm.deal.get /
crm.activity.list). Honest runtime truth: without a webhook the integration is NOT_CONFIGURED — nothing here fabricates access."""
import sys, json, pathlib, urllib.request, urllib.parse, urllib.error, socket, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
import adapter_bitrix24 as rd, int_secrets as _secrets
from contracts import IntegrationError

OPS = {"tasks.create": "tasks.task.add", "crm.deal.update": "crm.deal.update", "crm.activity.create": "crm.activity.add"}
WRITE_METHODS = re.compile(r"^(tasks\.task\.add|crm\.deal\.update|crm\.activity\.add)$")

def _err():
    from actions import ProviderError, ProviderUnknown; return ProviderError, ProviderUnknown

def _cfg():
    ProviderError, _ = _err(); cfg = _secrets.load_config("INT-B24")
    if not cfg.get("webhook_url"): raise ProviderError("INT-B24 NOT_CONFIGURED — no read/write webhook (see registry unblock)")
    return cfg

def post_transport(url, data, timeout=20):
    ProviderError, ProviderUnknown = _err()
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="POST", headers={"Content-Type": "application/json", "User-Agent": "Deputy-Command-center/governed-write"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8", "replace")
        except Exception: return e.code, ""
    except (socket.timeout, TimeoutError): raise ProviderUnknown("Bitrix24 timed out — the write may have been applied")
    except (urllib.error.URLError, OSError) as e: raise ProviderError(f"portal unreachable: {_secrets.redact(str(e))[:120]}")

def call(method, params, cfg=None, transport=None):
    ProviderError, ProviderUnknown = _err()
    if not WRITE_METHODS.match(method or ""): raise ProviderError(f"Bitrix24 write method {method!r} not in the governed allowlist")
    cfg = cfg or _cfg(); url = str(cfg["webhook_url"]).rstrip("/") + "/" + method + ".json"
    status, text = (transport or post_transport)(url, params)
    try: d = json.loads(text) if text else {}
    except ValueError: raise ProviderUnknown(f"non-JSON response (http {status}) — outcome unknown")
    if d.get("error"): raise ProviderError(f"{d.get('error')}: {_secrets.redact(str(d.get('error_description') or ''))[:120]}")
    if status >= 500: raise ProviderUnknown(f"http {status} — outcome unknown")
    if status != 200 or "result" not in d: raise ProviderError(f"unexpected response http {status}")
    return d["result"]

def precondition(op, params):
    oid = params.get("target_object_id")
    if not oid: return {"exists": False, "object": None}
    if op == "crm.deal.update":
        r = rd.read("crm.deals", {"filter": {"ID": oid}, "limit": 1}, _cfg_read())
        rec = r["records"][0] if r["records"] else None
        return {"exists": bool(rec), "object": rec}
    return {"exists": False, "object": None}

def _cfg_read():
    try: return _cfg()
    except Exception: return {}

def find_existing(op, params):
    cfg = _cfg_read()
    if not cfg.get("webhook_url"): raise RuntimeError("NOT_CONFIGURED")
    if op == "tasks.create":
        r = rd.read("tasks.list", {"filter": {"TITLE": params.get("title"), "RESPONSIBLE_ID": params.get("responsible_id")}, "limit": 5}, cfg)
        return ({"id": r["records"][0]["source_record_id"], **r["records"][0]} if r["records"] else None)
    if op == "crm.deal.update":
        r = rd.read("crm.deals", {"filter": {"ID": params.get("target_object_id")}, "limit": 1}, cfg)
        if r["records"] and all(str(r["records"][0].get(k)) == str(v) for k, v in (params.get("fields") or {}).items() if k in r["records"][0]): return {"id": params.get("target_object_id"), **r["records"][0]}
        return None
    return None

def execute(op, params):
    ProviderError, _ = _err()
    if op not in OPS: raise ProviderError(f"unknown Bitrix24 operation {op}")
    cfg = _cfg(); method = OPS[op]
    if op == "tasks.create": body = {"fields": {"TITLE": params["title"], "RESPONSIBLE_ID": params["responsible_id"], "DEADLINE": params.get("deadline"), "DESCRIPTION": params.get("description", "")}}
    elif op == "crm.deal.update": body = {"id": params["target_object_id"], "fields": params.get("fields") or {}}
    else: body = {"fields": {"SUBJECT": params["subject"], "RESPONSIBLE_ID": params["responsible_id"], "DEADLINE": params.get("deadline"), "OWNER_TYPE_ID": params.get("owner_type_id", 2), "OWNER_ID": params.get("owner_id"), "TYPE_ID": params.get("type_id", 6), "COMPLETED": "N"}}
    res = call(method, body, cfg, params.get("_transport"))
    oid = (res.get("task", {}).get("id") if isinstance(res, dict) and "task" in res else res) if op != "crm.deal.update" else params["target_object_id"]
    return {"ok": True, "id": str(oid)}

def verify(op, params, result):
    try:
        cfg = _cfg(); oid = (result or {}).get("id")
        if op == "tasks.create":
            r = rd.read("tasks.list", {"filter": {"ID": oid}, "limit": 1}, cfg); rec = r["records"][0] if r["records"] else None
            if not rec: return {"verified": False, "reason": f"task {oid} not found on read-back", "evidence": None}
            ok = rec["title"] == params["title"] and str(rec["responsible_id"]) == str(params["responsible_id"])
            return {"verified": ok, "reason": "read-back matches" if ok else "title/responsible mismatch", "evidence": rec}
        if op == "crm.deal.update":
            r = rd.read("crm.deals", {"filter": {"ID": oid}, "limit": 1}, cfg); rec = r["records"][0] if r["records"] else None
            if not rec: return {"verified": False, "reason": "deal not found", "evidence": None}
            fields = params.get("fields") or {}; norm = {"STAGE_ID": "stage_id", "TITLE": "title", "OPPORTUNITY": "opportunity"}
            diffs = {k: v for k, v in fields.items() if k in norm and str(rec.get(norm[k])) != str(v)}
            return {"verified": not diffs, "reason": ("mismatch: " + ", ".join(diffs)) if diffs else "read-back matches", "evidence": rec}
        return {"verified": False, "reason": "no verification method for this operation", "evidence": None}
    except Exception as e:
        return {"verified": False, "reason": f"read-back failed: {type(e).__name__}: {str(e)[:100]}", "evidence": None}
