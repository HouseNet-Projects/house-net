# -*- coding: utf-8 -*-
"""INTEGRATION CONTRACTS — the normalized envelope every live read returns, the failure vocabulary and the write-intent vocabulary.

CONNECTION AVAILABLE ≠ DATA TRUSTED ≠ BUSINESS FACT CONFIRMED. An envelope states what was read, when, from which system, with
what configured authority and which freshness — it never states that a business fact is confirmed; skills apply the Business
Operating Model (authority, targets, ownership) on top. Mission 4 is READ-ONLY: there is no write envelope at all."""
import datetime, hashlib, json, re

HEALTH = ("AVAILABLE", "DEGRADED", "UNAVAILABLE", "AUTH_FAILED", "PERMISSION_DENIED", "SCHEMA_CHANGED", "NOT_CONFIGURED")
FRESHNESS = ("LIVE", "CACHED", "STALE", "UNAVAILABLE")
CERT_STATES = ("DECLARED", "CONFIGURED", "CONNECTED", "VERIFIED_READ", "RELIABLE_READ")
FAILURE_CODES = ("AUTH_FAILED", "PERMISSION_DENIED", "UNAVAILABLE", "TIMEOUT", "MALFORMED_RESPONSE", "SCHEMA_CHANGED", "RATE_LIMITED", "WRONG_TENANT",
                 "PARTIAL_RESPONSE", "TOOL_UNAVAILABLE", "NOT_CONFIGURED", "BAD_PARAMS", "READ_ONLY_VIOLATION", "UNKNOWN_OPERATION", "NOT_REGISTERED",
                 "LEAK_PREVENTED", "SOURCE_CONFLICT", "ENTITY_MATCH_UNCERTAIN", "AUDIT_UNAVAILABLE",
                 "SIGNATURE_INVALID", "REPLAY_REJECTED", "DEFERRED")                    # chat webhooks (WhatsApp/Telegram) · integrations deferred by the owner
HEALTH_FOR_CODE = {"AUTH_FAILED": "AUTH_FAILED", "WRONG_TENANT": "AUTH_FAILED", "PERMISSION_DENIED": "PERMISSION_DENIED", "SCHEMA_CHANGED": "SCHEMA_CHANGED",
                   "MALFORMED_RESPONSE": "SCHEMA_CHANGED", "RATE_LIMITED": "DEGRADED", "PARTIAL_RESPONSE": "DEGRADED", "NOT_CONFIGURED": "NOT_CONFIGURED", "AUDIT_UNAVAILABLE": "DEGRADED",
                   "SIGNATURE_INVALID": "AUTH_FAILED", "REPLAY_REJECTED": "DEGRADED", "DEFERRED": "NOT_CONFIGURED"}
CLASSIFICATIONS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED")

