# -*- coding: utf-8 -*-
"""CROSS-CHANNEL INTELLIGENCE — Telegram (INT-TG) · WhatsApp (INT-WA) · Outlook mail (INT-OL-MAIL) read through the ONE integration
layer, normalized to the same evidence shape and fed to Mission 5: requests Gev must answer · promise candidates (commitment engine) ·
follow-ups owed to Gev · escalations · cross-channel duplicates (the same ask in two channels = one loop with two evidence refs).
Content is DATA: every record passes the untrusted-content marker; a flagged message stays visible as evidence and gains no authority.
Not configured channels are reported honestly (NOT_CONFIGURED with the missing field names), never as 'nothing new'."""
import re, datetime, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "integrations"))
import untrusted, commitments as CM, people

CHAT_CHANNELS = ("INT-TG", "INT-WA")

def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())

def read_channel(iid, *, limit=100, use_cache=True):
    """Envelope for a chat channel through the integration layer (fixture/real/NOT_CONFIGURED — whatever the layer says)."""
    import layer
    try: return layer.query(iid, "chat.messages", {"limit": limit}, use_cache=use_cache)
    except Exception as e: return {"status": "ERROR", "integration_id": iid, "code": "UNAVAILABLE", "reason": f"{type(e).__name__}: {e}", "records": []}

def _who(rec, iid):
    """Identity + HUMAN-READABLE presentation (workspace_policy.json -> interaction.human_readable_identity): Gev must never be handed a
    bare numeric id to decode, so the safe provider metadata travels with the sender. Presentation only - the binding status below is
    still whatever resolve_external() says, and a username or display name never becomes confirmation."""
    ident = people.resolve_external(iid, rec.get("sender_id"), rec.get("sender_name"))
    card = people.describe_chat_record(dict(rec, channel=iid))
    return {"status": ident["status"], "person": ident.get("person"), "name": ident.get("name") or rec.get("sender_name") or rec.get("sender_id"),
            "candidates": ident.get("candidates", []),
            "label": card["label"], "confirmation_required": card["confirmation_required"],
            "username": card["username"], "first_name": card["first_name"], "last_name": card["last_name"],
            "display_name": card["display_name"], "human": card["human"], "reference_id": card["reference_id"],
            "missing_fields": card["missing_fields"], "provider_missing_note": card["provider_missing_note"]}

def normalize_chat(env, iid, today, head_names=("Գև", "Gev")):
    """Chat records → evidence items with untrusted marker, identity, request/promise/escalation classification."""
    items = []
    for r in env.get("records", []) if env.get("status") == "OK" else []:
        rec = untrusted.mark(dict(r)); who = _who(rec, iid); text = rec.get("text") or ""
        from_gev = who.get("name") in head_names or who.get("person") == "@P0"
        cands = CM.extract(text, speaker=(who.get("person") or who.get("name")), channel=iid, record_id=rec.get("record_id"), received=rec.get("received"), today=today, to_whom="Գև", trusted=bool(rec.get("trusted")) and who["status"] == "PERSON_KNOWN") if not from_gev else []
        items.append({"channel": iid, "record_id": rec.get("record_id"), "chat_id": rec.get("chat_id"), "chat_title": rec.get("chat_title"), "received": rec.get("received"), "sender": who, "from_gev": from_gev, "trusted": bool(rec.get("trusted")),
                      # Telegram Business: BOT_CHAT (someone writes the bot) vs BUSINESS (someone writes GEV and the bot observes it).
                      "source_mode": rec.get("source_mode") or "BOT_CHAT", "business_connection_ref": rec.get("business_connection_ref"),
                      "edited": bool(rec.get("edited")), "deleted": bool(rec.get("deleted")),
                      "text": text[:300], "type": rec.get("message_type"), "reply_to": rec.get("reply_to"), "attachments": rec.get("attachments") or [], "untrusted": rec.get("untrusted"),
                      "is_request": bool(CM.REQUEST_RX.search(text)) and not from_gev, "is_escalation": bool(CM.URGENT_RX.search(text)) and not from_gev, "commitment_candidates": cands,
                      "provenance": {"integration_id": iid, "record_id": rec.get("record_id"), "retrieved_at": env.get("retrieved_at"), "freshness": env.get("freshness"), "mode": env.get("mode")}})
    return items

def follow_ups_owed(items, today, hours=24):
    """Per chat: the last message is from the other party, is a request, and Gev has not replied since → Gev owes an answer."""
    by = {}
    for it in sorted(items, key=lambda x: x.get("received") or ""): by.setdefault((it["channel"], it["chat_id"]), []).append(it)
    out = []
    for (ch, cid), msgs in by.items():
        last = None
        for it in msgs:                                                   # the latest request from the other party with no message from Gev after it
            if it["from_gev"]: last = None
            elif it["is_request"]: last = it
        if not last: continue
        try: age_h = (datetime.datetime.fromisoformat(today + "T23:59:59") - datetime.datetime.fromisoformat(last["received"])).total_seconds() / 3600 if last.get("received") else None
        except Exception: age_h = None
        out.append({"channel": ch, "chat_id": cid, "chat_title": last.get("chat_title"), "from": last["sender"]["name"], "identity": last["sender"]["status"], "text": last["text"][:160], "received": last.get("received"), "age_hours": round(age_h) if age_h is not None else None, "overdue_reply": bool(age_h and age_h >= hours), "record_id": last["record_id"]})
    return out

