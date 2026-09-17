"""Deterministic Deputy runtime integration facade.

This module connects the sealed architecture contracts to the existing Skill Engine
and Store without introducing a second runtime, memory, authority, or task database.
It is deliberately provider-neutral and fail-closed.
"""
from __future__ import annotations
import hashlib, json, sys, datetime
from pathlib import Path
try:
    from .brain_router import route
    from .work_orchestrator import create_node, validate_graph
except ImportError:
    from brain_router import route
    from work_orchestrator import create_node, validate_graph

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
if str(SKILLS) not in sys.path:
    sys.path.insert(0, str(SKILLS))

class RuntimeBlocked(RuntimeError):
    pass

_OWNER_BY_PRIMITIVE = {
    "policy": "CONTROL_PLANE", "repository": "CONTROL_PLANE", "brand": "DESIGN_SYSTEM",
    "template": "DESIGN_SYSTEM", "knowledge": "KNOWLEDGE", "task": "COMMAND_CENTER",
    "state": "COMMAND_CENTER", "vault": "VAULT", "external": "EXTERNAL_SYSTEM",
    "message": "INBOUND_EVIDENCE", "report": "GENERATED_OUTPUT", "history": "HISTORY",
}
_STATUS_ORDER = ("PLAN_PREPARED", "TASK_PREPARED", "TASK_AUTHORIZED", "TASK_CREATED",
                 "TASK_IN_PROGRESS", "TASK_BLOCKED", "TASK_COMPLETED", "RESULT_VERIFIED")


def _stable(*parts):
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:16]


def resolve_truth(sources, *, primitive=None):
    """Resolve by canonical ownership and currentness; never latest-file-wins."""
    rows=list(sources or [])
    if not rows: raise RuntimeBlocked("NO_SOURCE")
    expected=_OWNER_BY_PRIMITIVE.get(str(primitive or "").lower()) if primitive else None
    for row in rows:
        if not row.get("provenance"): raise RuntimeBlocked("MISSING_PROVENANCE")
        if expected and row.get("owner") != expected: raise RuntimeBlocked("WRONG_CANONICAL_OWNER")
    live=[r for r in rows if r.get("authority") == "current" and r.get("freshness") not in ("stale","unverified") and not r.get("superseded") and r.get("certification", "certified") != "revoked"]
    if not live: raise RuntimeBlocked("NO_CURRENT_AUTHORITY")
    values={json.dumps(r.get("value"),sort_keys=True,default=str) for r in live}
    if len(values)>1: raise RuntimeBlocked("CONFLICTING_AUTHORITATIVE_SOURCES")
    return {"value":live[0].get("value"),"authority":live[0].get("owner"),"provenance":[r["provenance"] for r in live],"status":"RESOLVED"}


