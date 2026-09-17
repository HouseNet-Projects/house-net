# -*- coding: utf-8 -*-
"""CONTROLLED TARGETS & THRESHOLDS (INTERNAL). The only place a numeric target / SLA / approval / discount / authority
threshold may enter the model. Prose never carries targets. status: APPROVED (approved source) · PROPOSED (proposal source,
not approved) · UNKNOWN (placeholder documenting that no source defines it). KPI.target is derived from APPROVED entries."""

def T(tid, kind, ref, value, unit, effective, approver, src, scope, status, review=None, note=None):
    d = {"target_id": tid, "kind": kind, "ref": ref, "value": value, "unit": unit, "effective_date": effective, "approver": approver, "src": list(src), "scope": scope, "status": status, "review_date": review or "UNKNOWN"}
    if note: d["note"] = note
    return d

TARGETS = [
 # ── KPI targets ──
 T("TG-D2D-PKG", "KPI_TARGET", "K-D2D-PKG", 10, "packages/agent/month", "UNKNOWN", "@P1 (staffing plan approval, Model Բ parameter)", ["S01"], "D2D agents", "APPROVED", note="Model Բ plan parameter; also used by the strategy proposal"),
 T("TG-D2D-FIX-THRESHOLD", "AUTHORITY_THRESHOLD", "K-D2D-PKG", 80, "% of plan below which no fixed salary is paid", "UNKNOWN", "@P1 (staffing plan approval)", ["S01"], "D2D agents", "APPROVED"),
 T("TG-BONUS-TIERS", "AUTHORITY_THRESHOLD", "P-MGMT-03", {"<80": 0, "80-89": 15, "90-99": 25, "100-119": 35, ">=120": 50}, "% bonus on fix by weighted KPI attainment", "UNKNOWN", "@P1 (staffing plan approval)", ["S01"], "Model Ա roles", "APPROVED"),
 T("TG-TELE-PKG", "KPI_TARGET", "K-TELE-PKG", 20, "packages/agent/month", "NOT_APPROVED", "pending @P1 green light", ["S03"], "telesales agents (phase 1)", "PROPOSED"),
 T("TG-NEW-BASELINE", "KPI_TARGET", "K-NEW", {"Արմավիր": 19, "Մեծամոր": 18, "Էջմիածին": 18, "total": 55}, "activations/month", "NOT_APPROVED", "pending @P1", ["S03"], "branch baseline", "PROPOSED"),
 T("TG-NEW-PHASE1", "KPI_TARGET", "K-NEW", 70, "activations/month (5 new hires)", "NOT_APPROVED", "pending @P1", ["S03"], "phase-1 hires", "PROPOSED"),
 T("TG-PENETRATION", "KPI_TARGET", "K-PENETRATION", 40, "% sector penetration before opening the next sector", "NOT_APPROVED", "pending @P1", ["S03"], "D2D sectors", "PROPOSED"),
 T("TG-STOP-D2D-M1", "AUTHORITY_THRESHOLD", "K-D2D-PKG", 5, "packages in month 1 below which the contract ends", "NOT_APPROVED", "pending @P1", ["S03"], "new D2D hires", "PROPOSED"),
 T("TG-STOP-TELE-M1", "AUTHORITY_THRESHOLD", "K-TELE-PKG", 10, "packages in month 1 below which the contract ends", "NOT_APPROVED", "pending @P1", ["S03"], "new telesales hires", "PROPOSED"),
 T("TG-STOP-2M", "AUTHORITY_THRESHOLD", "K-NEW", 80, "% of plan — 2 consecutive months below → termination", "NOT_APPROVED", "pending @P1", ["S03"], "new sales hires", "PROPOSED"),
 T("TG-TASK-OVERDUE", "KPI_TARGET", "K-TASK-OVERDUE", 0, "overdue tasks", "2026-09-10", "Gev (charter)", ["S15"], "Tasks.xlsx", "APPROVED"),
 # ── SLAs ──
 T("TG-SLA-INCIDENT-CLASSIFY", "SLA", "P-OPS-03", 5, "minutes alert → classified incident", "UNKNOWN (JD v1.1 unsigned)", "Գործադիր տնօրեն (JD approver)", ["S02"], "NOC", "PROPOSED"),
 T("TG-SLA-LINE-ESCALATION", "SLA", "P-OPS-03", 15, "minutes line-fault alert → escalation", "UNKNOWN (JD v1.1 unsigned)", "Գործադիր տնօրեն (JD approver)", ["S02"], "NOC", "PROPOSED"),
 T("TG-SLA-ACTIVATION-FREEZE", "SLA", "K-ACTIVATION-DAYS", 5, "days activation lead time above which the new-sales plan is frozen", "NOT_APPROVED", "pending @P1", ["S03"], "installation", "PROPOSED"),
 T("TG-SLA-ACTIVATION-PROMISE", "SLA", "K-ACTIVATION-DAYS", 24, "hours connection promise to customers", "NOT_APPROVED", "pending @P1", ["S03"], "sales promise", "PROPOSED"),
 T("TG-SLA-RETENTION-CONTACT", "SLA", "P-RET-01", 1, "day — contact a cancelling subscriber within the day of the request", "UNKNOWN (JD v1.1 unsigned)", "Գործադիր տնօրեն (JD approver)", ["S02"], "L&R", "PROPOSED"),
 T("TG-SLA-SPLICE-LOSS", "SLA", "P-OPS-04", 0.05, "dB maximum average splice loss for line acceptance", "UNKNOWN (JD v1.1 unsigned)", "Գործադիր տնօրեն (JD approver)", ["S02"], "network build", "PROPOSED"),
 T("TG-SLA-INSTALL", "SLA", "P-OPS-01", "UNKNOWN", "days", "UNKNOWN", "UNKNOWN", ["S02"], "installation", "UNKNOWN", note="KPI exists ('Տեղադրման SLA'), value defined nowhere"),
 T("TG-SLA-INHOME", "SLA", "P-OPS-02", "UNKNOWN", "hours/days", "UNKNOWN", "UNKNOWN", ["S02"], "in-home repair", "UNKNOWN"),
 T("TG-SLA-COMPLAINT", "SLA", "P-CS-02", "UNKNOWN", "days", "UNKNOWN", "UNKNOWN", ["S02"], "complaints", "UNKNOWN"),
 T("TG-SLA-LEAD-RESPONSE", "SLA", "P-SALES-04", "UNKNOWN", "minutes/hours", "UNKNOWN", "UNKNOWN", ["S02"], "marketing leads", "UNKNOWN"),
 T("TG-SLA-REACTIVATION", "SLA", "P-BILL-03", "UNKNOWN", "hours", "UNKNOWN", "UNKNOWN", ["S04"], "billing", "UNKNOWN"),
 # ── approval / discount / authority thresholds ──
 T("TG-APPROVAL-DISCOUNT", "APPROVAL_THRESHOLD", "P-BILL-04", "UNKNOWN", "AMD or % by approver level", "UNKNOWN", "UNKNOWN", ["S02", "S04"], "billing exceptions (discount/correction/reactivation/write-off)", "UNKNOWN", note="Approval Matrix referenced by roadmap and JD 4.1 — never defined"),
 T("TG-DISCOUNT-FLOOR", "DISCOUNT_THRESHOLD", "K-ARPU", 7000, "AMD/month price floor — no discounting", "NOT_APPROVED", "pending @P1", ["S03"], "new sales", "PROPOSED"),
 T("TG-AUTHORITY-PRICING", "AUTHORITY_THRESHOLD", "OW-DEC-PRICE", "UNKNOWN", "who may change tariffs", "UNKNOWN", "UNKNOWN", ["S02"], "pricing", "UNKNOWN", note="JD: Sales head escalates to S&O head 'or the authorized management' — final authority undefined"),
 T("TG-AUTHORITY-RETENTION-BENEFITS", "AUTHORITY_THRESHOLD", "OW-DEC-RETBEN", "within the approved benefits list and budget", "list", "UNKNOWN (JD v1.1 unsigned)", "Հաճախորդների սպասարկման ղեկավար approves the list", ["S02"], "retention offers", "PROPOSED", note="the list itself is not in the workspace"),
 T("TG-CHURN-NORM", "KPI_TARGET", "K-CHURN", "UNKNOWN", "%", "UNKNOWN", "UNKNOWN", ["S01"], "L&R KPI 'Churn % նորմայի մեջ'", "UNKNOWN"),
]

