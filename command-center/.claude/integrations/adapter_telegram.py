# -*- coding: utf-8 -*-
"""ADAPTER INT-TG — Telegram official Bot API (https://api.telegram.org/bot<token>/<method>), READ side.
No client session, no scraping, no UI automation. Long polling (getUpdates) by default so no public webhook is needed; webhook mode
is supported through `webhook_ingest()` (secret-token header check). The bot token lives OUTSIDE Git (int_secrets) and is
redacted from every error. Message content is UNTRUSTED DATA: it is normalized into records and flagged `trusted` only when the
chat/user is on the configured allowlist — it can never become an instruction or an approval.
Offset safety: every update is deduplicated by update_id in the local store (channel_events) and the confirmed offset is
acknowledged to Telegram (getUpdates offset) and persisted in the store's meta table, so a restart never replays old updates as new."""
import sys, pathlib, json, urllib.request, urllib.error, socket, re, datetime, hashlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
from contracts import IntegrationError
import normalize, int_secrets as _secrets

OPS = {"identity": "chat_identity", "chat.messages": "chat_message", "business.connection": "chat_connection"}
API = "https://api.telegram.org"
TOKEN_RX = re.compile(r"bot\d{6,}:[A-Za-z0-9_-]{20,}")
OFFSET_KEY = "tg_update_offset"
CONNECTION_KEY = "tg_business_connection"
# ONE canonical update stream: bot-chat and business updates share the same offset and the same update_id dedupe, so a restart
# never replays business messages as fresh and a single update can never create two commitments.
ALLOWED_UPDATES = ["message", "edited_message", "channel_post",
                   "business_connection", "business_message", "edited_business_message", "deleted_business_messages"]
RIGHT_FIELDS = ("can_reply", "can_read_messages", "can_delete_sent_messages", "can_delete_all_messages",
                "can_edit_messages", "can_post_stories", "can_edit_stories", "can_delete_stories")

