# -*- coding: utf-8 -*-
"""WHATSAPP CLOUD API WEBHOOK — verified handshake, HMAC-SHA256 signature validation, tenant check, idempotent ingestion, replay
protection, malformed-payload rejection, secret redaction. Pure functions (testable without a network) plus a minimal stdlib
listener for activation (`serve`) that is NEVER started automatically: public HTTPS reachability (reverse proxy / tunnel) is
deployment configuration, not product logic.

    handshake(query, cfg)                 → challenge string (GET hub.mode=subscribe & hub.verify_token) or raises SIGNATURE_INVALID
    verify_signature(body, header, cfg)   → True or raises SIGNATURE_INVALID (X-Hub-Signature-256 = sha256=<hmac>)
    ingest(body, headers, cfg)            → {"accepted": n, "duplicates": n, "rejected": [...], "messages": [...], "statuses": [...]}
Stored evidence per inbound message: provider message id, sender id/name, timestamp, type, reply context, attachment metadata,
short excerpt (≤300 chars). Never the full history; the log lives in the local store (channel_events), never in Git."""
import sys, pathlib, json, hmac, hashlib, datetime, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
from contracts import IntegrationError
import adapter_whatsapp as W, int_secrets as _secrets

REPLAY_WINDOW_SECONDS = 7 * 24 * 3600

def handshake(query, cfg=None):
    cfg = W._cfg(cfg); q = {str(k): (v[0] if isinstance(v, list) else v) for k, v in (query or {}).items()}
    if q.get("hub.mode") != "subscribe": raise IntegrationError("BAD_PARAMS", "handshake requires hub.mode=subscribe")
    if not hmac.compare_digest(str(q.get("hub.verify_token") or ""), str(cfg["verify_token"])): raise IntegrationError("SIGNATURE_INVALID", "verify_token mismatch — handshake rejected")
    ch = str(q.get("hub.challenge") or "")
    if not ch: raise IntegrationError("BAD_PARAMS", "handshake without hub.challenge")
    try:
        import health; health.update("INT-WA", lambda h: h.__setitem__("callback_verified_at", datetime.datetime.now().isoformat(timespec="seconds")))
    except Exception: pass
    return ch

def verify_signature(body, header, cfg=None):
    cfg = W._cfg(cfg); raw = body if isinstance(body, (bytes, bytearray)) else str(body).encode("utf-8")
    sig = str(header or "")
    if not sig.startswith("sha256="): raise IntegrationError("SIGNATURE_INVALID", "missing X-Hub-Signature-256")
    want = hmac.new(str(cfg["app_secret"]).encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig[7:].lower(), want): raise IntegrationError("SIGNATURE_INVALID", "X-Hub-Signature-256 mismatch — request rejected")
    return True

def _ts(v):
    try: return datetime.datetime.fromtimestamp(int(v)).isoformat(timespec="seconds")
    except Exception: return None

def _msg(m, contacts):
    t = m.get("type") or "unknown"; text = ""
    if t == "text": text = (m.get("text") or {}).get("body") or ""
    elif t in ("image", "document", "audio", "video", "sticker"): text = (m.get(t) or {}).get("caption") or ""
    elif t == "button": text = (m.get("button") or {}).get("text") or ""
    elif t == "interactive": i = m.get("interactive") or {}; text = ((i.get("button_reply") or i.get("list_reply") or {}).get("title")) or ""
    att = []
    if t in ("image", "document", "audio", "video", "sticker"):
        o = m.get(t) or {}; att.append({"kind": t, "name": o.get("filename"), "size": None, "mime": o.get("mime_type")})
    sender = str(m.get("from") or ""); name = next((c.get("profile", {}).get("name") for c in contacts if str(c.get("wa_id")) == sender), None)
    return {"message_id": m.get("id"), "sender_id": sender, "sender_name": name or "", "received": _ts(m.get("timestamp")), "message_type": t, "text": text, "reply_to": (m.get("context") or {}).get("id"), "attachments": att}

