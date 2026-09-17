# -*- coding: utf-8 -*-
"""ADAPTER INT-WA — WhatsApp Business official Cloud API (graph.facebook.com), READ side.
Inbound messages and delivery statuses arrive ONLY through the verified webhook (whatsapp_webhook.py) and are kept in the local
evidence log (store table channel_events: ids, sender ref, timestamp, type, short excerpt, statuses). `chat.messages` /
`chat.statuses` read that log — the provider has no historical read-back for inbound messages, so the minimum evidence is kept
locally and never versioned. `identity` verifies the business phone from the provider (display number / verified name).
No WhatsApp Web, no browser automation, no QR sessions. Secrets stay outside Git and are redacted from every error."""
import sys, pathlib, json, urllib.request, urllib.error, socket, datetime, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
from contracts import IntegrationError
import normalize, int_secrets as _secrets

OPS = {"identity": "chat_identity", "chat.messages": "chat_message", "chat.statuses": "chat_status"}
GRAPH = "https://graph.facebook.com/v20.0"
REQUIRED = ("access_token", "phone_number_id", "verify_token", "app_secret")

def default_transport(url, body=None, headers=None, timeout=25):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET", headers={"Content-Type": "application/json", "User-Agent": "Deputy-Command-center", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try: t = e.read().decode("utf-8", "replace")
        except Exception: t = ""
        return e.code, t
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
        raise IntegrationError("UNAVAILABLE", f"WhatsApp Cloud API unreachable: {_secrets.redact(str(e))[:160]}", retryable=True)

def _cfg(cfg):
    cfg = cfg if cfg is not None else _secrets.load_config("INT-WA")
    missing = [k for k in REQUIRED if not str(cfg.get(k) or "").strip()]
    if missing: raise IntegrationError("NOT_CONFIGURED", f"INT-WA missing config {missing} (CC_INT_WA_* or ~/.command-center/integrations/INT-WA.json)")
    _secrets.register({k: cfg[k] for k in ("access_token", "verify_token", "app_secret")}, "INT-WA")
    return cfg

def _ids(v):
    if v is None or v == "": return set()
    if isinstance(v, (list, tuple, set)): return {re.sub(r"\D", "", str(x)) for x in v if str(x).strip()}
    return {re.sub(r"\D", "", x) for x in str(v).split(",") if x.strip()}

def call(path, body=None, cfg=None, transport=None, method="GET"):
    cfg = _cfg(cfg); url = f"{GRAPH}/{path}"
    status, text = (transport or default_transport)(url, body, {"Authorization": f"Bearer {cfg['access_token']}"})
    if status >= 500: raise IntegrationError("UNAVAILABLE", f"Cloud API error http {status}", retryable=True)
    try: d = json.loads(text) if text else {}
    except ValueError: raise IntegrationError("MALFORMED_RESPONSE", f"non-JSON response (http {status}): {_secrets.redact(text)[:80]}")
    if not isinstance(d, dict): raise IntegrationError("MALFORMED_RESPONSE", "response is not an object")
    err = d.get("error") if isinstance(d.get("error"), dict) else None
    if status == 401 or (err and err.get("code") in (190,)): raise IntegrationError("AUTH_FAILED", f"401/190: {_secrets.redact(str((err or {}).get('message')))[:120]}")
    if status == 403 or (err and err.get("code") in (10, 200, 3)): raise IntegrationError("PERMISSION_DENIED", f"403: {_secrets.redact(str((err or {}).get('message')))[:120]}")
    if status == 429 or (err and err.get("code") in (4, 80007, 130429)): raise IntegrationError("RATE_LIMITED", "rate limited", retryable=True)
    if status >= 500: raise IntegrationError("UNAVAILABLE", f"Cloud API error http {status}", retryable=True)
    if err: raise IntegrationError("UNAVAILABLE", f"{err.get('code')}: {_secrets.redact(str(err.get('message')))[:120]}")
    if status != 200: raise IntegrationError("UNAVAILABLE", f"unexpected http {status}")
    return d

