# -*- coding: utf-8 -*-
"""KPI / TARGET LAYER on the Business Operating Model (single truth: .claude/business kpis.json · targets.json · ownership.json).
For any KPI reference Deputy resolves: id · definition · formula · owner role → person · target (APPROVED only) · period · source system →
integration · required fields · freshness · current value AVAILABILITY · status · provenance. Statuses:
  OK (definition + live source usable) · UNAVAILABLE (source not connected / deferred) · TARGET_UNKNOWN · KPI_DEFINITION_MISSING.
No value is ever invented: a KPI without a usable live source has current_value=UNAVAILABLE with the exact missing capability."""
import re, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "integrations"))
import business

SYSTEM_TO_INTEGRATION = {"SYS-MB": "INT-MB", "SYS-B24": "INT-B24", "SYS-CC": "INT-TASKS", "SYS-OL": "INT-OL-MAIL", "SYS-PBX": None, "SYS-NET": None, "SYS-PORTAL": None, "SYS-CHURN": None}
DIMENSION_KPIS = {"target_vs_actual": ["K-NEW"], "sales_pace": ["K-NEW"], "forecast": ["K-NEW"], "funnel_conversion": ["K-LEADS", "K-CALL-CONV"], "pipeline_health": ["K-LEADS"], "stagnant_opportunities": ["K-LEADS"],
                  "lost_opportunities": ["K-LEADS"], "retention_churn": ["K-CHURN", "K-CHURN-RISK", "K-RETAINED"], "revenue_leakage": ["K-LEAK", "K-COLLECT"], "sales_backlog": ["K-ACTIVATION-DAYS"], "follow_up_failures": ["K-PTP"]}

def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())

def catalog():
    m = business.load(); return list(((m or {}).get("kpis") or {}).get("kpis", []))

def find(ref):
    """KPI by id (K-…, R-…) or by name/definition words; None when nothing matches (KPI_DEFINITION_MISSING)."""
    if not ref: return None
    r = str(ref).strip(); m = business.load() or {}
    for k in catalog():
        if k["kpi_id"].lower() == r.lower(): return k
    for code, items in ((m.get("kpis") or {}).get("role_kpis") or {}).items():
        for k in items:
            if k["kpi_id"].lower() == r.lower(): return {**k, "definition": k["name"], "business_purpose": f"role KPI of {code}", "formula": "UNKNOWN", "reporting_frequency": "monthly", "role": code, "drill_down": []}
    hits = business.find_kpis(r, limit=3)
    if hits and (len(hits) == 1 or _norm(hits[0]["name"]) in _norm(r)): return hits[0]
    return None

def _source_state(iid):
    if not iid: return {"integration_id": None, "state": "NO_INTEGRATION", "usable": False, "reason": "no integration exists for this source system (manual/Excel/PBX/monitoring) — value must be supplied"}
    try:
        import layer, registry
        st = {s["integration_id"]: s for s in layer.status()}.get(iid) or {}; spec = registry.get(iid) or {}
        if spec.get("deferred"): return {"integration_id": iid, "state": "DEFERRED", "usable": False, "reason": f"{iid} deferred by {spec['deferred'].get('by')} since {spec['deferred'].get('since')} — no live value"}
        usable = st.get("certification") in ("VERIFIED_READ", "RELIABLE_READ") and st.get("health") in ("AVAILABLE", "DEGRADED")
        return {"integration_id": iid, "state": "LIVE_READABLE" if usable else (st.get("certification") or "DECLARED"), "usable": usable, "reason": None if usable else f"{iid} is {st.get('certification', 'DECLARED')} / {st.get('health')} — no live value", "last_success": st.get("last_success")}
    except Exception as e: return {"integration_id": iid, "state": "UNAVAILABLE", "usable": False, "reason": f"integration layer error {type(e).__name__}"}