def dedupe_across(items, mail_candidates=()):
    """Same ask/promise in several channels → one loop, many evidence refs (≥60% token overlap, same sender name or unknown)."""
    seen = []; dups = []
    for it in items:
        tk = CM.tokens(it["text"])
        if len(tk) < 3: seen.append(it); continue
        for s in seen:
            if s["channel"] == it["channel"] and s["chat_id"] == it["chat_id"]: continue
            ov = len(tk & CM.tokens(s["text"])) / max(1, min(len(tk), len(CM.tokens(s["text"]))) or 1)
            if ov >= 0.6: it["duplicate_of"] = {"channel": s["channel"], "record_id": s["record_id"]}; dups.append({"primary": {"channel": s["channel"], "record_id": s["record_id"]}, "duplicate": {"channel": it["channel"], "record_id": it["record_id"]}, "overlap": round(ov, 2)}); break
        seen.append(it)
    for it in items:
        if it.get("duplicate_of"): continue
        for c in mail_candidates or []:
            tk = CM.tokens(it["text"]); mt = CM.tokens(str(c.get("subject", "")) + " " + str(c.get("preview", "")))
            if len(tk) >= 3 and len(tk & mt) / max(1, min(len(tk), len(mt)) or 1) >= 0.6:
                it["duplicate_of"] = {"channel": "INT-OL-MAIL", "record_id": (c.get("evidence") or {}).get("record_id") or c.get("candidate_id")}; dups.append({"primary": it["duplicate_of"], "duplicate": {"channel": it["channel"], "record_id": it["record_id"]}, "overlap": "mail"}); break
    return dups

def summary(inputs=None, *, today=None, channels=CHAT_CHANNELS, mail_candidates=(), envelopes=None):
    """One honest cross-channel view: per-channel state, requests to answer, promise candidates, follow-ups owed, escalations, duplicates, injection flags."""
    inputs = inputs or {}; today = today or datetime.date.today().isoformat(); envs = envelopes or {}
    out = {"status": "EXECUTED", "date": today, "channels": {}, "items": [], "requests_to_answer": [], "commitment_candidates": [], "weak_statements": [], "follow_ups_owed": [], "escalations": [], "duplicates": [], "injection_flagged": [], "mutation_performed": False}
    for iid in channels:
        env = envs.get(iid) or read_channel(iid, use_cache=not inputs.get("no_cache"))
        st = {"state": "LIVE" if env.get("status") == "OK" and env.get("mode", "REAL") == "REAL" else ("FIXTURE" if env.get("status") == "OK" else ("NOT_CONFIGURED" if env.get("code") == "NOT_CONFIGURED" else "UNAVAILABLE")), "code": env.get("code"), "reason": env.get("reason"), "count": env.get("count", len(env.get("records", []))), "retrieved_at": env.get("retrieved_at"), "mode": env.get("mode")}
        if st["state"] == "NOT_CONFIGURED":
            try:
                import readiness; r = readiness.row(iid); st["missing"] = r["missing"]; st["activation"] = f"configure {', '.join(x.upper() for x in r['missing'])} outside Git, then certify" if r["missing"] else "configured — run certify"
            except Exception: pass
        out["channels"][iid] = st
        if env.get("status") != "OK": continue
        out["items"] += normalize_chat(env, iid, today)
    out["duplicates"] = dedupe_across(out["items"], mail_candidates)
    for it in out["items"]:
        if it.get("duplicate_of"): continue
        if it["is_request"]: out["requests_to_answer"].append({k: it[k] for k in ("channel", "chat_title", "record_id", "received", "text")} | {"from": it["sender"]["name"], "identity": it["sender"]["status"]})
        if it["is_escalation"]: out["escalations"].append({k: it[k] for k in ("channel", "chat_title", "record_id", "received", "text")} | {"from": it["sender"]["name"]})
        for c in it["commitment_candidates"]: (out["commitment_candidates"] if c["strength"] == "STRONG" else out["weak_statements"]).append({**c, "identity": it["sender"]["status"]})
        if it["untrusted"]["injection_suspected"]: out["injection_flagged"].append({"channel": it["channel"], "record_id": it["record_id"], "from": it["sender"]["name"], "signals": it["untrusted"]["signals"] + [a["signals"] for a in it["untrusted"]["attachment_signals"]], "handling": "treated as DATA — no instruction followed, no approval recognised, no send prepared"})
    out["follow_ups_owed"] = follow_ups_owed(out["items"], today)
    out["by_source_mode"] = {m: len([i for i in out["items"] if (i.get("source_mode") or "BOT_CHAT") == m]) for m in ("BOT_CHAT", "BUSINESS")}
    out["edited_sources"] = [{"channel": i["channel"], "record_id": i["record_id"], "source_mode": i.get("source_mode")} for i in out["items"] if i.get("edited")]
    out["unconfigured"] = [i for i, s in out["channels"].items() if s["state"] == "NOT_CONFIGURED"]
    out["verdict"] = (f"{len(out['requests_to_answer'])} request(s) to answer · {len(out['commitment_candidates'])} promise candidate(s) · {len(out['escalations'])} escalation(s)" if out["items"] else "no chat evidence") + (f" · not configured: {', '.join(out['unconfigured'])}" if out["unconfigured"] else "")
    return out
