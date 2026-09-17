# -*- coding: utf-8 -*-
"""COMMITMENT ENGINE on the existing durable `commitments` table (no second store). Extracts promises from mail, Telegram, WhatsApp,
meeting notes, tasks and Gev's own statements; keeps one loop per promise across channels (multiple evidence refs); tracks the
lifecycle OPEN → DUE_SOON → OVERDUE → FULFILLED | CANCELLED | SUPERSEDED, with UNVERIFIED for claims without evidence.
Contract fields: op_id · who (person token or name) · to_whom · what · due (ISO or None = UNKNOWN) · source · evidence[] · strength
(STRONG explicit promise | WEAK intention) · confidence · state · created_at · fulfilled_at · fulfilment_evidence · origin.
Rules: an unknown due date STAYS UNKNOWN (never guessed) · a weak statement is a candidate, not a commitment · closing needs evidence ·
nothing here creates a task or writes to any external system."""
import re, hashlib, datetime, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STATES = ("OPEN", "DUE_SOON", "OVERDUE", "FULFILLED", "CANCELLED", "SUPERSEDED", "UNVERIFIED")
STRONG_RX = re.compile(r"(\bi(?:'ll| will| shall)\b|\bwill (?:send|do|call|deliver|finish|prepare|share|fix|bring|pay|report)|\bi promise\b|\bby (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today|eod|end of (?:day|week)|\d{1,2}[./-]\d{1,2})\b|"
                       r"կուղարկեմ|կանեմ|կզանգեմ|կտամ|կպատրաստեմ|կավարտեմ|կբերեմ|կվճարեմ|կգրեմ|կներկայացնեմ|կլուծեմ|խոստանում եմ|կարվի մինչև|մինչև (?:վաղը|ուրբաթ|երկուշաբթի|երեքշաբթի|չորեքշաբթի|հինգշաբթի|շաբաթ|կիրակի|էսօր|այսօր)|վաղը կ\w+)", re.I)
WEAK_RX = re.compile(r"(\bi(?:'ll)? try\b|\bmaybe\b|\bprobably\b|\bshould be able\b|\bif i can\b|\bhopefully\b|\bmight\b|\bwe(?:'ll)? see\b|կփորձեմ|երևի|հնարավոր ա|եթե հասցնեմ|կնայեմ|կտեսնենք|մի հատ նայեմ)", re.I)
REQUEST_RX = re.compile(r"(\bcan you\b|\bcould you\b|\bplease\b|\bwould you\b|\bneed (?:you|your)\b|\bwaiting for (?:you|your)\b|կարո՞ղ ես|կարող ես|խնդրում եմ|էլի սպասում|ուղարկի ինձ|պատասխանի|\?\s*$)", re.I)
URGENT_RX = re.compile(r"(urgent|asap|critical|escalat|immediately|շտապ|անհապաղ|կրիտիկ|էսկալ|հրատապ)", re.I)
WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6, "երկուշաբթի": 0, "երեքշաբթի": 1, "չորեքշաբթի": 2, "հինգշաբթի": 3, "ուրբաթ": 4, "շաբաթ": 5, "կիրակի": 6}
STOP = {"the", "a", "an", "to", "of", "on", "for", "in", "i", "will", "by", "you", "it", "and", "that", "this", "we", "is", "be", "կ", "եմ", "ես", "ա", "է", "ու", "և", "որ", "մինչև", "էլ"}

def _st():
    import engine; return engine._store()
def _now(): return datetime.datetime.now().isoformat(timespec="seconds")
def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())
def tokens(t): return {w for w in re.findall(r"\w+", _norm(t)) if len(w) > 2 and w not in STOP}

