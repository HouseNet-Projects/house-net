"""Canonical Deputy conversation persistence on the existing Store.

Conversation messages are evidence/context, never business authority.  This
module deliberately uses the existing channel_events table rather than a
parallel database.
"""
from __future__ import annotations
import datetime, uuid
from store import Store, op_id_for


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def create(store=None, *, title="New conversation"):
    store = store or Store()
    cid = "CONV-" + uuid.uuid4().hex[:16]
    store.record("channel_events", op_id_for("conversation", cid), {
        "kind": "CONVERSATION",
        "conversation_id": cid,
        "title": title,
        "created_at": _now(),
        "updated_at": _now(),
        "archived": False,
    })
    return cid


def append(conversation_id, role, content, store=None, *, language=None):
    store = store or Store()
    rows = messages(conversation_id, store)
    message_id = op_id_for("message", conversation_id, len(rows), role, content)
    result = store.record("channel_events", message_id, {
        "kind": "CONVERSATION_MESSAGE",
        "conversation_id": conversation_id,
        "message_id": message_id,
        "role": role,
        "content": str(content),
        "language": language,
        "created_at": _now(),
    })
    return result.get("record") or result.get("existing")


def messages(conversation_id, store=None, *, limit=100):
    store = store or Store()
    rows = store.list("channel_events", limit=10000)
    out = [r for r in rows if r.get("kind") == "CONVERSATION_MESSAGE" and r.get("conversation_id") == conversation_id]
    return out[-limit:]


def list_conversations(store=None, *, limit=50):
    store = store or Store()
    rows = store.list("channel_events", limit=10000)
    grouped = {}
    for row in rows:
        cid = row.get("conversation_id")
        if not cid:
            continue
        if row.get("kind") == "CONVERSATION":
            grouped.setdefault(cid, {}).update(row)
        elif row.get("kind") == "CONVERSATION_MESSAGE":
            g = grouped.setdefault(cid, {"conversation_id": cid})
            g["message_count"] = g.get("message_count", 0) + 1
            g["updated_at"] = row.get("created_at")
            if not g.get("title") and row.get("role") == "user":
                g["title"] = row.get("content", "")[:80]
    return list(grouped.values())[-limit:]


def get(conversation_id, store=None):
    rows = list_conversations(store)
    meta = next((r for r in rows if r.get("conversation_id") == conversation_id), {"conversation_id": conversation_id})
    meta["messages"] = messages(conversation_id, store)
    return meta
