# -*- coding: utf-8 -*-
"""DECISION MEMORY on the existing durable `decisions` table (no second store). Contract fields per decision:
  op_id · text · decided_at (date/time) · maker · scope · source (channel/record/evidence) · rationale · alternatives · implementation_owner ·
  effective_date · review_date · status (CONFIRMED | CANDIDATE | REVIEW_PENDING | SUPERSEDED | REVOKED) · supersedes · superseded_by ·
  related (tasks/commitments/kpis) · confidence · origin (GEV | EXTERNAL | MEETING_NOTES)
Gev's explicit statements → CONFIRMED; anything extracted from mail/chat/notes → CANDIDATE until Gev confirms.
Retrieval answers: what did we decide about X · when · why · is it still in force · what is pending review · contradictions —
a newer decision on the same scope NEVER silently overwrites the older one: both are returned and the contradiction is surfaced."""
import re, hashlib, datetime, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STATUSES = ("CONFIRMED", "CANDIDATE", "REVIEW_PENDING", "SUPERSEDED", "REVOKED")
NEG = re.compile(r"\b(not|no|never|stop|cancel|instead|rather than|չ\w+|ոչ|այլևս|փոխարեն|դադար)\b", re.I)
STOP = {"the", "a", "an", "to", "of", "on", "for", "in", "we", "is", "it", "that", "this", "և", "ու", "որ", "էլ", "ա", "է", "ենք", "մասին", "about", "with", "by", "at", "as", "be"}

def _st():
    import engine; return engine._store()
def _now(): return datetime.datetime.now().isoformat(timespec="seconds")
def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())
def tokens(t): return {w for w in re.findall(r"\w+", _norm(t)) if (len(w) > 2 or (len(w) == 2 and w.isalpha())) and w not in STOP}       # hyphen splits Armenian suffixes ('billing-ի' → billing)

def _row(r):
    """Normalize legacy rows (decision/reason/owner/date) and new rows to one shape without rewriting the store."""
    if r.get("kind") == "LOCAL_DRAFT": return None
    d = dict(r); d.setdefault("text", r.get("decision")); d.setdefault("rationale", r.get("reason")); d.setdefault("maker", r.get("owner", "Գև")); d.setdefault("decided_at", r.get("date"))
    d.setdefault("status", "CONFIRMED" if d.get("maker") in ("Գև", "Gev") and not r.get("origin") or r.get("origin") == "GEV" else "CANDIDATE"); d.setdefault("origin", "GEV" if d["status"] == "CONFIRMED" else "EXTERNAL")
    d.setdefault("scope", None); d.setdefault("alternatives", []); d.setdefault("implementation_owner", None); d.setdefault("review_date", None); d.setdefault("supersedes", None); d.setdefault("superseded_by", None); d.setdefault("related", []); d.setdefault("confidence", "CONFIRMED" if d["status"] == "CONFIRMED" else "UNVERIFIED"); d.setdefault("source", None)
    return d

def all_decisions():
    return [d for d in (_row(r) for r in _st().list("decisions")) if d]

def in_force(d, today=None):
    today = today or datetime.date.today().isoformat()
    if d.get("status") in ("SUPERSEDED", "REVOKED"): return {"in_force": False, "reason": f"{d['status']}" + (f" by {d.get('superseded_by')}" if d.get("superseded_by") else "")}
    if d.get("status") == "CANDIDATE": return {"in_force": None, "reason": "CANDIDATE — not confirmed by Gev; treat as unverified"}
    if d.get("effective_date") and str(d["effective_date"]) > today: return {"in_force": False, "reason": f"effective from {d['effective_date']} (not yet)"}
    if d.get("review_date") and str(d["review_date"]) <= today: return {"in_force": True, "reason": f"in force but REVIEW PENDING since {d['review_date']}", "review_pending": True}
    return {"in_force": True, "reason": "CONFIRMED, not superseded" + (f", review on {d['review_date']}" if d.get("review_date") else "")}

def contradictions_for(text, scope=None, exclude=None, today=None):
    """Active decisions on the same scope/topic whose wording differs (negation or different key words) — surfaced, never auto-resolved."""
    tk = tokens(text); out = []
    for d in all_decisions():
        if exclude and d["op_id"] == exclude: continue
        if d.get("status") in ("SUPERSEDED", "REVOKED"): continue
        same_scope = scope and d.get("scope") and _norm(scope) == _norm(d["scope"])
        ov = tk & tokens(d.get("text")); rel = len(ov) / max(1, min(len(tk), len(tokens(d.get("text"))) or 1))
        if not (same_scope or (len(ov) >= 2 and rel >= 0.4)): continue
        if _norm(d.get("text")) == _norm(text): continue
        differs = bool(NEG.search(text)) != bool(NEG.search(d.get("text") or "")) or (tk ^ tokens(d.get("text")))
        if differs: out.append({"op_id": d["op_id"], "text": d.get("text"), "status": d.get("status"), "decided_at": d.get("decided_at"), "overlap": sorted(ov)[:6]})
    return out

