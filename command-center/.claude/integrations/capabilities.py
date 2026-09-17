# -*- coding: utf-8 -*-
"""CAPABILITY REGISTRY — honest, machine-readable truth for every integration operation (read AND write).
Levels: DECLARED (spec only) · IMPLEMENTED (adapter code exists) · CONFIGURED (secrets/config present) · CONNECTED (a real read succeeded) ·
VERIFIED_READ (integration certification) · VERIFIED_WRITE (a Gev-approved live write was executed and read back) · UNAVAILABLE (cannot work here).
Theoretical code is never a live capability: VERIFIED_WRITE comes only from .claude/state/durable/write_certifications.json, written by the Action Runtime
after an approved, verified live action. Every write requires Gev approval (approval_rule.json) — risk class changes scrutiny, never autonomy."""
import sys, json, pathlib, datetime
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import registry, health, int_secrets as _secrets

WRITE_CERTS = ROOT / ".claude" / "state" / "durable" / "write_certifications.json"

# write operations: risk class, authority level, idempotency + verification method, adapter (None = UNSUPPORTED)
WRITE_OPS = {
 "INT-TASKS": {
  "tasks.create": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "stable key (owner + normalized title); open task with the same key = duplicate", "verification_method": "read-back of the created row (id, title, owner, deadline, status)", "adapter": "adapter_tasks_write", "retry_safe_when_absent": True},
  "tasks.update": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "target id + changed fields; precondition snapshot (status/due/owner) must be unchanged", "verification_method": "read-back of changed fields", "adapter": "adapter_tasks_write", "retry_safe_when_absent": True},
  "tasks.assign": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "target id + owner", "verification_method": "read-back owner", "adapter": "adapter_tasks_write", "retry_safe_when_absent": True},
  "tasks.close": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "target id + status; completion evidence required", "verification_method": "read-back status", "adapter": "adapter_tasks_write", "retry_safe_when_absent": True},
  "tasks.reopen": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "target id + status", "verification_method": "read-back status", "adapter": "adapter_tasks_write", "retry_safe_when_absent": True},
  "tasks.note": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "target id + note text", "verification_method": "read-back comment", "adapter": "adapter_tasks_write", "retry_safe_when_absent": True},
 },
 "INT-OL-CAL": {
  "calendar.create": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "subject + start window; existing matching event = duplicate", "verification_method": "read-back by EntryID (subject, start/end, timezone, participants)", "adapter": "adapter_outlook_write", "retry_safe_when_absent": True},
  "calendar.update": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "EntryID + change set; precondition snapshot of the event", "verification_method": "read-back by EntryID", "adapter": "adapter_outlook_write", "retry_safe_when_absent": False},
  "calendar.cancel": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "EntryID; cancelled/deleted event cannot be cancelled twice", "verification_method": "read-back absence/cancelled state", "adapter": "adapter_outlook_write", "retry_safe_when_absent": False},
 },
 "INT-OL-MAIL": {
  "mail.draft": {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "recipient + subject + body hash; existing draft = duplicate", "verification_method": "read-back of the draft (Drafts folder: recipient, subject, body metadata)", "adapter": "adapter_outlook_write", "retry_safe_when_absent": True},
  "mail.send": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "recipient + subject + body hash; Sent Items evidence = already sent", "verification_method": "Sent Items evidence (recipient, subject, sent time, EntryID/ConversationID)", "adapter": "adapter_outlook_write", "retry_safe_when_absent": False},
 },
 "INT-B24": {
  "tasks.create": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "title + responsible + deadline; tasks.task.list read-back", "verification_method": "tasks.task.get read-back", "adapter": "adapter_bitrix24_write", "retry_safe_when_absent": True},
  "crm.deal.update": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "deal id + field set; DATE_MODIFY precondition", "verification_method": "crm.deal.get read-back of changed fields", "adapter": "adapter_bitrix24_write", "retry_safe_when_absent": False},
  "crm.activity.create": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "owner + subject + deadline", "verification_method": "crm.activity.list read-back", "adapter": "adapter_bitrix24_write", "retry_safe_when_absent": True},
 },
 "INT-MB": {
  "tariff.change": {"risk_class": "R3", "authority_required": "EXECUTE_MATERIAL", "idempotency_method": "UNDEFINED — interface not inventoried", "verification_method": "UNDEFINED", "adapter": None, "category": "MATERIAL_WRITE", "note": "WRITE NOT CERTIFIED: no interface, no object/ownership semantics, no verification — unsupported until inventoried and separately certified"},
  "subscriber.suspend": {"risk_class": "R3", "authority_required": "EXECUTE_MATERIAL", "idempotency_method": "UNDEFINED", "verification_method": "UNDEFINED", "adapter": None, "category": "MATERIAL_WRITE", "note": "WRITE NOT CERTIFIED: customer-impacting; unsupported"},
 },
}

def write_spec(iid): return {"adapter": None, "ops": {}} | {"adapter": next((o["adapter"] for o in WRITE_OPS.get(iid, {}).values() if o.get("adapter")), None), "ops": WRITE_OPS.get(iid, {})}

