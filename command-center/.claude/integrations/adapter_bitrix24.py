# -*- coding: utf-8 -*-
"""ADAPTER INT-B24 — Bitrix24 REST, GET-only, fixed method allowlist (list/get/fields only). There is NO generic endpoint
executor: call() refuses any method outside READ_METHODS even when asked directly (ReadOnlyViolation). Credentials come from
secrets.load_config("INT-B24") — never from the repository; the webhook code is redacted from every error/log.
Connectivity is NOT claimed by this module: only a real authenticated read (layer.query → certify) can mark it CONNECTED."""
import sys, pathlib, json, urllib.request, urllib.parse, urllib.error, socket, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from contracts import IntegrationError, ReadOnlyViolation
import normalize, int_secrets as _secrets

OPS = {"crm.deals": ("crm.deal.list", "deal"), "crm.leads": ("crm.lead.list", "lead"), "crm.stages": ("crm.status.list", "stage"), "crm.activities": ("crm.activity.list", "activity"),
       "tasks.list": ("tasks.task.list", "b24task"), "users": ("user.get", "user"), "identity": ("profile", "identity")}
READ_METHODS = re.compile(r"^(crm\.(deal|lead|status|contact|company|activity)\.(list|get|fields)|tasks\.task\.(list|get)|user\.(get|current)|profile|app\.info)$")
DEFAULT_SELECT = {"crm.deal.list": ["ID", "TITLE", "STAGE_ID", "ASSIGNED_BY_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSED", "CATEGORY_ID", "SOURCE_ID"],
                  "crm.lead.list": ["ID", "TITLE", "STATUS_ID", "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY", "SOURCE_ID"],
                  "crm.activity.list": ["ID", "SUBJECT", "RESPONSIBLE_ID", "DEADLINE", "COMPLETED", "TYPE_ID", "OWNER_TYPE_ID", "LAST_UPDATED"]}
AUTH_ERRORS = ("expired_token", "invalid_token", "no_auth_found", "invalid_credentials", "wrong_client", "authorization_error", "invalid_grant")
SCOPE_ERRORS = ("insufficient_scope", "access_denied", "allowed_only_intranet_user", "forbidden")

