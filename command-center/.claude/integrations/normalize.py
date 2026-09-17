# -*- coding: utf-8 -*-
"""NORMALIZATION — vendor records → the fixed record kinds of contracts.RECORD_SCHEMAS. Skills never see vendor schemas.
Data minimization: only the listed fields survive; bodies are previews; nothing else is retained."""
import re, datetime
from contracts import rid

def _s(v, n=None):
    t = "" if v is None else str(v)
    return t if n is None else t[:n]

def _iso(v):
    if v is None or v == "": return None
    if isinstance(v, datetime.datetime): return v.isoformat(timespec="seconds")
    if isinstance(v, datetime.date): return v.isoformat()
    t = str(v)
    return t[:19] if len(t) >= 19 and t[4] == "-" else t

def _bool(v):
    if isinstance(v, bool): return v
    return str(v).strip().lower() in ("1", "true", "y", "yes")

def meeting(iid, r):
    parts = [{"name": _s(p.get("name"), 120), "address": _s(p.get("address"), 160)} for p in (r.get("recipients") or []) if isinstance(p, dict)]
    if not parts and r.get("required"): parts = [{"name": x.strip(), "address": None} for x in str(r["required"]).split(";") if x.strip()]
    return {"record_id": rid(iid, r.get("entry_id") or f"{r.get('subject')}|{r.get('start')}"), "source_record_id": _s(r.get("entry_id") or f"{r.get('subject')}|{r.get('start')}", 400),
            "title": _s(r.get("subject"), 200), "start": _iso(r.get("start")), "end": _iso(r.get("end")), "all_day": _bool(r.get("all_day")), "organizer": _s(r.get("organizer"), 120),
            "participants": parts, "participant_count": len(parts), "location": _s(r.get("location"), 200), "online_link": r.get("online_link") or None,
            "description_preview": _s(r.get("preview"), 600), "recurring": _bool(r.get("is_recurring")), "meeting_status": r.get("meeting_status"), "response_status": r.get("response_status"),
            "source_updated_at": _iso(r.get("last_modified"))}

def message(iid, r):
    return {"record_id": rid(iid, r.get("entry_id") or f"{r.get('subject')}|{r.get('received')}"), "source_record_id": _s(r.get("entry_id") or f"{r.get('subject')}|{r.get('received')}", 400),
            "conversation_id": _s(r.get("conversation_id"), 200) or None, "conversation_topic": _s(r.get("conversation_topic"), 200), "subject": _s(r.get("subject"), 200),
            "sender": _s(r.get("sender"), 160).lower(), "sender_name": _s(r.get("sender_name"), 120), "to": _s(r.get("to"), 400), "cc": _s(r.get("cc"), 400),
            "received": _iso(r.get("received")), "sent": _iso(r.get("sent")), "unread": _bool(r.get("unread")), "importance": r.get("importance"),
            "flagged": bool(r.get("flag_status")) or bool(r.get("flag_request")), "attachments": int(r.get("attachments") or 0), "preview": _s(r.get("preview"), 600), "folder": _s(r.get("folder"), 20) or "Inbox",
            "source_updated_at": _iso(r.get("last_modified") or r.get("received"))}

def task(iid, t, source_updated_at=None):
    due = t.get("due"); due = due.isoformat() if hasattr(due, "isoformat") else (str(due)[:10] if due else None)
    return {"record_id": rid(iid, t.get("id")), "source_record_id": str(t.get("id")), "title": _s(t.get("task"), 300), "status": _s(t.get("status"), 40), "open": bool(t.get("open")),
            "owner": _s(t.get("owner"), 120), "due": due, "comment": _s(t.get("comment"), 400), "row": t.get("row"), "source_updated_at": source_updated_at}