class DeputyRuntime:
    """One Deputy identity, one Store, one Action Runtime boundary."""
    identity = "DEPUTY"

    def __init__(self, *, state_dir=None, knowledge=None, vault=None, capabilities=None):
        self._store_module = None
        import store
        self._store_module = store
        self.store = store.get(state_dir)
        self.knowledge = knowledge
        self.vault = vault
        self.capabilities = capabilities or {}
        if self.identity != "DEPUTY":
            raise RuntimeBlocked("INVALID_DEPUTY_IDENTITY")

    def discover_capability(self, capability_id):
        row = self.capabilities.get(capability_id)
        if not row or row.get("certification") != "certified" or row.get("registered") is not True:
            raise RuntimeBlocked("CAPABILITY_UNAVAILABLE")
        return dict(row)

    @staticmethod
    def discover_from_control_plane(control_plane_root, capability_id):
        """Read the canonical Control Plane repository registry; undeclared or uncertified is unavailable."""
        p = Path(control_plane_root) / "registry" / "repositories.json"
        try: data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc: raise RuntimeBlocked("CONTROL_PLANE_UNAVAILABLE") from exc
        rows=[]
        for repo in data.get("repositories", []):
            for cap in repo.get("capabilities", []):
                if cap.get("capability_id") == capability_id:
                    row=dict(cap); row.setdefault("repository", repo.get("repository")); row.setdefault("owner", repo.get("owner")); rows.append(row)
        if len(rows) != 1 or rows[0].get("certification") != "certified" or rows[0].get("health") != "healthy":
            raise RuntimeBlocked("CAPABILITY_UNAVAILABLE")
        return rows[0]

    def persist_work_graph(self, request, *, owner="GEV", brains=None, source=None, due=None):
        """Persist the complete approved hierarchy through the existing Store."""
        types=("GOAL","STRATEGY","ROADMAP","INITIATIVE","ACTION_PLAN","TASK","CHECKPOINT","EVIDENCE","VERIFIED_COMPLETION")
        nodes=[]; parent=None
        for kind in types:
            title = request if kind == "GOAL" else f"{kind}: {request}"
            status = "PROPOSED" if kind != "ACTION_PLAN" else "PLANNED"
            node=create_node(kind,title,owner=owner,status=status,parent_id=parent,source=source,brains=brains,approval="PENDING" if kind in ("TASK","ACTION_PLAN") else "NOT_REQUIRED",evidence=None)
            node.update({"priority":"NORMAL", "due":due, "dependencies":[], "next_action":"review", "review_cadence":"WEEKLY"})
            nodes.append(node); parent=node["id"]
        # validate graph before writing; record each node in canonical commitments table
        errors=validate_graph(nodes)
        if errors: raise RuntimeBlocked("INVALID_WORK_GRAPH:"+";".join(errors))
        saved=[]
        for n in nodes:
            saved.append(self.store.record("commitments", n["id"], {"kind":"WORK_GRAPH_NODE", **n}))
        return {"nodes":nodes,"statuses":list(_STATUS_ORDER),"records":saved,"root":nodes[0]["id"]}

    def transition_work(self, node, target, *, evidence=None, approval=False):
        if target not in _STATUS_ORDER: raise RuntimeBlocked("INVALID_WORK_STATUS")
        n=dict(node); current=n.get("lifecycle", "PLAN_PREPARED")
        if target in ("TASK_AUTHORIZED","TASK_CREATED") and not approval: raise RuntimeBlocked("APPROVAL_REQUIRED")
        if target in ("TASK_COMPLETED","RESULT_VERIFIED") and not evidence: raise RuntimeBlocked("COMPLETION_EVIDENCE_REQUIRED")
        n["lifecycle"]=target; n["evidence"]=evidence
        return n

    def plan(self, request, *, owner="GEV", source=None, events=None):
        routing = route(request)
        if any(x["brain_id"] not in {b["id"] for b in json.loads((Path(__file__).parent / "professional_brains.json").read_text())["brains"]} for x in routing["selected_brains"]):
            raise RuntimeBlocked("UNSUPPORTED_BRAIN")
        graph = [create_node("ACTION_PLAN", request, owner=owner, brains=[x["brain_id"] for x in routing["selected_brains"]], source=source, approval="NOT_REQUIRED")]
        errors = validate_graph(graph)
        if errors: raise RuntimeBlocked("INVALID_WORK_GRAPH:" + ";".join(errors))
        payload = {"runtime":"DEPUTY", "identity":self.identity, "request":request,
                   "routing":routing, "events":events or [], "graph":graph,
                   "authority":{"writes":"ACTION_RUNTIME_ONLY", "approval":"GEV_REQUIRED_FOR_MATERIAL_MUTATION"},
                   "synthesis":{"required":routing["synthesis_required"], "status":"ONE_DEPUTY_CONTEXT"}}
        oid = _stable("action-plan", request, owner)
        saved = self.store.record("commitments", oid, payload)
        return {"status":"PLANNED", "op_id":oid, "duplicate":saved["status"] == "DUPLICATE", **payload}

    def load_plan(self, op_id):
        row = self.store.get("commitments", op_id)
        if not row: raise RuntimeBlocked("PLAN_UNAVAILABLE")
        return row

    def complete(self, node, evidence):
        updated = dict(node); updated["status"] = "VERIFIED"; updated["evidence"] = evidence
        errors = validate_graph([updated])
        if errors: raise RuntimeBlocked("COMPLETION_EVIDENCE_REQUIRED")
        return updated

    def synthesize(self, query, *, knowledge=None, vault_reference=None):
        if knowledge is None: raise RuntimeBlocked("KNOWLEDGE_UNAVAILABLE")
        items = knowledge.search(query)
        if not items: raise RuntimeBlocked("KNOWLEDGE_NO_CANONICAL_EVIDENCE")
        evidence=[{"id":x.get("id"),"source":x.get("source"),"status":x.get("status"),"freshness":x.get("freshness"),"owner":x.get("owner"),"sensitivity":x.get("sensitivity")} for x in items]
        return {"identity":"DEPUTY","query":query,"evidence":evidence,"vault_reference":vault_reference,"authority":"KNOWLEDGE_NOT_POLICY"}

    def knowledge_context(self, query):
        if not self.knowledge: raise RuntimeBlocked("KNOWLEDGE_UNAVAILABLE")
        return self.knowledge.search(query)

    def synthesize_from_estate(self, control_plane_root, knowledge_root, query, *, vault_root=None, vault_reference_id=None):
        """Consume canonical Knowledge/Vault repositories through governed estate declarations."""
        knowledge_cap = self.discover_from_control_plane(control_plane_root, "knowledge.search")
        catalog_path = Path(knowledge_root) / knowledge_cap.get("path", "knowledge/index/catalog.json")
        if not catalog_path.is_file():
            raise RuntimeBlocked("KNOWLEDGE_CATALOG_UNAVAILABLE")
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeBlocked("KNOWLEDGE_CATALOG_INVALID") from exc
        items = []
        needle = str(query).lower()
        for entry in catalog.get("items", []):
            if str(entry.get("status", "")).lower() != "canonical":
                continue
            item_path = Path(knowledge_root) / str(entry.get("path", ""))
            try:
                item = json.loads(item_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise RuntimeBlocked("KNOWLEDGE_ITEM_INVALID") from exc
            if str(item.get("status", "")).lower() != "canonical":
                continue
            if not item.get("source") or not item.get("source", {}).get("hash"):
                raise RuntimeBlocked("KNOWLEDGE_PROVENANCE_MISSING")
            if item.get("freshness", {}).get("state") not in ("current", "verified"):
                continue
            haystack = " ".join(str(item.get(k, "")) for k in ("id", "title", "domain")).lower()
            if needle and needle not in haystack and len(items) > 0:
                continue
            items.append(item)
        if not items:
            raise RuntimeBlocked("KNOWLEDGE_NO_CANONICAL_EVIDENCE")
        vault = None
        if vault_reference_id is not None:
            if vault_root is None:
                raise RuntimeBlocked("VAULT_UNAVAILABLE")
            vault_cap = self.discover_from_control_plane(control_plane_root, "vault.reference")
            index_path = Path(vault_root) / vault_cap.get("path", "vault/index.json")
            try:
                index = json.loads(index_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise RuntimeBlocked("VAULT_INDEX_INVALID") from exc
            ref_path = None
            if any(r.get("id") == vault_reference_id for r in index.get("references", [])):
                for candidate in (Path(vault_root) / "vault" / "references").glob("*.json"):
                    try:
                        if json.loads(candidate.read_text(encoding="utf-8")).get("id") == vault_reference_id:
                            ref_path = candidate
                            break
                    except (OSError, ValueError):
                        continue
            if ref_path is None:
                raise RuntimeBlocked("VAULT_REFERENCE_UNAVAILABLE")
            data = json.loads(ref_path.read_text(encoding="utf-8"))
            vault = {k: data.get(k) for k in ("id", "purpose", "owner_principal", "target_system", "sensitivity", "required_for_bootstrap", "last_verified")}
        evidence = [{"id": x.get("id"), "source": x.get("source"), "freshness": x.get("freshness"), "owner": x.get("owner"), "status": x.get("status"), "sensitivity": x.get("sensitivity")} for x in items]
        return {"identity": self.identity, "query": query, "evidence": evidence, "vault_reference": vault, "authority": "KNOWLEDGE_NOT_POLICY"}

    def vault_context(self, reference_id):
        if not self.vault: raise RuntimeBlocked("VAULT_UNAVAILABLE")
        return self.vault.vault_reference(reference_id)

    def strategy_assessment(self, strategy, *, evidence=None, kpis=None, capacity=None):
        """Produce a non-mutating Strategy/PMO assessment; execution remains approval-bound."""
        evidence = list(evidence or []); kpis = list(kpis or [])
        gaps = []
        if not kpis: gaps.append("MISSING_KPI")
        if not evidence: gaps.append("MISSING_CURRENT_STATE_EVIDENCE")
        if capacity is not None and capacity.get("required", 0) > capacity.get("available", 0):
            gaps.append("CAPACITY_CONTRADICTION")
        return {"status":"ANALYSIS", "lifecycle":"DIAGNOSIS", "strategy":strategy,
                "gaps":gaps, "recommendation_required":bool(gaps),
                "authority":"NON_MUTATING_ANALYSIS", "owner_decision_required":bool(gaps)}

    def reconcile_inbound(self, event, *, existing_ids=None):
        """Normalize untrusted inbound evidence without granting authority or creating tasks."""
        if not event.get("provenance") or event.get("trusted_authority"):
            raise RuntimeBlocked("UNTRUSTED_INPUT_BOUNDARY")
        eid = event.get("source_id") or _stable(event.get("channel"), event.get("text"))
        duplicate = eid in set(existing_ids or [])
        classes = list(event.get("classes") or ["NO_ACTION"])
        return {"event_id":eid, "duplicate":duplicate, "classes":classes,
                "status":"PROPOSAL_ONLY", "authority_granted":False,
                "canonical_knowledge":False, "approval_required":any(c in classes for c in ("ACTION","DECISION_REQUIRED"))}

    def compose_output(self, output_type, *, template=None, provenance=None):
        """Resolve output readiness without becoming a second Design System."""
        if not provenance: raise RuntimeBlocked("MISSING_PROVENANCE")
        if not template: return {"status":"TEMPLATE_GAP", "output_type":output_type, "provenance":provenance}
        return {"status":"STRUCTURALLY_VALIDATED", "output_type":output_type,
                "template":template, "visual_certification":"REQUIRED", "provenance":provenance}

    def follow_through(self, nodes):
        """Return management exceptions from the same persisted work graph."""
        rows=[]
        for n in nodes:
            if n.get("status") in ("BLOCKED",) or n.get("status") not in ("VERIFIED", "COMPLETED"):
                rows.append({"id":n.get("id"), "status":n.get("status"), "owner":n.get("owner"),
                             "next_action":n.get("next_action"), "exception":n.get("status")})
        return {"status":"READY", "exceptions":rows, "views":["DAILY","WEEKLY","MONTHLY"],
                "authority":"COMMAND_CENTER_OPERATIONAL_STATE"}

    def prepare_material_action(self, action):
        return {"status":"APPROVAL_REQUIRED", "action":action, "authority":"ACTION_RUNTIME", "approved":False}