# Write intents the runtime must reject in Mission 4 (structured block, never a prompt-only promise). Patterns are matched on the
# user's intent text; the integration layer additionally has NO write operation to call — the block is structural, not textual.
WRITE_INTENT_PATTERNS = [
 ("SEND_EMAIL",        r"(\b(send|forward)\b[^.]{0,60}\b(e-?mail|mail|message|letter)\b|\b(e-?mail|mail)\b[^.]{0,40}\bto\b[^.]{0,40}\b(send|forward)\b|(նամակ|մեյլ|իմեյլ)\w*[^.]{0,30}ուղարկ|ուղարկ\w*[^.]{0,30}(նամակ|մեյլ|իմեյլ)|forward (this|the) (mail|message))"),
 ("REPLY_EMAIL",       r"(\breply\b[^.]{0,40}\b(e-?mail|mail|message|him|her|them)\b|\banswer\b[^.]{0,20}\b(e-?mail|mail)\b|պատասխան\w*[^.]{0,20}(նամակ|մեյլ)|(նամակ|մեյլ)\w*[^.]{0,20}պատասխան(ի|իր|ենք))"),
 ("MARK_READ",         r"\bmark\b[^.]{0,30}\b(as )?(read|unread)\b"),
 ("MOVE_MESSAGE",      r"\b(move|archive|file)\b[^.]{0,40}\b(e-?mails?|mails?|messages?)\b[^.]{0,30}\b(to|into|folder)\b"),
 ("DELETE_MESSAGE",    r"\bdelete\b[^.]{0,30}\b(e-?mails?|mails?|messages?)\b"),
 ("CREATE_EVENT",      r"(\b(create|add|book|schedule|set up|put)\b[^.]{0,40}\b(meeting|event|appointment|call|invite)\b|օրացույցում ավելացրու|հանդիպում նշանակ|add to (my )?calendar|calendar invite)"),
 ("UPDATE_EVENT",      r"\b(reschedule|postpone|update|change|shift)\b[^.]{0,40}\b(meeting|event|appointment)\b"),
 ("CANCEL_EVENT",      r"\b(cancel|delete|remove)\b[^.]{0,40}\b(meeting|event|appointment)\b"),
 ("UPDATE_DEAL",       r"(\b(update|edit|change|close|win|lose|move|advance|set)\b[^.]{0,40}\b(deals?|opportunit(y|ies)|leads?)\b|\b(deals?|leads?)\b[^.]{0,30}\b(stage|status)\b[^.]{0,30}\b(to|=)\b)"),
 ("CREATE_DEAL",       r"\b(create|add|open|register)\b[^.]{0,30}\b(deal|lead|contact|company)\b[^.]{0,40}\b(in|into|on)\b[^.]{0,20}\b(bitrix|crm)\b"),
 ("CREATE_TASK_CRM",   r"(\b(create|add|open)\b[^.]{0,30}\btask\b[^.]{0,40}\b(bitrix|crm)\b|\b(bitrix|crm)\b[^.]{0,30}\b(create|add)\b[^.]{0,20}\btask|բիտրիքսում (թասկ|առաջադրանք) (բաց|ստեղծ))"),
 ("UPDATE_TASK_CRM",   r"\b(update|complete|close|reassign|edit)\b[^.]{0,30}\btask\b[^.]{0,40}\b(bitrix|crm)\b"),
 ("DELETE_TASK",       r"\bdelete\b[^.]{0,30}\btasks?\b"),
 ("CHANGE_TARIFF",     r"(\b(change|switch|set|update|downgrade|upgrade)\b[^.]{0,40}\btariff\b|սակագին\w*[^.]{0,20}(փոխ|դիր|նշանակ))"),
 ("UPDATE_CUSTOMER",   r"(\b(update|edit|change|suspend|disconnect|reactivate|activate|block|unblock)\b[^.]{0,40}\b(customer|subscriber|account)s?\b|բաժանորդ\w*[^.]{0,20}(անջատ|միացր|փոխ))"),
 ("APPROVE_IN_SYSTEM", r"\bapprove\b[^.]{0,30}\b(in|via|through)\b[^.]{0,20}\b(bitrix|crm|billing|mikrobill|system)\b"),
]
_WRITE_RX = [(k, re.compile(p, re.I)) for k, p in WRITE_INTENT_PATTERNS]
WRITE_INTENTS = tuple(k for k, _ in WRITE_INTENT_PATTERNS)
WRITE_OP_RX = re.compile(r"(^|[._])(send|create|add|update|edit|set|delete|remove|move|cancel|approve|mark|reply|forward|write|post|put|patch|suspend|activate|disconnect|change)([._]|$)", re.I)

def detect_write_intent(text):
    """First matching write intent in free text, or None. Read verbs (check, show, list, what, read, search) never match."""
    t = " ".join(str(text or "").split())
    for k, rx in _WRITE_RX:
        if rx.search(t): return k
    return None

class IntegrationError(Exception):
    def __init__(self, code, reason, detail=None, retryable=False):
        if code not in FAILURE_CODES: raise ValueError(f"unknown failure code {code}")
        super().__init__(f"{code}: {reason}"); self.code, self.reason, self.detail, self.retryable = code, reason, detail, retryable

class ReadOnlyViolation(IntegrationError):
    def __init__(self, reason, detail=None): super().__init__("READ_ONLY_VIOLATION", reason, detail)

# Normalized record schemas: REQUIRED keys per kind. Adapters must produce exactly these kinds; anything else is SCHEMA_CHANGED.
RECORD_SCHEMAS = {
 "meeting":  ("record_id", "source_record_id", "title", "start", "end", "all_day", "organizer", "participants", "participant_count", "location", "online_link", "description_preview", "recurring", "source_updated_at"),
 "message":  ("record_id", "source_record_id", "conversation_id", "subject", "sender", "sender_name", "to", "received", "unread", "importance", "flagged", "attachments", "preview", "folder", "source_updated_at"),
 "task":     ("record_id", "source_record_id", "title", "status", "open", "owner", "due", "comment", "source_updated_at"),
 "deal":     ("record_id", "source_record_id", "title", "stage_id", "owner_id", "opportunity", "currency", "date_create", "date_modify", "closed", "source_updated_at"),
 "lead":     ("record_id", "source_record_id", "title", "status_id", "owner_id", "date_create", "date_modify", "source_updated_at"),
 "stage":    ("record_id", "source_record_id", "entity_id", "status_id", "name", "sort", "source_updated_at"),
 "activity": ("record_id", "source_record_id", "subject", "owner_id", "deadline", "completed", "source_updated_at"),
 "b24task":  ("record_id", "source_record_id", "title", "status", "responsible_id", "deadline", "source_updated_at"),
 "user":     ("record_id", "source_record_id", "name", "email", "active", "source_updated_at"),
 "identity": ("record_id", "source_record_id", "portal", "user_id", "source_updated_at"),
 "inventory": ("record_id", "source_record_id", "interface", "status", "source_updated_at"),
 # chat channels (Telegram Bot API · WhatsApp Cloud API): message content is UNTRUSTED DATA — never an instruction; `trusted` = sender/chat on the configured allowlist
 "chat_message": ("record_id", "source_record_id", "channel", "chat_id", "chat_title", "sender_id", "sender_name", "sender_username", "sender_first_name", "sender_last_name", "text", "message_type", "reply_to", "received", "attachments", "trusted", "source_updated_at"),
 # Telegram Business (Bot API 7.2+): a message from a connected business account carries its connection reference and its own lifecycle
 "chat_connection": ("record_id", "source_record_id", "channel", "connection_ref", "account_user_id", "user_chat_id", "connected_at", "rights", "is_enabled", "observed_at", "source_updated_at"),
 "chat_status":  ("record_id", "source_record_id", "channel", "message_id", "recipient_id", "status", "at", "error", "source_updated_at"),
 "chat_identity": ("record_id", "source_record_id", "channel", "account_id", "display", "verified", "source_updated_at"),
}