def identity(cfg=None, transport=None):
    cfg = _cfg(cfg); d = call(f"{cfg['phone_number_id']}?fields=display_phone_number,verified_name,id", None, cfg, transport)
    if "id" not in d: raise IntegrationError("SCHEMA_CHANGED", "phone number object lacks id")
    if str(d.get("id")) != str(cfg["phone_number_id"]): raise IntegrationError("WRONG_TENANT", "provider returned a different phone_number_id")
    exp = re.sub(r"\D", "", str(cfg.get("expected_display_phone") or "")); got = re.sub(r"\D", "", str(d.get("display_phone_number") or ""))
    if exp and got and exp != got: raise IntegrationError("WRONG_TENANT", f"display phone ends …{got[-4:]} ≠ expected …{exp[-4:]}")
    return {"account_id": str(d["id"]), "display": f"{d.get('verified_name') or ''} {d.get('display_phone_number') or ''}".strip(), "verified": bool(exp), "note": None if exp else "expected_display_phone not configured — identity observed, not verified"}

def _store():
    import engine; return engine._store()

def read(op, params=None, cfg=None, transport=None):
    params = params or {}
    if op not in OPS: raise IntegrationError("UNKNOWN_OPERATION", f"INT-WA has no operation {op}")
    cfg = _cfg(cfg); now = datetime.datetime.now().isoformat(timespec="seconds")
    if op == "identity":
        ident = identity(cfg, transport)
        return {"records": [normalize.chat_identity("INT-WA", ident, now)], "source_updated_at": now, "identity": {"addresses": [ident["display"]], "verified": ident["verified"], "note": ident.get("note")}, "partial": False, "notes": [], "kind": "chat_identity"}
    limit = int(params.get("limit") or 100)
    if limit < 1 or limit > 500: raise IntegrationError("BAD_PARAMS", "limit must be 1..500")
    rows = _store().list("channel_events", where="op_id LIKE ?", args=("INT-WA:%",))
    if op == "chat.messages":
        msgs = [r for r in rows if r.get("kind") == "message"]
        if params.get("since"): msgs = [r for r in msgs if (r.get("received") or "") >= str(params["since"])]
        msgs = sorted(msgs, key=lambda r: r.get("received") or "")[-limit:]
        recs = [normalize.chat_message("INT-WA", {"chat_id": r.get("sender_id"), "chat_title": r.get("sender_name"), "message_id": r.get("message_id"), "sender_id": r.get("sender_id"), "sender_name": r.get("sender_name"), "text": r.get("excerpt"), "message_type": r.get("message_type"), "reply_to": r.get("reply_to"), "received": r.get("received"), "attachments": r.get("attachments") or [], "trusted": r.get("trusted")}, now) for r in msgs]
        return {"records": recs, "source_updated_at": max([r.get("source_updated_at") or "" for r in recs] or [""]) or None, "identity": None, "partial": len(msgs) >= limit, "notes": ["inbound messages come from the verified webhook log (provider has no historical read-back)"], "kind": "chat_message", "retrieved_at": now}
    sts = [r for r in rows if r.get("kind") == "status"]
    if params.get("message_id"): sts = [r for r in sts if r.get("message_id") == params["message_id"]]
    sts = sorted(sts, key=lambda r: r.get("at") or "")[-limit:]
    recs = [normalize.chat_status("INT-WA", {"message_id": r.get("message_id"), "recipient_id": r.get("recipient_id"), "status": r.get("status"), "at": r.get("at"), "error": r.get("error")}, now) for r in sts]
    return {"records": recs, "source_updated_at": max([r.get("source_updated_at") or "" for r in recs] or [""]) or None, "identity": None, "partial": False, "notes": [], "kind": "chat_status", "retrieved_at": now}

def probe(cfg=None, transport=None): return identity(cfg, transport)