def chat_message(iid, r, updated=None):
    """Chat message (Telegram / WhatsApp) → fixed shape. Text is truncated (data minimization); attachments keep metadata only (kind, name, size, mime) — never content."""
    atts = [{"kind": _s(a.get("kind"), 20), "name": _s(a.get("name"), 120), "size": a.get("size"), "mime": _s(a.get("mime"), 80)} for a in (r.get("attachments") or []) if isinstance(a, dict)]
    return {"record_id": rid(iid, f"{r.get('chat_id')}|{r.get('message_id')}"), "source_record_id": _s(f"{r.get('chat_id')}|{r.get('message_id')}", 200), "channel": iid, "chat_id": _s(r.get("chat_id"), 80), "chat_title": _s(r.get("chat_title"), 120),
            "sender_id": _s(r.get("sender_id"), 80), "sender_name": _s(r.get("sender_name"), 120),
            # safe, provider-supplied human-readable identity metadata (presentation only — never identity evidence)
            "sender_username": _s(r.get("sender_username"), 64), "sender_first_name": _s(r.get("sender_first_name"), 64), "sender_last_name": _s(r.get("sender_last_name"), 64), "text": _s(r.get("text"), 1200), "message_type": _s(r.get("message_type") or "text", 24), "reply_to": _s(r.get("reply_to"), 80) or None,
            "received": _iso(r.get("received")), "attachments": atts, "trusted": bool(r.get("trusted")), "update_id": r.get("update_id"), "source_updated_at": _iso(r.get("received")) or updated,
            # Telegram Business: source_mode BOT_CHAT (direct bot chat) vs BUSINESS (Gev's own account, selected chats). The connection
            # id is an operational secret, so only a short reference is carried; edited/deleted are evidence lifecycle, never silent overwrites.
            "source_mode": _s(r.get("source_mode") or "BOT_CHAT", 12), "business_connection_ref": _s(r.get("business_connection_ref"), 24),
            "edited": bool(r.get("edited")), "deleted": bool(r.get("deleted"))}

def chat_connection(iid, r, updated=None):
    """Business connection state. The connection id itself is NEVER stored in a record: only a short non-reversible reference."""
    rights = {k: bool(v) for k, v in (r.get("rights") or {}).items()}
    return {"record_id": rid(iid, f"connection|{r.get('connection_ref')}"), "source_record_id": _s(r.get("connection_ref"), 24), "channel": iid, "connection_ref": _s(r.get("connection_ref"), 24),
            "account_user_id": _s(r.get("account_user_id"), 40), "user_chat_id": _s(r.get("user_chat_id"), 40), "connected_at": _iso(r.get("connected_at")), "rights": rights,
            "is_enabled": bool(r.get("is_enabled")), "observed_at": _iso(r.get("observed_at")) or updated, "source_updated_at": _iso(r.get("observed_at")) or updated}

def chat_status(iid, r, updated=None):
    return {"record_id": rid(iid, f"status|{r.get('message_id')}|{r.get('status')}|{r.get('at')}"), "source_record_id": _s(f"{r.get('message_id')}|{r.get('status')}", 200), "channel": iid, "message_id": _s(r.get("message_id"), 120),
            "recipient_id": _s(r.get("recipient_id"), 80), "status": _s(r.get("status"), 20), "at": _iso(r.get("at")), "error": _s(r.get("error"), 200) or None, "source_updated_at": _iso(r.get("at")) or updated}

def chat_identity(iid, r, updated=None):
    return {"record_id": rid(iid, f"identity|{r.get('account_id')}"), "source_record_id": _s(r.get("account_id"), 120), "channel": iid, "account_id": _s(r.get("account_id"), 120), "display": _s(r.get("display"), 120), "verified": bool(r.get("verified")), "source_updated_at": updated}