def default_transport(url, body=None, timeout=35):
    """POST JSON (or GET). Returns (http_status, text). Token in the URL is redacted from every raised error."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET", headers={"Content-Type": "application/json", "User-Agent": "Deputy-Command-center"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try: body_t = e.read().decode("utf-8", "replace")
        except Exception: body_t = ""
        return e.code, body_t
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
        raise IntegrationError("UNAVAILABLE", f"Telegram API unreachable: {redact(str(e))[:160]}", retryable=True)

def redact(text): return TOKEN_RX.sub("bot<secret>", _secrets.redact(text))

def _cfg(cfg):
    cfg = cfg if cfg is not None else _secrets.load_config("INT-TG")
    tok = str(cfg.get("bot_token") or "").strip()
    if not tok: raise IntegrationError("NOT_CONFIGURED", "no bot_token for INT-TG (CC_INT_TG_BOT_TOKEN or ~/.command-center/integrations/INT-TG.json)")
    if not re.match(r"^\d{6,}:[A-Za-z0-9_-]{20,}$", tok): raise IntegrationError("NOT_CONFIGURED", "bot_token has an unexpected shape")
    _secrets.register({"bot_token": tok}, "INT-TG")
    return cfg

def _ids(v):
    if v is None or v == "": return set()
    if isinstance(v, (list, tuple, set)): return {str(x).strip() for x in v if str(x).strip()}
    return {x.strip() for x in str(v).split(",") if x.strip()}

def call(method, params=None, cfg=None, transport=None):
    cfg = _cfg(cfg); url = f"{API}/bot{cfg['bot_token']}/{method}"
    status, text = (transport or default_transport)(url, params or {})
    if status >= 500: raise IntegrationError("UNAVAILABLE", f"Telegram API error http {status}", retryable=True)
    try: d = json.loads(text) if text else {}
    except ValueError: raise IntegrationError("MALFORMED_RESPONSE", f"non-JSON response (http {status}): {redact(text)[:80]}")
    if not isinstance(d, dict): raise IntegrationError("MALFORMED_RESPONSE", "response is not an object")
    if status == 401 or (d.get("error_code") == 401): raise IntegrationError("AUTH_FAILED", f"401: {redact(str(d.get('description')))[:120]}")
    if status == 403 or d.get("error_code") == 403: raise IntegrationError("PERMISSION_DENIED", f"403: {redact(str(d.get('description')))[:120]}")
    if status == 429 or d.get("error_code") == 429: raise IntegrationError("RATE_LIMITED", f"429: retry after {((d.get('parameters') or {}).get('retry_after'))}", retryable=True)
    if status >= 500: raise IntegrationError("UNAVAILABLE", f"Telegram API error http {status}", retryable=True)
    if not d.get("ok"): raise IntegrationError("UNAVAILABLE", f"{d.get('error_code')}: {redact(str(d.get('description')))[:120]}")
    if "result" not in d: raise IntegrationError("SCHEMA_CHANGED", "response without 'result'")
    return d["result"]

def connection_ref(cid):
    """Short, non-reversible reference to a business connection id. The id itself is an operational secret: it never enters a
    record, an envelope, an audit line or a report."""
    return "bc-" + hashlib.sha256(str(cid or "").encode("utf-8")).hexdigest()[:10]


def _connection_load():
    try:
        con = _store()._connect()
        try:
            row = con.execute("SELECT value FROM meta WHERE key=?", (CONNECTION_KEY,)).fetchone()
            return json.loads(row[0]) if row else None
        finally:
            con.close()
    except Exception:
        return None


def _connection_store(state):
    con = _store()._connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (CONNECTION_KEY, json.dumps(state, ensure_ascii=False)))
        con.execute("COMMIT")
    finally:
        con.close()


def current_connection():
    """Latest observed connection state (read-only accessor used by the outbound fail-closed gate)."""
    return _connection_load()


def _connection_fields(bc):
    u = bc.get("user") or {}
    if isinstance(bc.get("rights"), dict):
        rights = bc["rights"]
    elif "can_reply" in bc:
        rights = {"can_reply": bool(bc.get("can_reply"))}      # pre-9.0 shape, still accepted
    else:
        rights = {}
    ts = bc.get("date")
    connected_at = datetime.datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds") if isinstance(ts, (int, float)) else None
    return {"id": str(bc.get("id") or ""), "connection_ref": connection_ref(bc.get("id")),
            "account_user_id": str(u.get("id") or ""), "user_chat_id": str(bc.get("user_chat_id") or ""),
            "account_display": " ".join(x for x in (u.get("first_name"), u.get("last_name")) if x) or u.get("username") or "",
            "connected_at": connected_at,
            "rights": {k: bool(rights.get(k)) for k in RIGHT_FIELDS if k in rights},
            "is_enabled": bool(bc.get("is_enabled")),
            "observed_at": datetime.datetime.now().isoformat(timespec="seconds")}


def record_connection(bc, cfg=None):
    """Persist the latest business connection state. A replaced id or a disabled connection is kept explicitly, so the business
    path FAILS CLOSED until the current state is re-read and verified."""
    cfg = _cfg(cfg)
    state = _connection_fields(bc)
    exp = str(cfg.get("business_account_user_id") or "").strip()
    if exp and state["account_user_id"] and state["account_user_id"] != exp:
        raise IntegrationError("WRONG_TENANT", "business connection belongs to a different Telegram account than the configured owner")
    prev = _connection_load()
    state["replaced_previous"] = bool(prev and prev.get("id") and prev["id"] != state["id"])
    _connection_store(state)
    _store().record("channel_events", "INT-TG:bc:%s:%s" % (state["connection_ref"], state["observed_at"]),
                    {"channel": "INT-TG", "kind": "business_connection", "connection_ref": state["connection_ref"],
                     "account_user_id": state["account_user_id"], "user_chat_id": state["user_chat_id"],
                     "is_enabled": state["is_enabled"], "rights": state["rights"], "connected_at": state["connected_at"],
                     "observed_at": state["observed_at"], "replaced_previous": state["replaced_previous"]})
    return state


def connection_state(cfg=None, transport=None, refresh=False):
    """Current business connection state. refresh=True re-reads it from the provider (getBusinessConnection) - the only way a
    stale local view becomes trusted again after a disable or a replacement."""
    st = _connection_load()
    if refresh and st and st.get("id"):
        cfg = _cfg(cfg)
        bc = call("getBusinessConnection", {"business_connection_id": st["id"]}, cfg, transport)
        if not isinstance(bc, dict) or "id" not in bc:
            raise IntegrationError("SCHEMA_CHANGED", "getBusinessConnection returned no connection object")
        st = record_connection(bc, cfg)
    return st


def business_active(cfg=None):
    """(active, reason). Business evidence is trusted ONLY through an active, verified connection."""
    st = _connection_load()
    if not st:
        return False, "no business connection observed yet - connect the bot on the account (Settings > Telegram Business > Chatbots)"
    if not st.get("is_enabled"):
        return False, "the business connection is DISABLED at the provider - re-verify with getBusinessConnection before trusting business messages"
    return True, None


def identity(cfg=None, transport=None):
    cfg = _cfg(cfg); me = call("getMe", {}, cfg, transport)
    if not isinstance(me, dict) or "id" not in me or "username" not in me: raise IntegrationError("SCHEMA_CHANGED", "getMe result lacks id/username")
    exp = str(cfg.get("expected_bot_username") or "").lstrip("@").lower()
    if exp and str(me.get("username", "")).lower() != exp: raise IntegrationError("WRONG_TENANT", f"bot @{me.get('username')} ≠ expected @{exp}")
    return {"account_id": str(me["id"]), "display": f"@{me.get('username')}", "verified": bool(exp), "is_bot": bool(me.get("is_bot")), "note": None if exp else "expected_bot_username not configured — identity observed, not verified"}

def _store():
    import engine; return engine._store()

def _offset_get():
    try:
        con = _store()._connect()
        try:
            row = con.execute("SELECT value FROM meta WHERE key=?", (OFFSET_KEY,)).fetchone(); return int(row[0]) if row else None
        finally: con.close()
    except Exception: return None

def _offset_store(v):
    con = _store()._connect()
    try:
        con.execute("BEGIN IMMEDIATE"); con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (OFFSET_KEY, str(int(v)))); con.execute("COMMIT")
    finally: con.close()

def _attachments(m):
    out = []
    for k in ("document", "photo", "audio", "video", "voice", "sticker", "animation"):
        v = m.get(k)
        if v is None: continue
        if k == "photo" and isinstance(v, list): v = v[-1] if v else {}
        if isinstance(v, dict): out.append({"kind": k, "name": v.get("file_name"), "size": v.get("file_size"), "mime": v.get("mime_type")})
    return out

def parse_message(u, cfg):
    """One Telegram update -> raw chat message dict (or None for a non-message update). Trust is decided ONLY by Deputy's own
    allowlists. For a business message the Telegram-side recipient scope is NOT authority: the sender must also be on Deputy's
    business allowlist AND the connection must be active and the same one."""
    business = ("business_message" in u) or ("edited_business_message" in u)
    m = (u.get("message") or u.get("edited_message") or u.get("channel_post")
         or u.get("business_message") or u.get("edited_business_message"))
    if not isinstance(m, dict): return None
    chat = m.get("chat") or {}; frm = m.get("from") or {}
    chat_id = str(chat.get("id", "")); user_id = str(frm.get("id", ""))
    if business:
        bcid = str(m.get("business_connection_id") or "")
        st = _connection_load(); active, _why = business_active(cfg)
        same = bool(st and st.get("id") and bcid and st["id"] == bcid)
        trusted = bool(active and same and user_id in _ids(cfg.get("business_allowed_user_ids")))
        mode, ref = "BUSINESS", connection_ref(bcid)
    else:
        allowed_chats, allowed_users = _ids(cfg.get("allowed_chat_ids")), _ids(cfg.get("allowed_user_ids"))
        trusted = (chat_id in allowed_chats) or (user_id in allowed_users and chat.get("type") == "private")
        mode, ref = "BOT_CHAT", None
    ts = m.get("date"); received = datetime.datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds") if isinstance(ts, (int, float)) else None
    return {"source_mode": mode, "business_connection_ref": ref, "deleted": False, "chat_id": chat_id, "chat_title": chat.get("title") or (" ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x)) or chat.get("username"), "message_id": m.get("message_id"),
            "sender_id": user_id, "sender_name": " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x) or frm.get("username") or "",
            # SAFE human-readable identity metadata, kept SEPARATE so Deputy never asks Gev to decode a raw numeric id.
            # These are presentation fields only: a username or a name is NEVER identity evidence on its own.
            "sender_username": frm.get("username"), "sender_first_name": frm.get("first_name"), "sender_last_name": frm.get("last_name"),
            "text": m.get("text") or m.get("caption") or "",
            "message_type": "text" if m.get("text") else ("caption" if m.get("caption") else next((k for k in ("document", "photo", "audio", "video", "voice", "sticker", "animation", "location", "contact") if m.get(k)), "other")),
            "reply_to": str((m.get("reply_to_message") or {}).get("message_id") or "") or None, "received": received, "attachments": _attachments(m), "trusted": trusted, "update_id": u.get("update_id"),
            "edited": ("edited_message" in u) or ("edited_business_message" in u)}


def parse_deletions(u, cfg):
    """deleted_business_messages -> a deletion event. A deletion is evidence that the source changed; by itself it never fulfils
    or cancels anything."""
    d = u.get("deleted_business_messages")
    if not isinstance(d, dict): return None
    chat = d.get("chat") or {}
    bcid = str(d.get("business_connection_id") or ""); st = _connection_load()
    return {"source_mode": "BUSINESS", "business_connection_ref": connection_ref(bcid), "chat_id": str(chat.get("id", "")),
            "message_ids": [str(x) for x in (d.get("message_ids") or [])], "update_id": u.get("update_id"),
            "same_connection": bool(st and st.get("id") and bcid and st["id"] == bcid),
            "at": datetime.datetime.now().isoformat(timespec="seconds")}

def _dedupe(records, channel="INT-TG"):
    """Persist each update once (INSERT OR IGNORE by update id) — the local evidence log carries ids, sender refs, timestamps and a short excerpt only."""
    st = _store(); fresh = []
    for r in records:
        oid = f"{channel}:upd:{r.get('update_id')}"
        res = st.record("channel_events", oid, {"channel": channel, "kind": "message", "update_id": r.get("update_id"), "chat_id": r["chat_id"], "message_id": r["message_id"], "sender_id": r["sender_id"], "received": r["received"], "trusted": r["trusted"], "excerpt": str(r.get("text") or "")[:300], "message_type": r["message_type"],
                                                "source_mode": r.get("source_mode", "BOT_CHAT"),
                                                "business_connection_ref": r.get("business_connection_ref"),
                                                "edited": bool(r.get("edited"))})
        if res["status"] == "RECORDED": fresh.append(r)
    return fresh

def _apply_edits(fresh):
    """An EDITED business message reaches the evidence lifecycle: the original quote is preserved, confidence drops, and a
    material change of the promise text is surfaced as a contradiction. Never a silent overwrite."""
    touched = 0
    try:
        import commitments as CM
    except Exception:
        return {"edited": 0, "commitments_touched": 0}
    edits = [r for r in fresh if r.get("edited") and r.get("source_mode") == "BUSINESS"]
    for r in edits:
        rec_id = normalize.rid("INT-TG", "%s|%s" % (r["chat_id"], r["message_id"]))
        try:
            res = CM.source_changed(rec_id, channel="INT-TG", state="EDITED", new_text=r.get("text"), at=r.get("received"))
            touched += len((res or {}).get("affected") or [])
        except Exception:
            pass
    return {"edited": len(edits), "commitments_touched": touched}


def _apply_deletions(deletions):
    """Record each deletion once and hand it to the commitment evidence lifecycle. A deleted message NEVER fulfils or cancels a
    promise: the prior evidence is preserved and marked, and a material change is surfaced for Gev."""
    if not deletions: return {"events": 0, "messages": 0, "commitments_touched": 0}
    st = _store(); events = msgs = touched = 0
    for d in deletions:
        oid = "INT-TG:del:%s" % d.get("update_id")
        res = st.record("channel_events", oid, {"channel": "INT-TG", "kind": "deleted", "update_id": d.get("update_id"), "chat_id": d["chat_id"],
                                                "message_ids": d["message_ids"], "source_mode": "BUSINESS",
                                                "business_connection_ref": d.get("business_connection_ref"),
                                                "same_connection": d.get("same_connection"), "at": d.get("at")})
        if res["status"] != "RECORDED": continue
        events += 1; msgs += len(d["message_ids"])
        try:
            import commitments as CM
            for mid in d["message_ids"]:
                rec_id = normalize.rid("INT-TG", "%s|%s" % (d["chat_id"], mid))
                r = CM.source_changed(rec_id, channel="INT-TG", state="DELETED", at=d.get("at"))
                touched += len((r or {}).get("affected") or [])
        except Exception:
            pass
    return {"events": events, "messages": msgs, "commitments_touched": touched}


def read(op, params=None, cfg=None, transport=None):
    params = params or {}
    if op not in OPS: raise IntegrationError("UNKNOWN_OPERATION", f"INT-TG has no operation {op}")
    cfg = _cfg(cfg); now = datetime.datetime.now().isoformat(timespec="seconds")
    if op == "identity":
        ident = identity(cfg, transport)
        return {"records": [normalize.chat_identity("INT-TG", ident, now)], "source_updated_at": now, "identity": {"addresses": [ident["display"]], "verified": ident["verified"], "note": ident.get("note")}, "partial": False, "notes": [], "kind": "chat_identity"}
    if op == "business.connection":
        st = connection_state(cfg, transport, refresh=bool(params.get("refresh")))
        if not st:
            raise IntegrationError("NOT_CONFIGURED", "no business connection observed yet - connect the bot on the account (Settings > Telegram Business > Chatbots)")
        rec = normalize.chat_connection("INT-TG", st, now)
        active, why = business_active(cfg)
        return {"records": [rec], "source_updated_at": st.get("observed_at"), "identity": None, "partial": False,
                "notes": ([] if active else ["business connection NOT active: %s" % why]) + (["the connection id was replaced since the previous observation"] if st.get("replaced_previous") else []),
                "kind": "chat_connection", "retrieved_at": now}
    limit = int(params.get("limit") or 100)
    if limit < 1 or limit > 100: raise IntegrationError("BAD_PARAMS", "limit must be 1..100")
    if str(cfg.get("mode") or "polling").lower() == "webhook": raise IntegrationError("NOT_CONFIGURED", "INT-TG is in webhook mode: updates arrive through webhook_ingest(), not getUpdates")
    q = {"limit": limit, "timeout": int(params.get("timeout") or 0), "allowed_updates": list(ALLOWED_UPDATES)}
    off = _offset_get()
    if off is not None: q["offset"] = off
    res = call("getUpdates", q, cfg, transport)
    if not isinstance(res, list): raise IntegrationError("SCHEMA_CHANGED", "getUpdates result is not a list")
    conn_seen = []
    for u in res:
        if isinstance(u, dict) and isinstance(u.get("business_connection"), dict):
            try: conn_seen.append(record_connection(u["business_connection"], cfg))       # connection state first: it decides trust for this batch
            except IntegrationError as e: conn_seen.append({"error": "%s: %s" % (e.code, e.reason)})
    raw = [parse_message(u, cfg) for u in res if isinstance(u, dict)]; raw = [r for r in raw if r]
    deletions = [d for d in (parse_deletions(u, cfg) for u in res if isinstance(u, dict)) if d]
    if res:
        newest = max(int(u.get("update_id", 0)) for u in res if isinstance(u, dict))
        _offset_store(newest + 1)                                         # acknowledged to Telegram on the NEXT poll: never replayed after a restart
    fresh = _dedupe(raw)
    trusted = [r for r in fresh if r["trusted"]]; untrusted = [r for r in fresh if not r["trusted"]]
    observe = bool(cfg.get("observe_unknown"))
    recs = [normalize.chat_message("INT-TG", r, now) for r in (fresh if observe else trusted)]
    notes = [f"{len(untrusted)} message(s) from chats/users outside the allowlist — {'observed as UNTRUSTED (observe_unknown=true)' if observe else 'dropped (not business evidence)'}"] if untrusted else []
    ignored = len(res) - len(raw) - len(deletions) - len([c for c in conn_seen if c])
    if ignored > 0: notes.append(f"{ignored} non-message update(s) ignored")
    applied = _apply_deletions(deletions); edited_applied = _apply_edits(fresh)
    if deletions: notes.append(f"{sum(len(d['message_ids']) for d in deletions)} business message(s) deleted at the provider — evidence marked, nothing closed automatically")
    if conn_seen: notes.append(f"{len(conn_seen)} business connection update(s) observed")
    if any(r.get("source_mode") == "BUSINESS" for r in fresh):
        active, why = business_active(cfg)
        if not active: notes.append(f"business messages arrived but the connection is not active: {why}")
    return {"records": recs, "source_updated_at": max([r.get("source_updated_at") or "" for r in recs] or [""]) or None, "identity": None,
            "partial": len(res) >= limit, "notes": notes, "kind": "chat_message", "retrieved_at": now,
            "business": {"connection_updates": len([c for c in conn_seen if c and not c.get("error")]),
                         # observed = arrived on the business connection; trusted = also on Deputy's own business allowlist
                         "messages_observed": len([r for r in fresh if r.get("source_mode") == "BUSINESS"]),
                         "messages_trusted": len([r for r in trusted if r.get("source_mode") == "BUSINESS"]),
                         "edited": edited_applied,
                         "deletions": applied}}

def webhook_ingest(payload, headers=None, cfg=None):
    """Webhook mode ingestion: the X-Telegram-Bot-Api-Secret-Token header must equal the configured webhook_secret; then the update is deduplicated exactly like polling."""
    cfg = _cfg(cfg); headers = {str(k).lower(): v for k, v in (headers or {}).items()}
    secret = str(cfg.get("webhook_secret") or "")
    if not secret: raise IntegrationError("NOT_CONFIGURED", "webhook mode needs webhook_secret")
    if headers.get("x-telegram-bot-api-secret-token") != secret: raise IntegrationError("SIGNATURE_INVALID", "webhook secret token mismatch — update rejected")
    if not isinstance(payload, dict) or "update_id" not in payload: raise IntegrationError("MALFORMED_RESPONSE", "update lacks update_id")
    r = parse_message(payload, cfg)
    if not r: return {"accepted": False, "reason": "non-message update"}
    fresh = _dedupe([r])
    return {"accepted": bool(fresh), "duplicate": not fresh, "trusted": r["trusted"], "record": normalize.chat_message("INT-TG", r) if fresh and (r["trusted"] or cfg.get("observe_unknown")) else None}

def probe(cfg=None, transport=None): return identity(cfg, transport)
