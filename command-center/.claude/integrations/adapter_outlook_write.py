# -*- coding: utf-8 -*-
"""WRITE ADAPTER INT-OL-CAL / INT-OL-MAIL — Outlook desktop mutations through the integrity-pinned outlook_write.ps1.
Reached ONLY by the Action Runtime after Gev's approval. Verification never trusts the writer: it re-reads through the READ-ONLY reader
(outlook_read.ps1 -Op get / mail Sent folder). Timeouts and ambiguous COM outcomes raise ProviderUnknown (→ RESULT_UNKNOWN, reconcile first).
IMPLEMENTED ≠ VERIFIED_WRITE: no operation here is certified until a Gev-approved live action is executed and read back."""
import sys, os, json, pathlib, subprocess, hashlib, datetime, re
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
import adapter_outlook, registry
from contracts import IntegrationError

WRITER = HERE / "outlook_write.ps1"
WRITER_SHA256 = "fc3e3219c012ee1f690b67d9da8bae51b2a0e642a661322a8a54cfe0e9b496c3"
OPS = ("calendar.create", "calendar.update", "calendar.cancel", "mail.draft", "mail.send")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")

def writer_sha256(): return hashlib.sha256(WRITER.read_bytes()).hexdigest() if WRITER.exists() else None
def writer_problems():
    if not WRITER.exists(): return ["outlook_write.ps1 missing"]
    if WRITER_SHA256 == "PIN_PENDING": return ["writer integrity pin not set"]
    if writer_sha256() != WRITER_SHA256: return ["outlook_write.ps1 does not match its integrity pin — modified writer refused"]
    return []

def _err():
    from actions import ProviderError, ProviderUnknown; return ProviderError, ProviderUnknown

def _run(args, timeout=90):
    ProviderError, ProviderUnknown = _err()
    ps = adapter_outlook.pwsh()
    if not ps: raise ProviderError("PowerShell not available — Outlook writer cannot run")
    wp = writer_problems()
    if wp: raise ProviderError("; ".join(wp))
    try: p = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(WRITER), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired: raise ProviderUnknown(f"Outlook writer exceeded {timeout}s — the mutation may or may not have happened")
    lines = [l for l in (p.stdout or "").splitlines() if l.strip()]
    if not lines: raise ProviderUnknown(f"writer produced no output (rc={p.returncode}) — outcome unknown")
    try: d = json.loads(lines[-1])
    except ValueError: raise ProviderUnknown("writer output not JSON — outcome unknown")
    if not d.get("ok"):
        if d.get("code") in ("BAD_PARAMS", "INLINE_RESPONSE", "ALREADY_SENT"): raise ProviderError(f"{d.get('code')}: {str(d.get('error'))[:200]}")     # nothing was written — a clean, explained refusal
        raise ProviderError(f"Outlook refused: {str(d.get('error'))[:160]}")
    return d

def _get(entry_id):
    """Read-back through the READ-ONLY reader."""
    d = adapter_outlook._run(["-Op", "get", "-EntryId", entry_id])
    return d.get("item")

def precondition(op, params):
    eid = params.get("target_object_id")
    if not eid: return {"exists": False, "object": None}
    try: it = _get(eid)
    except IntegrationError as e:
        if e.code in ("UNAVAILABLE", "TOOL_UNAVAILABLE"): raise
        it = None
    if not it: return {"exists": False, "object": None}
    keys = ("subject", "start", "end", "location", "required", "to", "unread", "folder", "submitted")       # folder/submitted: a draft that was edited, sent or moved after the card → STALE_CONFLICT
    return {"exists": True, "object": {k: it.get(k) for k in keys if k in it}}

def _sent_evidence(params, since=None):
    """Sent Items evidence through the READ-ONLY reader: same subject and recipient — and, when `since` (the execution start) is known,
    sent at or after it: an OLDER message with the same subject never verifies a new send."""
    d = adapter_outlook.read("mail.search", {"folder": "Sent", "query": str(params.get("subject", ""))[:60], "limit": 20}, {}, integration_id="INT-OL-MAIL")
    hits = [r for r in d["records"] if r["subject"].strip().lower() == str(params.get("subject", "")).strip().lower() and str(params.get("to", "")).lower() in (r.get("to") or "").lower()]
    if since: hits = [r for r in hits if (r.get("sent") or r.get("received") or "") >= str(since)[:19]]
    hits.sort(key=lambda r: r.get("sent") or "", reverse=True)
    return {"id": hits[0]["source_record_id"], **hits[0]} if hits else None

def _draft_left_drafts(entry_id):
    """After sending an existing draft the item is gone from Drafts (its EntryID changes when Outlook moves it to Sent Items)."""
    try: it = _get(entry_id)
    except IntegrationError as e:
        if e.code in ("UNAVAILABLE", "TOOL_UNAVAILABLE"): raise
        it = None
    return (it is None) or bool(it.get("submitted")) or ("draft" not in str(it.get("folder", "")).lower())

