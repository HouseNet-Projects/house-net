"""Fail-closed proactive watcher layer over Deputy intelligence.

Runs on demand or from an external scheduler; it persists schedules/events in
the existing Store and never performs an external mutation.
"""
from __future__ import annotations
import datetime as dt, hashlib, json
import intelligence
import engine
import inbound_intelligence

def _now(): return dt.datetime.now().isoformat(timespec="seconds")
def _st(): return engine._store()
def _id(prefix, value): return prefix + hashlib.sha256(str(value).encode()).hexdigest()[:16]

def create_schedule(schedule_id, purpose, cadence, *, timezone="Asia/Yerevan", source_dependencies=None, enabled=True):
    row={"schedule_id":schedule_id,"purpose":purpose,"trigger_type":"interval","cadence":cadence,"timezone":timezone,
         "next_run":_now(),"last_run":None,"last_result":None,"enabled":enabled,"source_dependencies":source_dependencies or [],
         "authority_class":"THINK/PREPARE","owner":"Gev","failure_state":None,"retry_policy":"bounded_no_blind_retry"}
    _st().upsert("checkpoints", "schedule:"+schedule_id, row); return row

def schedules(): return [r for r in _st().list("checkpoints") if str(r.get("schedule_id","")).strip()]

def _event(kind, source, ref, severity, evidence, response, *, domain="operations", state="DETECTED", requires_attention=True):
    dedupe=_id("DED-", kind+":"+source+":"+ref)
    existing=_st().get("alerts", dedupe)
    if existing and existing.get("state") not in ("RESOLVED","SUPPRESSED"):
        existing.update({"last_seen":_now(),"occurrences":int(existing.get("occurrences",1))+1}); _st().upsert("alerts",dedupe,existing)
        return {**existing,"state":"DEDUPED","deduped":True}
    e={"event_id":_id("EVT-",dedupe),"event_type":kind,"detected_at":_now(),"source":source,"source_reference":ref,"domain":domain,
       "severity":severity,"impact":severity,"evidence":evidence,"previous_state":None,"current_state":"OPEN","dedupe_key":dedupe,
       "requires_attention":requires_attention,"recommended_response":response,"authority_requirement":"PREPARE_ONLY","state":state,"occurrences":1}
    _st().upsert("alerts",dedupe,e); return e

def run_cycle(*, persist=True):
    state=intelligence.current_state({}); exc=intelligence.exceptions(state); queue=intelligence.gev_queue(state,exc); out=[]
    for e in exc:
        if e.get("kind") in ("OVERDUE_TASK","DUE_TODAY","BLOCKED_TASK","OWNERLESS_TASK","UNCLEAR_TASK","DECISION_PENDING","ACTION_UNVERIFIED"):
            out.append(_event(e["kind"],e["subject"].get("source","INT-TASKS"),e["subject"].get("ref"),e.get("severity","LOW"),e.get("provenance",{}),e.get("recommendation",{})))
    for q in queue:
        if q.get("category") == "APPROVAL": out.append(_event("APPROVAL_WAITING","action-runtime",q.get("ref"),q.get("severity","MEDIUM"),q.get("ref"),q.get("required"),requires_attention=True))
    for iid,v in state.get("visibility",{}).items():
        if v.get("state") in ("STALE","UNAVAILABLE","NOT_CONFIGURED") and iid not in ("INT-MB",):
            out.append(_event("SOURCE_GAP",iid,iid,"MEDIUM",v,f"restore or certify {iid}",requires_attention=False))
    # Process normalized inbound observations already written by a certified
    # adapter.  This is internal preparation only: inbound content remains
    # evidence and can never grant approval or perform an external write.
    for obs in _st().list("channel_events", limit=500):
        if obs.get("kind") != "INBOUND_SIGNAL" or obs.get("processed_at"):
            continue
        ev = inbound_intelligence.event(obs.get("text", ""), channel=obs.get("channel", "unknown"),
                                       source_id=obs.get("source_id", "unknown"),
                                       retrieved_at=obs.get("retrieved_at") or _now(), sender=obs.get("sender"))
        inbound_intelligence.assert_safe(ev)
        _st().record("checkpoints", "observation:" + ev["id"], ev)
        if "COMMITMENT" in ev["event_classes"] or "ACTION" in ev["event_classes"] or "DEADLINE" in ev["event_classes"]:
            _st().upsert("loops", "inbound:" + ev["id"], {
                "loop_id": "inbound:" + ev["id"], "kind": "PREPARED_INBOUND_WORK",
                "summary": ev["text"][:240], "state": "OPEN", "source": ev["provenance"],
                "event_classes": ev["event_classes"], "confidence": "CANDIDATE",
                "authority": "INTERNAL_ONLY", "next_action": "Review and prepare governed follow-up",
            })
            out.append(_event("INBOUND_WORK_DETECTED", ev["channel"], ev["id"], "MEDIUM",
                              ev["provenance"], "Review prepared follow-up", requires_attention=True))
        obs["processed_at"] = _now(); _st().upsert("channel_events", obs.get("op_id") or ev["id"], obs)
    if persist: _st().upsert("checkpoints","proactive:last_cycle",{"at":_now(),"events":len(out),"truth_mode":state.get("truth_mode")})
    return {"status":"PARTIAL_SUCCESS" if state.get("unavailable") else "CURRENT","at":state.get("at"),"events":out,"attention":queue,"state":state}

def events(): return _st().list("alerts")
def daily_cycle(): return run_cycle()
def weekly_cycle():
    r=run_cycle(); r["review"]="weekly management review prepared from current snapshot and evidence"; return r
def monthly_cycle():
    r=run_cycle(); r["review"]="monthly management review prepared; trend is INSUFFICIENT_HISTORY until enough production checkpoints exist"; return r
