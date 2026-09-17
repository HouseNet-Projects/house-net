# -*- coding: utf-8 -*-
"""ALERT MANAGEMENT around Mission 5 exceptions — durable `alerts` table (upsert; references only). One alert per exception id
(deterministic → dedupe). Lifecycle: OPEN → ACKNOWLEDGED | SUPPRESSED (until date, by Gev) → RESOLVED (evidence: exception absent
from the live state) → REOPENED (came back or worsened). Escalation is computed from persistence (seen on ≥3 distinct days without
acknowledgement) and severity — reported, never delivered: any external notification is an Action Runtime approval."""
import datetime, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STATES = ("OPEN", "ACKNOWLEDGED", "SUPPRESSED", "RESOLVED", "REOPENED")
SEV = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

def _st():
    import engine; return engine._store()
def _now(): return datetime.datetime.now().isoformat(timespec="seconds")

def _aid(exc_id): return f"ALERT-{exc_id}"

def sync(exceptions, today=None, *, persist=True):
    """Reconcile the alert table with the current exception list. Returns the alert rows grouped: new_today · escalated · open · acknowledged · suppressed · resolved_now · reopened."""
    today = today or datetime.date.today().isoformat(); st = _st(); cur = {e["id"]: e for e in exceptions}
    rows = {r["op_id"]: r for r in st.list("alerts")}; out = {"new_today": [], "escalated": [], "open": [], "acknowledged": [], "suppressed": [], "resolved_now": [], "reopened": []}
    for eid, e in cur.items():
        aid = _aid(eid); r = rows.get(aid)
        if not r:
            r = {"op_id": aid, "exception_id": eid, "kind": e.get("kind"), "subject_ref": (e.get("provenance") or {}).get("record_id") or str(e.get("subject", {}).get("id")), "what": e.get("what"), "severity": e.get("severity"), "urgency": e.get("urgency"),
                 "state": "OPEN", "first_seen": today, "last_seen": today, "seen_days": [today], "escalation_level": 0, "ack": None, "suppressed_until": None, "resolved": None, "history": [{"at": _now(), "state": "OPEN"}]}
            out["new_today"].append(r)
        else:
            r = dict(r); prev_sev = r.get("severity")
            if today not in r.get("seen_days", []): r["seen_days"] = (r.get("seen_days") or []) + [today]
            r["last_seen"] = today; r["what"] = e.get("what"); r["urgency"] = e.get("urgency")
            worsened = SEV.get(e.get("severity"), 0) > SEV.get(prev_sev, 0); r["severity"] = e.get("severity")
            if r["state"] == "RESOLVED" or (r["state"] == "SUPPRESSED" and (worsened or (r.get("suppressed_until") and r["suppressed_until"] < today))) or (r["state"] == "ACKNOWLEDGED" and worsened):
                r["state"] = "REOPENED"; r["history"] = (r.get("history") or []) + [{"at": _now(), "state": "REOPENED", "reason": "worsened" if worsened else "came back / suppression expired"}]; out["reopened"].append(r)
        if r["state"] in ("OPEN", "REOPENED") and len(r.get("seen_days", [])) >= 3 and r.get("severity") in ("HIGH", "MEDIUM"):
            lvl = 1 + (len(r["seen_days"]) - 3) // 2
            if lvl > r.get("escalation_level", 0): r["escalation_level"] = lvl; r["history"] = (r.get("history") or []) + [{"at": _now(), "state": r["state"], "escalation_level": lvl}]; out["escalated"].append(r)
        if r["state"] in ("OPEN", "REOPENED"): out["open"].append(r)
        elif r["state"] == "ACKNOWLEDGED": out["acknowledged"].append(r)
        elif r["state"] == "SUPPRESSED": out["suppressed"].append(r)
        rows[aid] = r
        if persist: st.upsert("alerts", aid, r)
    for aid, r in list(rows.items()):
        if r.get("exception_id") in cur or r.get("state") == "RESOLVED": continue
        r = dict(r); r["state"] = "RESOLVED"; r["resolved"] = {"at": _now(), "evidence": f"exception {r['exception_id']} absent from the live state on {today}"}; r["history"] = (r.get("history") or []) + [{"at": _now(), "state": "RESOLVED"}]
        out["resolved_now"].append(r); rows[aid] = r
        if persist: st.upsert("alerts", aid, r)
    out["escalated"] = [r for r in out["open"] if r.get("escalation_level", 0) > 0]
    return out

def _set(aid, fn, by="Gev"):
    st = _st(); r = st.get("alerts", aid) or st.get("alerts", _aid(aid))
    if not r: return {"status": "NOT_FOUND", "alert": aid}
    r = dict(r); fn(r); r["history"] = (r.get("history") or []) + [{"at": _now(), "state": r["state"], "by": by}]; st.upsert("alerts", r["op_id"], r); return {"status": r["state"], "alert": r}

def ack(aid, by="Gev", note=None): return _set(aid, lambda r: r.update(state="ACKNOWLEDGED", ack={"by": by, "at": _now(), "note": note}), by)
def suppress(aid, until, by="Gev", reason=None): return _set(aid, lambda r: r.update(state="SUPPRESSED", suppressed_until=until, suppress_reason=reason), by)
def resolve(aid, evidence, by="Gev"):
    if not evidence: return {"status": "BLOCKED", "code": "VERIFICATION_REQUIRED", "reason": "resolving an alert needs evidence"}
    return _set(aid, lambda r: r.update(state="RESOLVED", resolved={"at": _now(), "evidence": evidence, "by": by}), by)
def reopen(aid, by="Gev", reason=None): return _set(aid, lambda r: r.update(state="REOPENED", reopen_reason=reason), by)

def listing(state=None):
    return [r for r in _st().list("alerts") if not state or r.get("state") == state]