def _owner(k):
    m = business.load() or {}; oe = None
    for e in ((m.get("ownership") or {}).get("ownership") or []):
        if k["kpi_id"] in str(e.get("primitive", "")): oe = e; break
    if oe: r = business.resolve_owner(oe); return {"role": r.get("owner_role"), "role_codes": r.get("role_codes"), "status": r.get("status"), "person": r.get("person") or "UNKNOWN", "person_status": r.get("person_status"), "candidates": r.get("candidates", []), "src": oe.get("src", [])}
    codes = re.findall(r"\((\d+\.\d+|EXEC-[A-Z]+)\)", str(k.get("owner") or "")) or re.findall(r"^(\d+\.\d+)", str(k.get("owner") or ""))
    if codes:
        p = business.person_for_role(codes[0]); return {"role": k.get("owner"), "role_codes": codes, "status": "ROLE_DEFINED", "person": p.get("person") or "UNKNOWN", "person_status": p["status"], "candidates": p.get("candidates", []), "src": k.get("src", [])}
    if "CONFLICT" in str(k.get("owner", "")): return {"role": k.get("owner"), "role_codes": [], "status": "CONFLICT", "person": "UNKNOWN", "person_status": "SOURCE_CONFLICT", "candidates": [], "src": k.get("src", [])}
    return {"role": k.get("owner") or "UNKNOWN", "role_codes": [], "status": "OWNER_UNKNOWN" if not k.get("owner") else "ROLE_DEFINED_NO_CODE", "person": "UNKNOWN", "person_status": "PERSON_UNKNOWN", "candidates": [], "src": k.get("src", [])}

def resolve(ref):
    """Full KPI binding with provenance. Never invents a value or a target."""
    k = find(ref)
    if not k: return {"status": "KPI_DEFINITION_MISSING", "ref": ref, "reason": "no KPI with this id/name in the Business Operating Model — define it in bm_kpis.py (with source) and rebuild", "provenance": {"model": (business.model_id() or {}).get("model_version")}}
    tg = [t for t in business.targets_for(k["kpi_id"]) if t.get("kind") == "KPI_TARGET"]
    approved = [t for t in tg if t.get("status") == "APPROVED"]; proposed = [t for t in tg if t.get("status") != "APPROVED"]
    target = ({"value": approved[0]["value"], "unit": approved[0].get("unit"), "status": "APPROVED", "approver": approved[0].get("approver"), "effective_date": approved[0].get("effective_date"), "review_date": approved[0].get("review_date"), "src": approved[0].get("src"), "target_id": approved[0]["target_id"]} if approved
              else {"value": "UNKNOWN", "status": "TARGET_UNKNOWN", "proposed": [{"target_id": t["target_id"], "value": t.get("value"), "status": t.get("status"), "approver": t.get("approver")} for t in proposed], "reason": "no APPROVED target in targets.json" + (" — proposals exist, not approved" if proposed else "")})
    sys_id = str(k.get("source") or "").split(" ")[0].split("/")[0]; iid = SYSTEM_TO_INTEGRATION.get(sys_id); src = _source_state(iid)
    status = "OK" if src["usable"] else "UNAVAILABLE"
    if target["status"] == "TARGET_UNKNOWN" and status == "OK": status = "TARGET_UNKNOWN"
    return {"status": status, "kpi_id": k["kpi_id"], "name": k["name"], "kind": k.get("kind"), "definition": k.get("definition"), "formula": k.get("formula", "UNKNOWN"), "unit": k.get("unit"), "period": k.get("reporting_frequency"),
            "owner": _owner(k), "target": target, "thresholds": {"warning": k.get("warning_threshold", "UNKNOWN"), "critical": k.get("critical_threshold", "UNKNOWN")},
            "source": {"system": k.get("source"), "system_id": sys_id or None, "integration": iid, **src}, "required_fields": k.get("drill_down", []), "freshness": src.get("last_success"),
            "current_value": "UNAVAILABLE" if not src["usable"] else "READABLE (query the live source; not computed here)", "drivers": k.get("driver_kpis", []), "outcomes": k.get("outcome_kpis", []), "action_when_off_target": k.get("action_when_off_target"),
            "provenance": {"src": k.get("src", []), "conf": k.get("conf"), "model": (business.model_id() or {}).get("model_version")}, "note": k.get("note")}

def bindings_for_dimensions(vis=None):
    """Mission 5 sales dimensions → the KPI bindings they consume (status per KPI). Consumed by intelligence.sales_intelligence."""
    out = {}
    for dim, ids in DIMENSION_KPIS.items():
        rows = []
        for kid in ids:
            r = resolve(kid); rows.append({"kpi_id": kid, "status": r["status"], "target": r.get("target", {}).get("value", "UNKNOWN"), "integration": (r.get("source") or {}).get("integration"), "owner_role": (r.get("owner") or {}).get("role")})
        out[dim] = rows
    return out

def for_text(text, limit=4):
    return [{"kpi_id": k["kpi_id"], "name": k["name"], "status": resolve(k["kpi_id"])["status"]} for k in business.find_kpis(text, limit=limit)]
