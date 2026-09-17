# -*- coding: utf-8 -*-
"""WRITE ADAPTER INT-WA — outbound WhatsApp Cloud API messages: `chat.send_text` (free-form, only inside the provider's reply window)
and `chat.send_template` (approved template + variables). Reached ONLY by the Action Runtime after Gev's approval; recipient,
message/template and variables are bound to the approval fingerprint. A template is never silently substituted for a text message.
VERIFICATION is asynchronous and provider-evidenced: the send returns a message id (wamid) = provider acceptance; delivery evidence
(sent/delivered/read/failed) arrives later through the verified webhook. verify() returns pending=True until a status exists →
the runtime records EXECUTED_UNVERIFIED with code AWAITING_PROVIDER_STATUS; reconcile → find_existing reads the statuses → VERIFIED
(delivered/read/sent) or FAILED evidence. No blind retry."""
import sys, pathlib, datetime, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
import adapter_whatsapp as R
from contracts import IntegrationError

OPS = ("chat.send_text", "chat.send_template")
GOOD = ("sent", "delivered", "read")

def _err():
    from actions import ProviderError, ProviderUnknown; return ProviderError, ProviderUnknown

def _digits(v): return re.sub(r"\D", "", str(v or ""))

def _allowed(cfg, to): return _digits(to) in R._ids(cfg.get("allowed_numbers"))

def precondition(op, params):
    ProviderError, _ = _err()
    try: cfg = R._cfg(None)
    except IntegrationError as e: raise ProviderError(f"{e.code}: {e.reason}")
    to = _digits(params.get("to"))
    if not to: return {"exists": False, "object": None}
    if not _allowed(cfg, to): raise ProviderError(f"PERMISSION_DENIED: recipient …{to[-4:]} is not on the configured allowed_numbers — no outbound message to unknown numbers")
    return {"exists": True, "object": {"to": f"…{to[-4:]}", "allowed": True}}

def _statuses(mid):
    try:
        import engine; st = engine._store()
        rows = [r for r in st.list("channel_events", where="op_id LIKE ?", args=(f"INT-WA:status:{mid}:%",))]
        return sorted(rows, key=lambda r: r.get("at") or "")
    except Exception: return []

def _outbound_by_key(key):
    try:
        import engine; st = engine._store()
        for r in st.list("channel_events", where="op_id LIKE ?", args=("INT-WA:out:%",)):
            if r.get("idem_key") == key and r.get("provider_message_id"): return r
    except Exception: pass
    return None

def find_existing(op, params):
    """Reconciliation: an outbound record for the same idempotency key + provider statuses = the message exists (never send twice)."""
    o = _outbound_by_key(params.get("_idem_key"))
    if not o: return None
    sts = _statuses(o["provider_message_id"]); last = sts[-1]["status"] if sts else None
    return {"id": o["provider_message_id"], "provider_accepted": True, "last_status": last, "statuses": [{"status": s.get("status"), "at": s.get("at"), "error": s.get("error")} for s in sts], "at": o.get("at")}

def execute(op, params):
    ProviderError, ProviderUnknown = _err()
    if op not in OPS: raise ProviderError(f"unknown WhatsApp operation {op}")
    try: cfg = R._cfg(None)
    except IntegrationError as e: raise ProviderError(f"{e.code}: {e.reason}")
    to = _digits(params.get("to"))
    if not to: raise ProviderError("BAD_PARAMS: recipient 'to' required")
    if not _allowed(cfg, to): raise ProviderError(f"PERMISSION_DENIED: recipient …{to[-4:]} not on allowed_numbers")
    body = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to}
    if op == "chat.send_text":
        text = str(params.get("text") or "")
        if not text: raise ProviderError("BAD_PARAMS: text required")
        body["type"] = "text"; body["text"] = {"preview_url": False, "body": text[:4096]}
        if params.get("reply_to_message_id"): body["context"] = {"message_id": str(params["reply_to_message_id"])}
    else:
        name = str(params.get("template") or ""); lang = str(params.get("language") or "en")
        if not name: raise ProviderError("BAD_PARAMS: template name required")
        comps = []
        vals = params.get("variables") or []
        if vals: comps.append({"type": "body", "parameters": [{"type": "text", "text": str(v)} for v in vals]})
        body["type"] = "template"; body["template"] = {"name": name, "language": {"code": lang}, "components": comps}
    at = datetime.datetime.now().isoformat(timespec="seconds")
    try: res = R.call(f"{cfg['phone_number_id']}/messages", body, cfg, params.get("_transport"), method="POST")
    except IntegrationError as e:
        if e.code in ("UNAVAILABLE", "TIMEOUT", "RATE_LIMITED"): raise ProviderUnknown(f"{e.code}: {e.reason} — the message may or may not have been accepted")
        raise ProviderError(f"{e.code}: {e.reason}")
    msgs = res.get("messages") if isinstance(res, dict) else None
    mid = str((msgs[0] or {}).get("id") or "") if isinstance(msgs, list) and msgs else ""
    if not mid: raise ProviderUnknown("Cloud API accepted the request but returned no message id — outcome unknown")
    try:
        import engine; engine._store().record("channel_events", f"INT-WA:out:{mid}", {"channel": "INT-WA", "kind": "outbound", "to": f"…{to[-4:]}", "provider_message_id": mid, "idem_key": params.get("_idem_key"), "at": at, "op": op, "excerpt": (params.get("text") or params.get("template") or "")[:300]})
    except Exception: pass
    return {"ok": True, "id": mid, "to": f"…{to[-4:]}", "at": at, "provider_accepted": True}

def verify(op, params, result):
    """Provider delivery status is the independent evidence; until it arrives the send is pending (never assumed delivered)."""
    mid = (result or {}).get("id")
    sts = _statuses(mid) if mid else []
    if not sts: return {"verified": False, "pending": True, "reason": "AWAITING_PROVIDER_STATUS — provider accepted the message (wamid) but no delivery status event has arrived yet; reconcile later, never retry blindly", "evidence": {"provider_message_id": mid, "statuses": []}}
    last = sts[-1]
    if last.get("status") == "failed": return {"verified": False, "pending": False, "reason": f"provider reported FAILED: {last.get('error') or 'no detail'}", "evidence": {"provider_message_id": mid, "statuses": [{"status": s.get("status"), "at": s.get("at"), "error": s.get("error")} for s in sts]}}
    ok = any(s.get("status") in GOOD for s in sts)
    return {"verified": ok, "pending": not ok, "reason": (f"provider status {last.get('status')} at {last.get('at')}" if ok else f"status {last.get('status')} is not delivery evidence yet"), "evidence": {"provider_message_id": mid, "statuses": [{"status": s.get("status"), "at": s.get("at"), "error": s.get("error")} for s in sts]}}