WRITE_OPS["INT-TG"] = {
 "chat.send":  {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "runtime key (no provider read-back)", "verification_method": "PROVIDER_ACCEPTED only (message_id) — no independent read-back; full certification needs a second-source confirmation", "adapter": "adapter_telegram_write", "retry_safe_when_absent": False, "category": "MATERIAL_WRITE", "note": "outbound to allowlisted chats only; with on_behalf_of_gev it is sent AS GEV over the business connection — the provider right rights.can_reply is capability, never authority, and every send still needs Gev's approval"},
 "chat.reply": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "runtime key (no provider read-back)", "verification_method": "PROVIDER_ACCEPTED only (message_id) — no independent read-back", "adapter": "adapter_telegram_write", "retry_safe_when_absent": False, "category": "MATERIAL_WRITE"},
}
WRITE_OPS["INT-WA"] = {
 "chat.send_text":     {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "runtime key + outbound log (wamid)", "verification_method": "provider delivery status events via the verified webhook (sent/delivered/read; failed surfaced) — async, reconcile first", "adapter": "adapter_whatsapp_write", "retry_safe_when_absent": False, "category": "MATERIAL_WRITE", "note": "free-form text only inside the provider's customer-service window"},
 "chat.send_template": {"risk_class": "R2", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "runtime key + outbound log (wamid)", "verification_method": "provider delivery status events via the verified webhook — async, reconcile first", "adapter": "adapter_whatsapp_write", "retry_safe_when_absent": False, "category": "MATERIAL_WRITE", "note": "approved template + exact variables; never substituted for a text message"},
}

def _write_certs():
    try: return json.loads(WRITE_CERTS.read_text(encoding="utf-8")) if WRITE_CERTS.exists() else {}
    except ValueError: return {}

def record_write_certification(iid, op, action_id, evidence):
    """Called by the Action Runtime after a Gev-approved, VERIFIED live write flagged as certification. Durable (versioned) evidence."""
    d = _write_certs(); d.setdefault(iid, {})[op] = {"action_id": action_id, "verified_at": datetime.datetime.now().isoformat(timespec="seconds"), "evidence": evidence}
    WRITE_CERTS.parent.mkdir(parents=True, exist_ok=True); WRITE_CERTS.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"); return d[iid][op]

def _read_cert(iid):
    p = HERE / "certification.json"
    try: return (json.loads(p.read_text(encoding="utf-8")).get("integrations", {}) if p.exists() else {}).get(iid, {})
    except ValueError: return {}

def capability(iid, op):
    """One honest capability row for (integration, operation)."""
    spec = registry.get(iid) or {}; h = health.get(iid) or {}; rc = _read_cert(iid); wc = _write_certs().get(iid, {}).get(op)
    read = op in (spec.get("read_ops") or {}); w = WRITE_OPS.get(iid, {}).get(op)
    if not read and not w: return {"integration_id": iid, "operation": op, "read_or_write": "unknown", "implemented": False, "configured": False, "connected": False, "runtime_available": False, "level": "UNAVAILABLE", "note": "operation not declared"}
    implemented = bool(read) or bool(w and w.get("adapter"))
    secrets = spec.get("auth", {}).get("secrets", [])
    configured = bool(spec) and (not secrets or (spec.get("adapter") != "adapter_mikrobill" and all(_secrets.load_config(iid).get(s) for s in secrets)))
    connected = bool(h.get("last_success")) and h.get("status") in ("AVAILABLE", "DEGRADED")
    row = {"integration_id": iid, "operation": op, "read_or_write": "read" if read else "write", "implemented": implemented, "configured": configured, "connected": connected,
           "runtime_available": implemented and configured and connected, "risk_class": (w or {}).get("risk_class", "R0"), "gev_approval_required": bool(w), "authority_required": (w or {}).get("authority_required", "READ"),
           "idempotency_method": (w or {}).get("idempotency_method", "n/a (read)"), "verification_method": (w or {}).get("verification_method", "n/a (read)"), "machine_dependency": spec.get("machine_dependency"),
           "system": spec.get("system"), "unblock": spec.get("unblock"), "note": (w or {}).get("note"), "category": (w or {}).get("category", "READ" if read else "SAFE_WRITE" if (w or {}).get("risk_class") == "R1" else "MATERIAL_WRITE"),
           "retry_safe_when_absent": (w or {}).get("retry_safe_when_absent", False), "last_verified_at": (wc or {}).get("verified_at") if w else (rc.get("health") or {}).get("last_success")}
    row["deferred"] = bool(spec.get("deferred"))
    if spec.get("deferred"): row["level"] = "DEFERRED"; row["note"] = spec["deferred"].get("note")
    elif not implemented: row["level"] = "UNAVAILABLE" if (w and not w.get("adapter")) else "DECLARED"
    elif not configured: row["level"] = "IMPLEMENTED"
    elif not connected: row["level"] = "CONFIGURED"
    elif w: row["level"] = "VERIFIED_WRITE" if wc else "CONNECTED"
    else: row["level"] = "VERIFIED_READ" if rc.get("state") in ("VERIFIED_READ", "RELIABLE_READ") else "CONNECTED"
    row["certification_status"] = row["level"]
    return row

def table():
    rows = []
    for iid, spec in registry.INTEGRATIONS.items():
        for op in sorted(spec.get("read_ops") or {}): rows.append(capability(iid, op))
        for op in WRITE_OPS.get(iid, {}): rows.append(capability(iid, op))
    return rows

if __name__ == "__main__":
    for r in table(): print(f"{r['integration_id']:12} {r['operation']:22} {r['read_or_write']:5} {r['level']:15} risk={r['risk_class']} approval={'yes' if r['gev_approval_required'] else 'no'}" + (f"  [{r['note']}]" if r.get("note") else ""))