def default_transport(url, timeout=20):
    """GET only. Returns (http_status, text). Never posts a body — writes are impossible through this transport."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Deputy-Command-center/read-only"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try: body = e.read().decode("utf-8", "replace")
        except Exception: body = ""
        return e.code, body
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
        raise IntegrationError("UNAVAILABLE", f"portal unreachable: {_secrets.redact(str(e))[:160]}", retryable=True)

def _host(url):
    try: return urllib.parse.urlparse(url).hostname or ""
    except Exception: return ""

def call(method, params=None, cfg=None, transport=None):
    if not READ_METHODS.match(method or ""): raise ReadOnlyViolation(f"Bitrix24 method {method!r} is not in the read allowlist (list/get/fields only)")
    cfg = cfg if cfg is not None else _secrets.load_config("INT-B24")
    base = str(cfg.get("webhook_url") or "").strip()
    if not base: raise IntegrationError("NOT_CONFIGURED", "no webhook_url for INT-B24 (CC_INT_B24_WEBHOOK_URL or ~/.command-center/integrations/INT-B24.json)")
    if not base.startswith("https://"): raise IntegrationError("NOT_CONFIGURED", "webhook_url must be https")
    exp = str(cfg.get("portal_domain") or "").strip().lower()
    if exp and _host(base).lower() != exp: raise IntegrationError("WRONG_TENANT", f"webhook host {_host(base)} ≠ configured portal_domain {exp}")
    q = {}
    for k, v in (params or {}).items():
        if isinstance(v, dict):
            for kk, vv in v.items(): q[f"{k}[{kk}]"] = vv
        elif isinstance(v, (list, tuple)):
            for i, vv in enumerate(v): q[f"{k}[{i}]"] = vv
        else: q[k] = v
    url = base.rstrip("/") + "/" + method + ".json" + ("?" + urllib.parse.urlencode(q) if q else "")
    status, text = (transport or default_transport)(url)
    try: d = json.loads(text) if text else {}
    except ValueError: raise IntegrationError("MALFORMED_RESPONSE", f"non-JSON response (http {status}): {_secrets.redact(text)[:80]}")
    if not isinstance(d, dict): raise IntegrationError("MALFORMED_RESPONSE", "response is not an object")
    err = str(d.get("error") or "").lower()
    if err or status in (401, 403):
        desc = _secrets.redact(str(d.get("error_description") or ""))[:160]
        if err in AUTH_ERRORS or status == 401: raise IntegrationError("AUTH_FAILED", f"{err or status}: {desc}")
        if err in SCOPE_ERRORS or status == 403: raise IntegrationError("PERMISSION_DENIED", f"{err or status}: {desc}")
        if err == "query_limit_exceeded" or status == 503: raise IntegrationError("RATE_LIMITED", f"{err}: {desc}", retryable=True)
        raise IntegrationError("UNAVAILABLE", f"{err or status}: {desc}")
    if status >= 500: raise IntegrationError("UNAVAILABLE", f"portal error http {status}", retryable=True)
    if status == 429: raise IntegrationError("RATE_LIMITED", "http 429", retryable=True)
    if status != 200: raise IntegrationError("UNAVAILABLE", f"unexpected http {status}")
    if "result" not in d: raise IntegrationError("SCHEMA_CHANGED", f"response without 'result' (keys {sorted(d)[:6]})")
    return d

def read(op, params=None, cfg=None, transport=None):
    params = params or {}
    if op not in OPS: raise IntegrationError("UNKNOWN_OPERATION", f"INT-B24 has no operation {op}")
    method, kind = OPS[op]
    cfg = cfg if cfg is not None else _secrets.load_config("INT-B24")
    q = {}
    if op in ("crm.deals", "crm.leads", "crm.activities"):
        q["select"] = params.get("select") or DEFAULT_SELECT[method]
        if params.get("filter"): q["filter"] = params["filter"]
        q["order"] = {"DATE_MODIFY": "DESC"} if op != "crm.activities" else {"LAST_UPDATED": "DESC"}
    elif op == "crm.stages": q["filter"] = {"ENTITY_ID": params.get("entity_id") or "DEAL_STAGE"}
    elif op == "tasks.list":
        q["select"] = ["ID", "TITLE", "STATUS", "RESPONSIBLE_ID", "DEADLINE", "CREATED_BY", "CHANGED_DATE"]
        if params.get("filter"): q["filter"] = params["filter"]
    elif op == "users" and params.get("filter"): q["filter"] = params["filter"]
    d = call(method, q, cfg, transport)
    res = d["result"]
    if op == "tasks.list":
        if not isinstance(res, dict) or "tasks" not in res: raise IntegrationError("SCHEMA_CHANGED", "tasks.task.list result lacks 'tasks'")
        rows = res["tasks"]
    elif op == "identity":
        if not isinstance(res, dict) or "ID" not in res: raise IntegrationError("SCHEMA_CHANGED", "profile result lacks ID")
        rows = [res]
    else:
        if not isinstance(res, list): raise IntegrationError("SCHEMA_CHANGED", f"{method} result is not a list")
        rows = res
    if not all(isinstance(r, dict) for r in rows): raise IntegrationError("SCHEMA_CHANGED", f"{method}: non-object rows")
    limit = int(params.get("limit") or 50); partial = bool(d.get("next")) or len(rows) > limit
    rows = rows[:limit]
    host = _host(cfg.get("webhook_url", ""))
    upd = None
    norm = {"deal": normalize.deal, "lead": normalize.lead, "stage": normalize.stage, "activity": normalize.activity, "b24task": normalize.b24task, "user": normalize.user}
    recs = [normalize.identity("INT-B24", r, host, upd) for r in rows] if op == "identity" else [norm[kind]("INT-B24", r, upd) for r in rows]
    notes = [f"paged result — only the first {limit} rows read (next={d.get('next')})"] if partial else []
    return {"records": recs, "source_updated_at": max([r.get("source_updated_at") or "" for r in recs] or [""]) or None, "identity": {"portal": host, "verified": bool(cfg.get("portal_domain"))},
            "partial": partial, "notes": notes, "kind": kind, "total": d.get("total")}