def find_existing(op, params):
    """Idempotency / reconciliation through read-only ops: same subject+start in the calendar; same subject+recipient in Drafts/Sent."""
    try:
        if op == "calendar.create":
            f = params["start"][:10]; d = adapter_outlook.read("calendar.events", {"from": f"{f}T00:00:00", "to": f"{f}T23:59:59", "limit": 100}, {}, integration_id="INT-OL-CAL")
            for r in d["records"]:
                if r["title"].strip().lower() == str(params.get("subject", "")).strip().lower() and (r["start"] or "")[:16] == params["start"][:16]: return {"id": r["source_record_id"], **r}
            return None
        if op == "mail.draft": return None                            # the reader exposes Inbox/Sent only; drafts are verified by EntryID after execution
        if op == "mail.send":
            if params.get("target_object_id"):                        # sending an EXISTING draft: already sent ⇔ it left Drafts (idempotent, never a second send)
                if _draft_left_drafts(params["target_object_id"]): return {"id": params["target_object_id"], "sent_draft": True, **(_sent_evidence(params) or {})}
                return None
            return _sent_evidence(params)
        if op in ("calendar.update", "calendar.cancel"):
            it = _get(params.get("target_object_id"))
            if op == "calendar.cancel": return None if it and not it.get("cancelled") else ({"id": params.get("target_object_id"), "cancelled": True} if it is None or it.get("cancelled") else None)
            if it and all(str(it.get(k)) == str(v) for k, v in params.items() if k in ("subject", "start", "end", "location")): return {"id": params.get("target_object_id"), **it}
            return None
    except IntegrationError as e:
        raise RuntimeError(f"reconciliation read failed: {e.code}")
    return None

def execute(op, params):
    ProviderError, _ = _err()
    if op not in OPS: raise ProviderError(f"unknown Outlook operation {op}")
    args = ["-Op", op]
    if op.startswith("calendar."):
        for k, flag in (("subject", "-Subject"), ("start", "-Start"), ("end", "-End"), ("location", "-Location"), ("body", "-Body")):
            if params.get(k): args += [flag, str(params[k])]
        if params.get("participants"): args += ["-Participants", ";".join(params["participants"]) if isinstance(params["participants"], list) else str(params["participants"])]
        if params.get("target_object_id"): args += ["-EntryId", str(params["target_object_id"])]
        for k in ("start", "end"):
            if params.get(k) and not _ISO.match(str(params[k])): raise ProviderError(f"{k} must be ISO local time")
    elif op == "mail.send" and params.get("target_object_id"):
        args += ["-EntryId", str(params["target_object_id"])]         # send the reviewed draft item as it is — content is what Gev saw in Outlook
    else:
        if params.get("to"): args += ["-To", ";".join(params["to"]) if isinstance(params["to"], list) else str(params["to"])]
        if params.get("cc"): args += ["-Cc", ";".join(params["cc"]) if isinstance(params["cc"], list) else str(params["cc"])]
        if params.get("subject"): args += ["-Subject", str(params["subject"])]
        if params.get("body"): args += ["-Body", str(params["body"])]
        if params.get("reply_to_entry_id"): args += ["-ReplyToEntryId", str(params["reply_to_entry_id"])]
    d = _run(args)
    return {"ok": True, "id": d.get("entry_id") or d.get("conversation_id"), "subject": d.get("subject"), "start": d.get("start"), "end": d.get("end"), "to": d.get("to"), "submitted": d.get("submitted"), "cancelled": d.get("cancelled"),
            "at": d.get("retrieved_at"), "inline_closed": d.get("inline_closed")}                       # `at` = writer start time: verification only accepts Sent evidence from this execution onward

def verify(op, params, result):
    """Independent read-back via the read-only reader; provider success alone never verifies."""
    try:
        if op == "mail.send":
            since = (result or {}).get("at")                              # only a message sent during/after THIS execution is evidence
            found = _sent_evidence(params, since=since)
            if params.get("target_object_id"):                        # a sent draft must ALSO have left Drafts — natural Outlook behaviour, verified independently
                left = _draft_left_drafts(params["target_object_id"])
                ok = bool(found) and left
                return {"verified": ok, "reason": ("Sent Items evidence found (sent ≥ execution start) and the draft left Drafts" if ok else ("draft still in Drafts" if not left else "no Sent Items evidence for this recipient/subject since the execution started")), "evidence": {"draft_entry_id": params["target_object_id"], "left_drafts": left, "since": since, "sent": found}}
            return {"verified": bool(found), "reason": "Sent Items evidence found (sent ≥ execution start)" if found else "no Sent Items evidence for this recipient/subject since the execution started", "evidence": found}
        eid = (result or {}).get("id") or params.get("target_object_id")
        it = _get(eid) if eid else None
        if op == "calendar.cancel":
            ok = it is None or bool(it.get("cancelled")); return {"verified": ok, "reason": "event absent/cancelled on read-back" if ok else "event still present", "evidence": {"id": eid, "cancelled": ok}}
        if not it: return {"verified": False, "reason": f"item {eid} not found on read-back", "evidence": None}
        checks = {"subject": params.get("subject"), "start": params.get("start"), "end": params.get("end")} if op.startswith("calendar") else {"subject": params.get("subject"), "to": ";".join(params["to"]) if isinstance(params.get("to"), list) else params.get("to")}
        diffs = {k: (v, it.get(k)) for k, v in checks.items() if v and str(it.get(k, ""))[:len(str(v))].lower() != str(v).lower()}
        if op == "mail.draft":                                                   # a draft is verified only as a DRAFT: in the Drafts folder and never submitted — provider success alone proves nothing
            if "draft" not in str(it.get("folder", "")).lower(): diffs["folder"] = ("Drafts", it.get("folder"))
            if it.get("submitted"): diffs["submitted"] = (False, True)
        return {"verified": not diffs, "reason": ("field mismatch: " + ", ".join(diffs)) if diffs else "read-back matches" + (" (Drafts, unsent)" if op == "mail.draft" else ""),
                "evidence": {"id": eid, **{k: it.get(k) for k in ("subject", "start", "end", "to", "location", "folder", "submitted", "unread", "last_modified") if k in it}}}
    except IntegrationError as e:
        return {"verified": False, "reason": f"read-back unavailable ({e.code}) — cannot verify", "evidence": None}