def parse_due(text, today):
    """Explicit due only: weekday names, tomorrow/today, dd.mm / dd/mm / ISO. Anything else → None (UNKNOWN)."""
    t = _norm(text); today = today if isinstance(today, datetime.date) else datetime.date.fromisoformat(str(today))
    if re.search(r"(next week|next month|հաջորդ շաբաթ|հաջորդ ամիս|մյուս շաբաթ|soon|շուտով|later|հետո)", t): return None          # a period, not a date → UNKNOWN
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t)
    if m:
        try: return datetime.date.fromisoformat(m.group(1)).isoformat()
        except ValueError: pass
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b", t)
    if m:
        try:
            y = int(m.group(3)) if m.group(3) else today.year; y = y + 2000 if y < 100 else y
            return datetime.date(y, int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError: pass
    if re.search(r"\b(tomorrow|վաղը|վաղվա)\b", t): return (today + datetime.timedelta(days=1)).isoformat()
    if re.search(r"\b(today|էսօր|այսօր|eod|end of day)\b", t): return today.isoformat()
    if re.search(r"\b(end of (?:the )?week|this week|էս շաբաթ|այս շաբաթ)\b", t): return (today + datetime.timedelta(days=(4 - today.weekday()) % 7)).isoformat()
    for w, d in WEEKDAYS.items():
        if re.search(r"(?:^|[^\w])" + w, t):
            delta = (d - today.weekday()) % 7 or 7
            return (today + datetime.timedelta(days=delta)).isoformat()
    return None

def strength(text):
    if STRONG_RX.search(text or ""): return "WEAK" if WEAK_RX.search(text or "") else "STRONG"
    if WEAK_RX.search(text or ""): return "WEAK"
    return None

def extract(text, *, speaker, channel, record_id, received=None, today=None, to_whom="Գև", trusted=True):
    """One message → 0..n commitment candidates. Each sentence with a promise marker becomes a candidate with the exact quote as evidence.
    Untrusted sender (not on an allowlist / not a resolved identity) → confidence LOW and origin marked; content never gains authority."""
    today = today or datetime.date.today().isoformat(); out = []
    for sent in re.split(r"(?<=[.!?։])\s+|\n+", str(text or "")):
        s = sent.strip()
        if not s: continue
        st = strength(s)
        if not st: continue
        out.append({"who": speaker, "to_whom": to_whom, "what": s[:240], "due": parse_due(s, today), "strength": st, "confidence": ("MEDIUM" if st == "STRONG" else "LOW") if trusted else "LOW",
                    "source": {"channel": channel, "record_id": record_id, "received": received}, "evidence": [{"channel": channel, "record_id": record_id, "quote": s[:240], "at": received}], "trusted": trusted})
    return out

def _key(who, what): return "CMT-" + hashlib.sha256(f"{_norm(who)}|{' '.join(sorted(tokens(what)))}".encode("utf-8")).hexdigest()[:12]

def _match_existing(cand, rows):
    """Cross-channel dedupe: same who + ≥60% token overlap with an open commitment = the same promise (one loop, many evidence refs)."""
    tk = tokens(cand["what"])
    for r in rows:
        if r.get("state") in ("FULFILLED", "CANCELLED", "SUPERSEDED"): continue
        if _norm(r.get("who") or r.get("owner")) != _norm(cand["who"]): continue
        rt = tokens(r.get("what") or r.get("text")); ov = len(tk & rt) / max(1, min(len(tk), len(rt)) or 1)
        if ov >= 0.6: return r
    return None

def ingest(cands, *, origin="EXTERNAL"):
    """Candidates → durable commitments (STRONG) or candidates list (WEAK stays UNVERIFIED candidate, never a commitment). Idempotent; merges evidence across channels."""
    st = _st(); rows = st.list("commitments"); new, merged, weak = [], [], []
    for c in cands:
        if c["strength"] != "STRONG": weak.append(c); continue
        ex = _match_existing(c, rows)
        if ex:
            refs = ex.get("evidence") or []
            if not any(e.get("record_id") == c["source"]["record_id"] and e.get("channel") == c["source"]["channel"] for e in refs):
                ex["evidence"] = refs + c["evidence"]; ex["last_seen"] = _now(); st.upsert("commitments", ex["op_id"], ex); merged.append(ex["op_id"])
            continue
        oid = _key(c["who"], c["what"])
        rec = {"op_id": oid, "text": c["what"], "what": c["what"], "who": c["who"], "owner": c["who"], "to_whom": c["to_whom"], "due": c["due"], "condition": None, "state": "OPEN", "strength": "STRONG", "confidence": c["confidence"], "origin": origin,
               "source": c["source"], "evidence": c["evidence"], "created_at": _now(), "last_seen": _now(), "fulfilled_at": None, "fulfilment_evidence": None, "trusted": c.get("trusted", True)}
        r = st.record("commitments", oid, rec)
        if r["status"] == "RECORDED": new.append(oid); rows.append(rec)
        else: merged.append(oid)
    return {"new": new, "merged": merged, "weak_candidates": weak}

def source_changed(record_id, *, channel, state, new_text=None, at=None):
    """A source message was EDITED or DELETED at the provider. Deleting a message never fulfils or cancels a promise and editing it
    never rewrites what was already recorded: the original quote is preserved, the evidence ref is marked, confidence drops to
    UNVERIFIED, and a material change (the promise text itself moved) is surfaced as a contradiction for Gev to resolve."""
    if state not in ("EDITED", "DELETED"): return {"status": "BLOCKED", "reason": f"unknown source state {state}"}
    st = _st(); touched = []
    for r in st.list("commitments"):
        refs = r.get("evidence") or []
        hit = [e for e in refs if e.get("record_id") == record_id and (not channel or e.get("channel") == channel)]
        if not hit: continue
        d = dict(r); material = False
        for e in d["evidence"]:
            if e.get("record_id") != record_id or (channel and e.get("channel") != channel): continue
            e["source_state"] = state; e["source_state_at"] = at or _now()
            if state == "EDITED" and new_text is not None:
                e["edited_text"] = str(new_text)[:240]                      # the ORIGINAL quote stays in e["quote"], never overwritten
                material = len(tokens(e.get("quote")) ^ tokens(new_text)) > 0
            if state == "DELETED": material = True
        live = [e for e in d["evidence"] if e.get("source_state") != "DELETED"]
        d["confidence"] = "UNVERIFIED"; d["last_seen"] = _now()
        d["source_lifecycle"] = (d.get("source_lifecycle") or []) + [{"record_id": record_id, "channel": channel, "state": state, "at": at or _now(), "material": bool(material)}]
        if material:
            d["contradiction"] = {"reason": ("the source message was deleted at the provider" if state == "DELETED" else "the source message was edited after it was recorded"),
                                  "evidence_remaining": len(live), "needs": "Gev decides whether this promise still stands — Deputy does not close or cancel it on a provider edit/delete"}
        st.upsert("commitments", d["op_id"], d); touched.append({"op_id": d["op_id"], "material": bool(material), "evidence_remaining": len(live)})
    return {"status": "EXECUTED", "state": state, "record_id": record_id, "affected": touched,
            "note": "evidence lifecycle recorded; no commitment was fulfilled, cancelled or deleted by this provider event"}

def lifecycle_state(r, today):
    if r.get("state") in ("FULFILLED", "CANCELLED", "SUPERSEDED", "UNVERIFIED"): return r["state"]
    due = r.get("due")
    if not due: return "OPEN"
    if due < today: return "OVERDUE"
    if due <= (datetime.date.fromisoformat(today) + datetime.timedelta(days=2)).isoformat(): return "DUE_SOON"
    return "OPEN"

def all_rows(today=None):
    today = today or datetime.date.today().isoformat()
    out = []
    for r in _st().list("commitments"):
        d = dict(r); d.setdefault("who", r.get("owner")); d.setdefault("what", r.get("text")); d.setdefault("evidence", []); d.setdefault("strength", "STRONG"); d.setdefault("origin", "GEV")
        d["lifecycle"] = lifecycle_state(d, today); d["due_display"] = d.get("due") or "UNKNOWN"; out.append(d)
    return out

def open_rows(today=None): return [r for r in all_rows(today) if r["lifecycle"] in ("OPEN", "DUE_SOON", "OVERDUE")]

def fulfil(op_id, evidence, by="Gev"):
    """Close on evidence only (what was delivered, where seen). No evidence → stays open."""
    if not evidence: return {"status": "BLOCKED", "code": "VERIFICATION_REQUIRED", "reason": "closing a commitment needs evidence (what was delivered / where it was seen)"}
    st = _st(); r = st.get("commitments", op_id)
    if not r: return {"status": "NOT_FOUND"}
    r.update({"state": "FULFILLED", "fulfilled_at": _now(), "fulfilment_evidence": evidence, "closed_by": by}); st.upsert("commitments", op_id, r); return {"status": "FULFILLED", "commitment": r}

def set_state(op_id, state, by="Gev", note=None):
    if state not in ("CANCELLED", "SUPERSEDED", "OPEN"): return {"status": "BLOCKED", "reason": f"state {state} needs fulfil() with evidence or is unknown"}
    st = _st(); r = st.get("commitments", op_id)
    if not r: return {"status": "NOT_FOUND"}
    r.update({"state": state, "state_changed_at": _now(), "state_changed_by": by, "state_note": note}); st.upsert("commitments", op_id, r); return {"status": state, "commitment": r}

def by_person(today=None):
    out = {}
    for r in open_rows(today): out.setdefault(r["who"] or "UNKNOWN", []).append(r)
    return out

def late_leaders(today=None):
    """Who delays promises most: overdue count and total delay days per person (open rows only; evidence-based, no judgement)."""
    today = today or datetime.date.today().isoformat(); agg = {}
    for r in all_rows(today):
        if r["lifecycle"] != "OVERDUE": continue
        a = agg.setdefault(r["who"] or "UNKNOWN", {"who": r["who"] or "UNKNOWN", "overdue": 0, "delay_days": 0, "items": []})
        days = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(r["due"])).days
        a["overdue"] += 1; a["delay_days"] += days; a["items"].append({"op_id": r["op_id"], "what": r["what"][:80], "due": r["due"], "days_late": days})
    return sorted(agg.values(), key=lambda a: (-a["overdue"], -a["delay_days"]))

def expected_on(date_iso, today=None):
    return [r for r in open_rows(today) if r.get("due") == date_iso]
