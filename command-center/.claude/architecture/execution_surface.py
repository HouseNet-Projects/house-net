"""Human-facing controlled execution surface over the canonical Action Runtime.

No provider calls happen in preview or preparation.  All mutation requests are
delegated to ``skills.actions`` so approval, idempotency, audit and verification
remain single-owner concerns.
"""
from __future__ import annotations
import datetime as _dt
import capabilities
import actions


def capability_matrix():
    out = []
    for iid in capabilities.registry.ids():
        read = bool(capabilities.registry.get(iid).get("read_ops"))
        for op, spec in (capabilities.WRITE_OPS.get(iid) or {}).items():
            cap = capabilities.capability(iid, op)
            out.append({"source": iid, "operation": op, "read": read, "prepare": bool(cap.get("implemented")),
                        "write_implemented": bool(cap.get("implemented")), "write_certified": cap.get("certification_status"),
                        "approval_required": True, "verification": cap.get("verification_method"),
                        "live_binding": bool(cap.get("configured") and cap.get("connected")), "limitation": cap.get("note")})
    return out


def preview(requests):
    """Return a dry-run plan; the provider is never resolved or called."""
    return {"mode": "PREVIEW", "state": "PREPARED", "actions": [{"action_id": r.get("action_id"),
        "target": f"{r.get('target_system')}:{r.get('target_operation')}", "effect": r.get("expected_effect"),
        "approval_required": True, "risk": r.get("risk_class", "R2"), "verification": r.get("verification_method", "read-back")}
        for r in requests], "provider_calls": 0}


def approval_inbox(session_id=None):
    return [{"action_id": a["action_id"], "mission": a.get("session_id"), "target": a["request"].get("operation_id"),
             "effect": a["request"].get("expected_effect"), "risk": a["request"].get("risk_class"),
             "fingerprint": a["request"].get("action_fingerprint"), "state": a["state"],
             "expires_at": (a.get("approval") or {}).get("expires_at"), "card": a.get("card")}
            for a in actions.pending(session_id)]


def prepare_candidate(*, mission_id, target_system, target_operation, target_object_type, parameters,
                      intent, domain="operations", expected_effect="Apply the exact proposed change",
                      postcondition="Provider read-back matches the proposed change"):
    req = actions.build_request(skill_id="deputy_execution", business_intent=intent, business_domain=domain,
        target_system=target_system, target_operation=target_operation, target_object_type=target_object_type,
        parameters=parameters, expected_effect=expected_effect, expected_postcondition=postcondition,
        correlation_id=mission_id)
    return actions.prepare(req, session_id=mission_id)


def execute_approved(action_id, *, token_id=None):
    return actions.execute(action_id, token_id=token_id)
