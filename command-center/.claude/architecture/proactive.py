"""Fail-closed proactive watcher layer over Deputy intelligence.

Runs on demand or from an external scheduler; it persists schedules/events in
the existing Store and never performs an external mutation.
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os
import intelligence
import engine
import inbound_intelligence
import commitments

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


def _claude_prepare_inbound(ev, commitment_result):
    """Use Claude for bounded internal preparation after deterministic triage.

    This function is deliberately opt-in and has no write connector. It only
    stores a short analysis/trace checkpoint and can propose follow-up work;
    any external action remains an Action Runtime candidate requiring approval.
    """
    if os.environ.get("DEPUTY_USE_CLAUDE") != "1":
        return None
    try:
        from ai_provider import ask_agent
        from context_orchestrator import run_tool
        prompt = ("You are Deputy's proactive operating analyst. Review this governed inbound observation. "
                  "Explain why it matters, identify the internal work or commitment to track, and recommend the next preparation step. "
                  "Do not send messages, mutate external systems, or invent facts. Return a concise operator summary.\n\n" +
                  json.dumps({"observation": {k: ev.get(k) for k in ("id", "text", "channel", "event_classes", "commitment", "provenance")},
                              "commitment_result": commitment_result, "authority": "INTERNAL_PREPARE_ONLY"}, ensure_ascii=False, default=str))
        result = ask_agent(prompt, context={"sources": [{"source": ev.get("provenance", {}).get("source_id", ev.get("channel")), "state": "VERIFIED_READ"}]},
                           tool_executor=lambda request: run_tool(request, store=_st()), max_iterations=3)
        analysis = {"status": result.get("status"), "provider": result.get("provider"),
                    "provider_state": result.get("provider_state"),
                    "summary": (result.get("answer") or "")[:2400],
                    "agent_trace": result.get("agent_trace", []), "iterations": result.get("agent_iterations"),
                    "recorded_at": _now(), "authority": "INTERNAL_PREPARE_ONLY"}
        _st().upsert("checkpoints", "proactive:analysis:" + str(ev.get("id")), analysis)
        return analysis
    except Exception as exc:
        failure = {"status": "UNAVAILABLE", "reason": type(exc).__name__, "recorded_at": _now(), "authority": "INTERNAL_PREPARE_ONLY"}
        _st().upsert("checkpoints", "proactive:analysis:" + str(ev.get("id")), failure)
        return failure

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
    # Keep durable commitments alive after their source event was processed.
    # This is preparation only: a follow-up draft may be created later, but no
    # external message is sent by the watcher.
    today = dt.date.today().isoformat()
    for commitment in commitments.open_rows(today, store=_st()):
        lifecycle = commitment.get("lifecycle")
        if lifecycle not in ("OVERDUE", "DUE_SOON"):
            continue
        op_id = commitment.get("op_id") or commitment.get("id")
        severity = "HIGH" if lifecycle == "OVERDUE" else "MEDIUM"
        response = "Prepare a follow-up for Gev's review; sending requires exact approval"
        out.append(_event("COMMITMENT_OVERDUE" if lifecycle == "OVERDUE" else "COMMITMENT_DUE_SOON",
                          "commitments", op_id, severity,
                          {"op_id": op_id, "who": commitment.get("who"), "what": commitment.get("what"),
                           "due": commitment.get("due"), "evidence": commitment.get("evidence", [])}, response,
                          requires_attention=True))
        _st().upsert("loops", "followup:" + str(op_id), {
            "loop_id": "followup:" + str(op_id), "kind": "PREPARED_COMMITMENT_FOLLOW_UP",
            "summary": commitment.get("what") or commitment.get("text"), "state": "OPEN",
            "source": commitment.get("source"), "commitment_id": op_id, "lifecycle": lifecycle,
            "next_action": response, "authority": "INTERNAL_ONLY", "evidence": commitment.get("evidence", []),
        })
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
            commitment_result = {"new": [], "merged": [], "weak_candidates": []}
            if "COMMITMENT" in ev["event_classes"] or ev.get("commitment"):
                candidates = commitments.extract(ev["text"], speaker=ev.get("sender") or "UNKNOWN",
                    channel=ev["channel"], record_id=ev["id"], received=ev["provenance"].get("retrieved_at"),
                    trusted=False)
                direction = (ev.get("commitment") or {}).get("kind")
                for candidate in candidates:
                    candidate["direction"] = direction
                commitment_result = commitments.ingest(candidates, origin="PROACTIVE_INBOUND", store=_st())
            _st().upsert("loops", "inbound:" + ev["id"], {
                "loop_id": "inbound:" + ev["id"], "kind": "PREPARED_INBOUND_WORK",
                "summary": ev["text"][:240], "state": "OPEN", "source": ev["provenance"],
                "event_classes": ev["event_classes"], "commitment": ev.get("commitment"), "confidence": "CANDIDATE",
                "authority": "INTERNAL_ONLY", "next_action": "Review and prepare governed follow-up",
                "commitment_result": commitment_result,
            })
            analysis = _claude_prepare_inbound(ev, commitment_result)
            alert = _event("INBOUND_WORK_DETECTED", ev["channel"], ev["id"], "MEDIUM",
                            ev["provenance"], "Review prepared follow-up", requires_attention=True)
            if analysis:
                alert["claude_preparation"] = {k: analysis.get(k) for k in ("status", "summary", "iterations", "agent_trace")}
                _st().upsert("alerts", alert.get("dedupe_key"), alert)
            out.append(alert)
        obs["processed_at"] = _now(); _st().upsert("channel_events", obs.get("op_id") or ev["id"], obs)
    if persist: _st().upsert("checkpoints","proactive:last_cycle",{"at":_now(),"events":len(out),"truth_mode":state.get("truth_mode")})
    return {"status":"PARTIAL_SUCCESS" if state.get("unavailable") else "CURRENT","at":state.get("at"),"events":out,"attention":queue,"state":state}

def events(): return _st().list("alerts")
def daily_cycle(): return run_cycle()
def weekly_cycle():
    r=run_cycle(); r["review"]="weekly management review prepared from current snapshot and evidence"; return r
def monthly_cycle():
    r=run_cycle(); r["review"]="monthly management review prepared; trend is INSUFFICIENT_HISTORY until enough production checkpoints exist"; return r