PROMOTION_STATES = ["OBSERVATION", "PROPOSED", "CONFIRMED", "APPROVED", "SUPERSEDED"]
# who may move a business fact between states (source authority → maximum state it can create; explicit acts promote further)
PROMOTION_RULES = {
 "max_state_by_authority": {"EVIDENCE": "OBSERVATION", "ACTIVE_REGISTER": "OBSERVATION", "PROPOSAL": "PROPOSED", "ACTIVE_DRAFT": "PROPOSED", "CHARTER": "APPROVED", "REFERENCE_APPROVED": "APPROVED", "HISTORICAL": "SUPERSEDED"},
 "promotions": [
  {"from": "OBSERVATION", "to": "PROPOSED", "by": "Deputy after cross-checking a second current source, or Gev", "note": "a chat message alone stays an OBSERVATION"},
  {"from": "PROPOSED", "to": "CONFIRMED", "by": "Gev's explicit confirmation (recorded with date) or a current ACTIVE document", "note": "confirmation ≠ approval"},
  {"from": "CONFIRMED", "to": "APPROVED", "by": "the approver role of the primitive (staffing → @P1; JD → Գործադիր տնօրեն; strategy → @P1; charter → Gev) or a REFERENCE_APPROVED document", "note": "only APPROVED facts may set targets/thresholds"},
  {"from": "APPROVED", "to": "SUPERSEDED", "by": "a newer APPROVED fact from a source of equal or higher authority", "note": "the old fact stays readable as history"},
  {"from": "*", "to": "SUPERSEDED", "by": "source moved to 05_Archive / marked SUPERSEDED", "note": "history never overrides current"},
 ],
 "forbidden": ["OBSERVATION → APPROVED directly", "any EVIDENCE/chat overriding a REFERENCE_APPROVED fact", "HISTORICAL source promoting anything", "Deputy self-approving a target/threshold"],
}