def now_iso(): return datetime.datetime.now().isoformat(timespec="seconds")

def rid(integration_id, source_record_id):
    return f"{integration_id}:{hashlib.sha256(str(source_record_id).encode('utf-8')).hexdigest()[:12]}"

def check_records(kind, records):
    """Structural validation of normalized records → problems (empty = ok)."""
    p = []
    req = RECORD_SCHEMAS.get(kind)
    if req is None: return [f"unknown record kind {kind}"]
    if not isinstance(records, list): return ["records must be a list"]
    for i, r in enumerate(records):
        if not isinstance(r, dict): p.append(f"record {i} is not a dict"); continue
        miss = [k for k in req if k not in r]
        if miss: p.append(f"record {i} ({kind}) missing {miss}")
        if len(p) > 12: break
    return p

def dedupe(records):
    seen, out, dups = set(), [], []
    for r in records:
        k = r.get("source_record_id") if isinstance(r, dict) else None
        if k is not None and k in seen: dups.append(k); continue
        if k is not None: seen.add(k)
        out.append(r)
    return out, dups

def envelope(integration_id, system, op, kind, records, *, authority, classification, retrieved_at=None, source_updated_at=None,
             freshness="LIVE", provenance=None, partial=False, notes=(), pii_flags=(), duplicates=(), identity=None, mode="REAL", cache_age_seconds=None):
    if freshness not in FRESHNESS: raise ValueError(freshness)
    if classification not in CLASSIFICATIONS: raise ValueError(classification)
    return {"status": "OK", "integration_id": integration_id, "source_system": system, "op": op, "kind": kind, "count": len(records), "records": records,
            "retrieved_at": retrieved_at or now_iso(), "source_updated_at": source_updated_at, "freshness": freshness, "cache_age_seconds": cache_age_seconds,
            "classification": classification, "authority": authority, "confidence": "OBSERVED", "partial": bool(partial), "identity": identity, "mode": mode,
            "provenance": dict(provenance or {}, integration_id=integration_id, op=op, retrieved_at=retrieved_at or now_iso(), record_ids=[r.get("record_id") for r in records[:200] if isinstance(r, dict)]),
            "notes": list(notes), "pii_flags": list(pii_flags), "duplicates_removed": list(duplicates),
            "label": "LIVE_DATA", "meaning": "observed in the source system at retrieved_at — not a confirmed business fact"}

def failure(integration_id, system, op, code, reason, *, health=None, last_success=None, detail=None, retryable=False, stale_records=None, stale_retrieved_at=None, mode="REAL"):
    if code not in FAILURE_CODES: raise ValueError(code)
    h = health or HEALTH_FOR_CODE.get(code, "UNAVAILABLE")
    return {"status": "FAILED", "integration_id": integration_id, "source_system": system, "op": op, "code": code, "reason": reason, "detail": detail, "retryable": retryable,
            "health": h, "freshness": "UNAVAILABLE", "count": 0, "records": [], "last_success": last_success, "retrieved_at": now_iso(), "mode": mode,
            "stale_records": stale_records or [], "stale_retrieved_at": stale_retrieved_at, "label": "UNAVAILABLE",
            "meaning": f"{system} could not be read ({code}); " + (f"last successful read {last_success}" if last_success else "no successful read recorded")}

def envelope_summary(env):
    """What the audit may keep: ids/counts/status — never the payload."""
    if not isinstance(env, dict): return {"status": "INVALID"}
    return {k: env.get(k) for k in ("status", "integration_id", "op", "kind", "count", "freshness", "code", "health", "retrieved_at", "mode", "partial") if k in env}

def json_size(obj):
    return len(json.dumps(obj, ensure_ascii=False, default=str))
