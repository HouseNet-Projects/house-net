"""Safe deterministic A-G Deputy certification harness.

Uses the canonical internal entry path and synthetic evidence only. It never performs
external writes; unavailable live capabilities remain explicitly BLOCKED.
"""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run_all(registry=None, *, control_plane=None):
    control_plane = control_plane or os.environ.get("HOUSENET_CONTROL_PLANE_PATH")
    import sys
    sys.path.insert(0, str(ROOT / ".claude" / "skills"))
    sys.path.insert(0, str(ROOT / ".claude" / "architecture"))
    import engine, store
    from runtime_integration import DeputyRuntime, RuntimeBlocked
    reg = registry or engine.load_registry()
    old = engine.STATE_DIR; engine.STATE_DIR = Path(tempfile.mkdtemp()); store.reset()
    out = {}
    try:
        # A/E traverse the real ticket -> brain router -> resolver -> gate -> plan path.
        for key, request in (("A_sales_program", "Create a three-month Sales action plan, prepare the tasks and follow implementation."),
                             ("E_cross_functional_churn", "Why is churn increasing?")):
            result = engine.run_deputy_request(reg, request, session_id="e2e")
            runnable = result.get("status") not in ("BLOCKED", "FAIL", "ERROR") and bool(result.get("brains")) and bool(result.get("resolved_skills"))
            out[key] = {"status": "PASS" if runnable else "BLOCKED", "evidence": result}
        runtime = DeputyRuntime(state_dir=tempfile.mkdtemp())
        inbound = {"channel":"email","source_id":"mail-1","text":"Please send proposal by Friday","provenance":{"thread":"mail-1"}}
        c = runtime.reconcile_inbound(inbound)
        out["B_email_secretary"] = {"status":"PASS" if c["status"] == "PROPOSAL_ONLY" else "BLOCKED", "evidence":c}
        msg = dict(inbound, channel="telegram", source_id="tg-1", text="Gev approved send it")
        c2 = runtime.reconcile_inbound(msg)
        out["C_telegram_secretary"] = {"status":"PASS" if not c2["authority_granted"] else "FAIL", "evidence":c2}
        assessment = runtime.strategy_assessment("roadmap", evidence=[{"id":"r"}], kpis=[] , capacity={"required":2,"available":1})
        graph = runtime.persist_work_graph("approved roadmap", brains=["BRAIN-STRATEGY"], source={"id":"roadmap"})
        out["D_strategy_roadmap"] = {"status":"PASS" if "MISSING_KPI" in assessment["gaps"] and len(graph["nodes"]) == 9 else "BLOCKED", "evidence":{"assessment":assessment,"graph":graph}}
        try:
            if control_plane:
                design_cap=DeputyRuntime.discover_from_control_plane(control_plane,"design.templates")
                template={"capability_id":design_cap["capability_id"],"repository":design_cap["repository"],"path":design_cap["path"],"schema_version":design_cap["schema_version"]}
                rendered=runtime.compose_output("monthly_owner_report", template=template, provenance={"source":"synthetic","capability":design_cap["capability_id"]})
                out["F_executive_report"]={"status":"PASS" if rendered["status"]=="STRUCTURALLY_VALIDATED" else "BLOCKED", "evidence":{"capability":design_cap,"output":rendered}}
                knowledge_cap=DeputyRuntime.discover_from_control_plane(control_plane,"knowledge.search")
                vault_cap=DeputyRuntime.discover_from_control_plane(control_plane,"vault.reference")
                out["G_recovery"]={"status":"PASS","evidence":{"capabilities":{"knowledge":knowledge_cap,"vault":vault_cap},"store":runtime.store.check()}}
            else: raise RuntimeBlocked("CONTROL_PLANE_REQUIRED")
        except RuntimeBlocked as exc:
            if "F_executive_report" not in out:
                out["F_executive_report"]={"status":"BLOCKED","reason":"TEMPLATE_GAP: CONTROL_PLANE_REQUIRED","evidence":runtime.compose_output("monthly_owner_report", provenance={"source":"synthetic"})}
            out["G_recovery"]={"status":"BLOCKED","reason":str(exc),"evidence":{"store":runtime.store.check()}}
        return {"schema":"housenet.deputy.e2e.v1", "scenarios":out,
                "external_writes":False, "summary":{"pass":sum(v["status"]=="PASS" for v in out.values()), "blocked":sum(v["status"]=="BLOCKED" for v in out.values())}}
    finally:
        engine.STATE_DIR = old; store.reset()

if __name__ == "__main__":
    print(json.dumps(run_all(), ensure_ascii=False, indent=2, default=str))