def record(text, *, maker="Գև", origin="GEV", scope=None, rationale=None, alternatives=None, implementation_owner=None, effective_date=None, review_date=None, source=None, related=None, decided_at=None, supersedes=None, confirmed_by=None):
    """Store a decision. origin GEV (Gev's own explicit statement) → CONFIRMED; any other origin → CANDIDATE. Contradictions are returned, nothing is overwritten."""
    text = " ".join(str(text or "").split())
    if not text: return {"status": "BLOCKED", "reason": "decision text missing"}
    status = "CONFIRMED" if origin == "GEV" and (confirmed_by in (None, "Gev", "Գև")) else "CANDIDATE"
    oid = "DEC-" + hashlib.sha256(f"{_norm(text)}|{maker}|{scope or ''}".encode("utf-8")).hexdigest()[:12]
    st = _st(); ex = st.get("decisions", oid)
    if ex: return {"status": "DUPLICATE", "op_id": oid, "decision": _row(ex), "contradictions": contradictions_for(text, scope, exclude=oid), "store": "decisions"}
    rec = {"op_id": oid, "text": text, "decision": text, "decided_at": decided_at or _now(), "date": (decided_at or _now())[:10], "maker": maker, "owner": maker, "origin": origin, "status": status, "scope": scope, "source": source,
           "rationale": rationale, "reason": rationale or "", "alternatives": list(alternatives or []), "implementation_owner": implementation_owner, "effective_date": effective_date, "review_date": review_date,
           "supersedes": supersedes, "superseded_by": None, "related": list(related or []), "confidence": "CONFIRMED" if status == "CONFIRMED" else "UNVERIFIED", "recorded_at": _now()}
    r = st.record("decisions", oid, rec)
    contra = contradictions_for(text, scope, exclude=oid)
    if supersedes and status == "CONFIRMED": supersede(oid, supersedes, by=maker)
    return {"status": r["status"], "op_id": oid, "decision": rec, "contradictions": contra, "store": "decisions", "note": ("CONFIRMED — Gev's explicit decision" if status == "CONFIRMED" else "CANDIDATE — extracted from external content; Gev must confirm before it counts")}

def confirm(op_id, by="Gev"):
    st = _st(); d = st.get("decisions", op_id)
    if not d: return {"status": "NOT_FOUND"}
    if by not in ("Gev", "Գև"): return {"status": "BLOCKED", "reason": "only Gev confirms a decision"}
    d.update({"status": "CONFIRMED", "confidence": "CONFIRMED", "confirmed_by": by, "confirmed_at": _now()}); st.upsert("decisions", op_id, d); return {"status": "CONFIRMED", "decision": _row(d)}

def supersede(new_id, old_id, by="Gev"):
    """Explicit supersession only (Gev): the old decision keeps its record, status → SUPERSEDED with the pointer; the new one points back."""
    st = _st(); old = st.get("decisions", old_id); new = st.get("decisions", new_id)
    if not old or not new: return {"status": "NOT_FOUND"}
    if by not in ("Gev", "Գև"): return {"status": "BLOCKED", "reason": "only Gev supersedes a decision"}
    old.update({"status": "SUPERSEDED", "superseded_by": new_id, "superseded_at": _now()}); new["supersedes"] = old_id
    st.upsert("decisions", old_id, old); st.upsert("decisions", new_id, new); return {"status": "SUPERSEDED", "old": old_id, "new": new_id}

def recall(query, today=None, limit=10):
    """«սրա մասին ինչ էինք որոշել» — ranked matches with when / why / still in force, contradictions surfaced."""
    tk = tokens(query); scored = []
    for d in all_decisions():
        blob = tokens(d.get("text")) | tokens(d.get("scope")) | tokens(d.get("rationale"))
        s = len(tk & blob) + (3 if d.get("scope") and _norm(d["scope"]) in _norm(query) else 0)
        if s: scored.append((s, d))
    hits = [d for s, d in sorted(scored, key=lambda x: (-x[0], 0 if x[1].get("status") == "CONFIRMED" else 1, str(x[1].get("decided_at"))))][:limit]     # confirmed decisions outrank candidates at equal relevance
    out = []
    for d in hits:
        f = in_force(d, today)
        out.append({"op_id": d["op_id"], "text": d.get("text"), "when": d.get("decided_at"), "why": d.get("rationale") or "UNKNOWN — rationale not recorded", "maker": d.get("maker"), "status": d.get("status"), "in_force": f["in_force"], "in_force_reason": f["reason"],
                    "review_pending": bool(f.get("review_pending")), "scope": d.get("scope"), "source": d.get("source"), "alternatives": d.get("alternatives"), "implementation_owner": d.get("implementation_owner"), "supersedes": d.get("supersedes"), "superseded_by": d.get("superseded_by"), "confidence": d.get("confidence"),
                    "contradictions": contradictions_for(d.get("text"), d.get("scope"), exclude=d["op_id"], today=today)})
    return out

def review_pending(today=None):
    return [d for d in all_decisions() if in_force(d, today).get("review_pending")]

def candidates():
    return [d for d in all_decisions() if d.get("status") == "CANDIDATE"]