def deal(iid, d, updated=None):
    return {"record_id": rid(iid, d.get("ID")), "source_record_id": _s(d.get("ID")), "title": _s(d.get("TITLE"), 200), "stage_id": _s(d.get("STAGE_ID"), 60), "owner_id": _s(d.get("ASSIGNED_BY_ID"), 20),
            "opportunity": d.get("OPPORTUNITY"), "currency": _s(d.get("CURRENCY_ID"), 8), "date_create": _iso(d.get("DATE_CREATE")), "date_modify": _iso(d.get("DATE_MODIFY")), "closed": _bool(d.get("CLOSED")),
            "category_id": _s(d.get("CATEGORY_ID"), 10), "source_id": _s(d.get("SOURCE_ID"), 40), "source_updated_at": _iso(d.get("DATE_MODIFY")) or updated}

def lead(iid, d, updated=None):
    return {"record_id": rid(iid, d.get("ID")), "source_record_id": _s(d.get("ID")), "title": _s(d.get("TITLE"), 200), "status_id": _s(d.get("STATUS_ID"), 60), "owner_id": _s(d.get("ASSIGNED_BY_ID"), 20),
            "date_create": _iso(d.get("DATE_CREATE")), "date_modify": _iso(d.get("DATE_MODIFY")), "source_id": _s(d.get("SOURCE_ID"), 40), "source_updated_at": _iso(d.get("DATE_MODIFY")) or updated}

def stage(iid, d, updated=None):
    return {"record_id": rid(iid, f"{d.get('ENTITY_ID')}|{d.get('STATUS_ID')}"), "source_record_id": _s(d.get("ID") or f"{d.get('ENTITY_ID')}|{d.get('STATUS_ID')}"), "entity_id": _s(d.get("ENTITY_ID"), 60),
            "status_id": _s(d.get("STATUS_ID"), 60), "name": _s(d.get("NAME"), 120), "sort": d.get("SORT"), "semantics": _s(d.get("SEMANTICS"), 20) or None, "source_updated_at": updated}

def activity(iid, d, updated=None):
    return {"record_id": rid(iid, d.get("ID")), "source_record_id": _s(d.get("ID")), "subject": _s(d.get("SUBJECT"), 200), "owner_id": _s(d.get("RESPONSIBLE_ID"), 20), "deadline": _iso(d.get("DEADLINE")),
            "completed": _bool(d.get("COMPLETED")), "type_id": _s(d.get("TYPE_ID"), 10), "owner_type_id": _s(d.get("OWNER_TYPE_ID"), 10), "source_updated_at": _iso(d.get("LAST_UPDATED")) or updated}

def b24task(iid, d, updated=None):
    g = {k.lower(): v for k, v in d.items()} if isinstance(d, dict) else {}
    return {"record_id": rid(iid, g.get("id")), "source_record_id": _s(g.get("id")), "title": _s(g.get("title"), 200), "status": _s(g.get("status"), 10), "responsible_id": _s(g.get("responsibleid") or g.get("responsible_id"), 20),
            "deadline": _iso(g.get("deadline")), "created_by": _s(g.get("createdby") or g.get("created_by"), 20), "source_updated_at": _iso(g.get("changeddate") or g.get("changed_date")) or updated}

def user(iid, d, updated=None):
    return {"record_id": rid(iid, d.get("ID")), "source_record_id": _s(d.get("ID")), "name": (_s(d.get("NAME"), 60) + " " + _s(d.get("LAST_NAME"), 60)).strip(), "email": _s(d.get("EMAIL"), 160).lower(),
            "active": _bool(d.get("ACTIVE", True)), "position": _s(d.get("WORK_POSITION"), 120), "source_updated_at": updated}

def identity(iid, d, portal, updated=None):
    return {"record_id": rid(iid, f"{portal}|{d.get('ID')}"), "source_record_id": _s(d.get("ID")), "portal": portal, "user_id": _s(d.get("ID")), "name": (_s(d.get("NAME"), 60) + " " + _s(d.get("LAST_NAME"), 60)).strip(),
            "admin": _bool(d.get("ADMIN", False)), "source_updated_at": updated}

NORMALIZERS = {"meeting": meeting, "message": message, "task": task, "deal": deal, "lead": lead, "stage": stage, "activity": activity, "b24task": b24task, "user": user}