def ingest(body, headers=None, cfg=None):
    """Signed webhook body → local evidence log. Tenant mismatch → WRONG_TENANT; bad signature → SIGNATURE_INVALID; malformed → MALFORMED_RESPONSE.
    Old or already-seen events are counted as duplicates/replays (never re-ingested as new facts)."""
    cfg = W._cfg(cfg); headers = {str(k).lower(): v for k, v in (headers or {}).items()}
    raw = body if isinstance(body, (bytes, bytearray)) else str(body).encode("utf-8")
    verify_signature(raw, headers.get("x-hub-signature-256"), cfg)
    try: d = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError): raise IntegrationError("MALFORMED_RESPONSE", "webhook body is not JSON")
    if not isinstance(d, dict) or d.get("object") != "whatsapp_business_account" or not isinstance(d.get("entry"), list): raise IntegrationError("MALFORMED_RESPONSE", "not a whatsapp_business_account event")
    waba = str(cfg.get("business_account_id") or ""); pnid = str(cfg["phone_number_id"]); allowed = W._ids(cfg.get("allowed_numbers")); observe = bool(cfg.get("observe_unknown"))
    import engine; st = engine._store(); now = datetime.datetime.now(); out = {"accepted": 0, "duplicates": 0, "replays": 0, "rejected": [], "messages": [], "statuses": []}
    for e in d["entry"]:
        if not isinstance(e, dict): out["rejected"].append("entry not an object"); continue
        if waba and str(e.get("id")) != waba: raise IntegrationError("WRONG_TENANT", f"event for a foreign business account …{str(e.get('id'))[-4:]}")
        for ch in e.get("changes") or []:
            v = (ch or {}).get("value") or {}
            if str((v.get("metadata") or {}).get("phone_number_id")) != pnid: raise IntegrationError("WRONG_TENANT", "event for a foreign phone_number_id")
            contacts = v.get("contacts") or []
            for m in v.get("messages") or []:
                if not isinstance(m, dict) or not m.get("id") or not m.get("from") or not m.get("timestamp"): out["rejected"].append("message lacks id/from/timestamp"); continue
                r = _msg(m, contacts)
                try: age = (now - datetime.datetime.fromtimestamp(int(m["timestamp"]))).total_seconds()
                except Exception: age = 0
                if age > REPLAY_WINDOW_SECONDS: out["replays"] += 1; continue
                sender = re.sub(r"\D", "", r["sender_id"]); trusted = sender in allowed
                if not trusted and not observe: out["rejected"].append(f"sender …{sender[-4:]} not on the allowlist (dropped)"); continue
                res = st.record("channel_events", f"INT-WA:msg:{r['message_id']}", {"channel": "INT-WA", "kind": "message", "message_id": r["message_id"], "sender_id": r["sender_id"], "sender_name": r["sender_name"], "received": r["received"], "message_type": r["message_type"], "reply_to": r["reply_to"], "attachments": r["attachments"], "excerpt": (r["text"] or "")[:300], "trusted": trusted})
                if res["status"] == "RECORDED": out["accepted"] += 1; out["messages"].append({k: r[k] for k in ("message_id", "sender_id", "received", "message_type")} | {"trusted": trusted})
                else: out["duplicates"] += 1
            for s in v.get("statuses") or []:
                if not isinstance(s, dict) or not s.get("id") or not s.get("status"): out["rejected"].append("status lacks id/status"); continue
                err = None
                if s.get("errors"): e0 = s["errors"][0] if isinstance(s["errors"], list) and s["errors"] else {}; err = f"{e0.get('code')}: {_secrets.redact(str(e0.get('title') or e0.get('message') or ''))[:120]}"
                res = st.record("channel_events", f"INT-WA:status:{s['id']}:{s['status']}", {"channel": "INT-WA", "kind": "status", "message_id": s["id"], "recipient_id": s.get("recipient_id"), "status": s["status"], "at": _ts(s.get("timestamp")), "error": err})
                if res["status"] == "RECORDED": out["accepted"] += 1; out["statuses"].append({"message_id": s["id"], "status": s["status"], "error": err})
                else: out["duplicates"] += 1
    return out

def serve(cfg=None, host=None, port=None, path=None):
    """Minimal stdlib listener for activation (run explicitly by Gev/ops; behind a reverse proxy/tunnel for public HTTPS). Never auto-started."""
    import http.server, urllib.parse
    cfg = W._cfg(cfg); host = host or cfg.get("webhook_host") or "127.0.0.1"; port = int(port or cfg.get("webhook_port") or 8788); route = path or cfg.get("webhook_path") or "/webhooks/whatsapp"
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, text):
            b = text.encode("utf-8"); self.send_response(code); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path != route: return self._send(404, "not found")
            try: return self._send(200, handshake(urllib.parse.parse_qs(u.query), cfg))
            except IntegrationError as e: return self._send(403, e.code)
        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if u.path != route: return self._send(404, "not found")
            n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n)
            try: r = ingest(body, dict(self.headers.items()), cfg); return self._send(200, json.dumps({k: r[k] for k in ("accepted", "duplicates", "replays")}))
            except IntegrationError as e: return self._send({"SIGNATURE_INVALID": 403, "WRONG_TENANT": 403}.get(e.code, 400), e.code)
    srv = http.server.ThreadingHTTPServer((host, port), H)
    print(f"WhatsApp webhook listener on http://{host}:{port}{route} (expose via reverse proxy/tunnel as public HTTPS; Ctrl+C to stop)")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: srv.server_close()

if __name__ == "__main__":
    serve()
