# -*- coding: utf-8 -*-
"""SOURCE INVENTORY — every business fact in the model cites one of these ids. Authority ranks decide precedence:
REFERENCE_APPROVED > ACTIVE_DRAFT/PROPOSAL/REGISTER > EVIDENCE (raw) > HISTORICAL. Two CURRENT sources that disagree = CONFLICT
(recorded in bm_company.CONFLICTS, never silently resolved). HISTORICAL never overrides CURRENT."""

# EXTRACTION INVARIANTS — a fingerprint alone never proves extraction. For every CURRENT decision-relevant source the builder
# verifies (a) the document still contains the primitives the model was extracted from and (b) the model still carries the
# ids that source supports. Any failure = EXTRACTION_MISMATCH → build/certification fail.
#   docx_headings ⊇ / docx_text_contains / xlsx_sheets ⊇ / xlsx_min_rows / md_regex_min / text_contains / min_size ·  model_has (ids)
EXTRACTION_INVARIANTS = {
 "S01": {"xlsx_sheets": ["Ամփոփ պատկեր", "Կառուցվածք և աշխատավարձ", "Մոդելներ և պարտադիր վճարներ", "KPI"], "model_has": ["K-NEW", "K-D2D-PKG", "TG-D2D-PKG", "TG-BONUS-TIERS", "P-MGMT-03", "OW-DEC-STAFF"], "role_kpi_weights_match": True},
 "S02": {"docx_headings": ["Վաճառքի ղեկավար", "Բիլինգի և եկամտի ղեկավար (+Համադրում/Աուդիտ)", "L & R մասնագետ", "NOC, Մոնիտորինգի և Backup մասնագետ"], "docx_text_contains": ["Ծածկագիր", "Էսկալացնում է", "Որոշում է ինքնուրույն"], "model_has": ["P-OPS-01", "P-OPS-02", "P-OPS-03", "P-CS-01", "P-CS-02", "P-BILL-01", "P-RET-01", "OW-ESC-TECH", "TG-SLA-INCIDENT-CLASSIFY"], "jd_cards_match_roles": True},
 "S03": {"docx_text_contains": ["ՎԱՃԱՌՔԻ ԿԱՐՃԱԺԱՄԿԵՏ", "ԿԱՆԳՆԵՑՄԱՆ ԿԱՆՈՆՆԵՐ", "Արմավիր", "D2D"], "model_has": ["P-SALES-02", "P-SALES-03", "P-MGMT-02", "TG-NEW-BASELINE", "TG-NEW-PHASE1", "TG-TELE-PKG", "TG-PENETRATION", "TG-DISCOUNT-FLOOR", "K-PENETRATION"]},
 "S04": {"docx_text_contains": ["Roadmap", "Reporting cadence", "KPI Dictionary", "Revenue leakage", "Promise-to-pay"], "model_has": ["P-BILL-03", "P-BILL-04", "P-BILL-06", "K-LEAK", "K-OVERDUE", "K-RECOVERY", "RT-BILLING", "C01"]},
 "S05": {"xlsx_sheets": ["Provenance", "Save list"], "xlsx_min_rows": {"Save list": 10}, "model_has": ["K-CHURN-RISK", "P-RET-01"]},
 "S06": {"min_size": 20000, "model_has": ["K-CHURN-RISK"]},
 "S07": {"text_contains": ["WhatsApp Chat Export", "Revenue Assurance", "Roadmap"], "md_regex_min": {"\\[\\d{1,2}:\\d{2} (AM|PM)\\]": 100}, "model_has": ["C02", "C03", "U01", "U02", "OW-DEC-STRATEGY", "OW-DEC-STAFF"]},
 "S08": {"text_contains": ["WhatsApp Chat Export", "churn"], "md_regex_min": {"\\[\\d{1,2}:\\d{2} (AM|PM)\\]": 20}, "model_has": ["C02", "C03", "P-RET-01"]},
 "S09": {"xlsx_sheets": ["ԱՌԱՋԱԴՐԱՆՔՆԵՐ"], "xlsx_min_rows": {"ԱՌԱՋԱԴՐԱՆՔՆԵՐ": 20}, "model_has": ["K-TASK-OVERDUE", "P-MGMT-01", "OW-KPI-TASKS"]},
 "S10": {"md_regex_min": {"^\\*\\*\\d+\\.\\*\\*": 20}, "model_has": ["U03", "U04", "U05"]},
 "S11": {"xlsx_sheets": ["Գրաֆիկ"], "text_contains_any_of_paths": [], "model_has": ["OW-PRJ-RA", "OW-PRJ-RECON", "C01"]},
 "S14": {"text_contains": ["## Բաց", "Bitrix24"], "model_has": ["GAP-17", "U09"]},
 "S15": {"text_contains": ["DEPUTY", "DAILY BRIEF", "MANAGEMENT RHYTHM", "AUTHORITY BOUNDARY"], "md_regex_min": {"^# ": 40}, "model_has": ["RT-DAILY", "RT-WEEKLY", "RT-MONTHLY", "P-MGMT-01", "OW-KPI-TASKS"]},
 "S16": {"text_contains": ["INT-TASKS", "INT-OL-CAL", "INT-OL-MAIL", "INT-B24", "INT-MB", "FACT_AUTHORITY", "\"write_ops\": []"], "model_has": ["U04", "U09"]},
}

AUTHORITY_RANK = {"REFERENCE_APPROVED": 5, "CHARTER": 5, "ACTIVE_REGISTER": 4, "ACTIVE_DRAFT": 3, "PROPOSAL": 3, "EVIDENCE": 2, "HISTORICAL": 1}

# SOURCE KIND — how a source binds the certified model (explicit semantics, one provenance system):
#   EXTRACTED      (default)  the model's facts were extracted from the document's CONTENT → fingerprint_scope CONTENT: any byte
#                             change = SOURCE_CHANGED → STALE_MODEL → rebuild + certification (product/model path).
#   LIVE_REGISTER             a LIVE OPERATIONAL SOURCE (task register): its rows are live business state, read at query time
#                             through the declared live integration (INT-*, with retrieved_at/freshness/authority per read) and
#                             NEVER extracted into the model. The model depends only on its STRUCTURE (sheet + header block) →
#                             fingerprint_scope STRUCTURE: row create/update/assign/close/reopen/note never changes the core
#                             fingerprint or invalidates certification; a sheet/header (schema) change still does.
SOURCE_KINDS = ("EXTRACTED", "LIVE_REGISTER")
FINGERPRINT_SCOPES = ("CONTENT", "STRUCTURE")
def kind(s): return s.get("source_kind", "EXTRACTED")
def scope(s): return s.get("fingerprint_scope", "CONTENT")

SOURCES = [
 {"source_id": "S01", "path": "02_Reference/People/Staffing-plan-2026-09-07.xlsx", "title": "Հաստիքացուցակ v2 — կառուցվածք, աշխատավարձ, վճարման մոդելներ, KPI (4 sheets)",
  "domain": "PEOPLE", "status": "APPROVED", "effective_date": "UNKNOWN (Oct 1 2026 proposed, unconfirmed — Open-questions #9)", "date": "2026-09-07",
  "owner": "Gev (author) · approved by @P1 2026-09-07 (evidence EV-09)", "source_type": "xlsx", "authority": "REFERENCE_APPROVED", "currency": "CURRENT",
  "conflicts": ["C05", "C08", "C09"], "notes": "Baseline for JD and everything else. 52 positions (25 filled, 27 vacant, 13 critical) + 2 ԱՁ + 3 execs = 57. Subtotal rows interleaved — never sum blindly."},
 {"source_id": "S02", "path": "01_Active/People/Job-descriptions-v1.1-2026-09-05.docx", "title": "Հաստիքների նկարագրություններ և որակավորման պահանջներ v1.1 (29 քարտ, 4 բաժին)",
  "domain": "PEOPLE", "status": "DRAFT_FINAL — awaiting each head's OK (due 2026-09-11)", "effective_date": "UNKNOWN (unsigned)", "date": "2026-09-05",
  "owner": "Gev (Տիրապետող՝ Վաճառքի և գործառնական ղեկավար); approver Գործադիր տնօրեն", "source_type": "docx", "authority": "ACTIVE_DRAFT", "currency": "CURRENT",
  "conflicts": ["C09", "C10"], "notes": "Aligned with S01 (29 titles identical, verified 2026-09-09). Deliberately excludes numeric KPI targets/weights."},
 {"source_id": "S03", "path": "01_Active/Sales/Sales-strategy-2026-09-09.docx", "title": "Վաճառքի կարճաժամկետ ռազմավարություն · Փուլ 1 — D2D և հեռավաճառք (Արմավիր, Մեծամոր, Էջմիածին)",
  "domain": "SALES", "status": "PROPOSAL — presented 2026-09-08; @P1 requires telesales + corporate sections; decision meeting Thu 2026-09-10", "effective_date": "NOT_APPROVED", "date": "2026-09-09",
  "owner": "Gev (+@P3 expected)", "source_type": "docx", "authority": "PROPOSAL", "currency": "CURRENT",
  "conflicts": ["C05"], "notes": "Numbers are proposal assumptions (7,000 AMD package, 18,000 connection cost, 70 activations/month, break-even month 5), not approved targets. No corporate section."},
 {"source_id": "S04", "path": "01_Active/Systems/Billing-roadmap-v2-2026-09-07.docx", "title": "HouseNet Billing Department — Տարեկան Roadmap 2026 (v2, document dated 17 March 2026)",
  "domain": "SYSTEMS/BILLING", "status": "ACTIVE — accepted as basis with 2 amendments by Gev (2026-09-09); @P1's acceptance of amendments not recorded", "effective_date": "UNKNOWN", "date": "2026-09-07",
  "owner": "Billing Head (roadmap owner); sent by @P1", "source_type": "docx", "authority": "ACTIVE_DRAFT", "currency": "CURRENT",
  "conflicts": ["C01", "C08"], "notes": "Defines reporting cadence, KPI dictionary (no targets), Bitrix24 workflows (planned Q1–Q2), prediction streams."},
 {"source_id": "S05", "path": "01_Active/Sales/Churn-save-list-2026-09-09.xlsx", "title": "Churn save list — 30 բաժանորդ, rule-based score (uncalibrated)",
  "domain": "SALES/RETENTION", "status": "WORKING DATA — to be worked by @P5 + @P2 from Mon 2026-09-14", "effective_date": "2026-09-09 (scored on)", "date": "2026-09-09",
  "owner": "@P1 (producer)", "source_type": "xlsx", "authority": "EVIDENCE", "currency": "CURRENT",
  "conflicts": [], "notes": "Criteria: score ≥70, hot signals ≥3, coverage ≥60%, limit 50. Contains subscriber PII (RESTRICTED) — payload never enters the model; aggregates only in overlay EV-01."},
 {"source_id": "S06", "path": "04_Sources/Screenshots/Churn-risk-signals-2026-09-09.jpeg", "title": "Churn risk — 12 rule signals with published weights (of 100)",
  "domain": "SALES/RETENTION", "status": "EVIDENCE (@P1's team model)", "effective_date": "2026-09-09", "date": "2026-09-09",
  "owner": "@P1's team", "source_type": "image", "authority": "EVIDENCE", "currency": "CURRENT",
  "conflicts": [], "notes": "Gev proposed additions: complaint calls/month; separate treatment for yearly-agreement subscribers (not yet in model)."},
 {"source_id": "S07", "path": "04_Sources/Whatsapp/Principal-2026-09-09/chat.md", "title": "WhatsApp @P1 ↔ Gev, 2026-09-05 … 09-09 11:29",
  "domain": "MANAGEMENT", "status": "RAW EVIDENCE", "effective_date": "n/a", "date": "2026-09-09",
  "owner": "@P1 / Gev", "source_type": "chat export", "authority": "EVIDENCE", "currency": "CURRENT",
  "conflicts": ["C02", "C03"], "notes": "Voice messages and images are missing from the export (Revenue Assurance 09-07 20:14/20:16; churn signals 09-09 12:51/12:52)."},
 {"source_id": "S08", "path": "04_Sources/Whatsapp/Principal-2026-09-09-afternoon/chat.md", "title": "WhatsApp @P1 ↔ Gev, 2026-09-09 00:39 … 13:10",
  "domain": "MANAGEMENT", "status": "RAW EVIDENCE", "effective_date": "n/a", "date": "2026-09-09",
  "owner": "@P1 / Gev", "source_type": "chat export", "authority": "EVIDENCE", "currency": "CURRENT", "conflicts": ["C02", "C03"], "notes": "Retention flow, churn lists, save-list handoff."},
 {"source_id": "S09", "path": "Tasks.xlsx", "title": "Առաջադրանքներ — LIVE task register (hand-edited by Gev; Action Runtime writes only with Gev's approval)",
  "domain": "MANAGEMENT", "status": "LIVE REGISTER", "effective_date": "n/a", "date": "2026-09-09",
  "owner": "Gev", "source_type": "xlsx", "authority": "ACTIVE_REGISTER", "currency": "CURRENT", "conflicts": [],
  "source_kind": "LIVE_REGISTER", "fingerprint_scope": "STRUCTURE", "structure": {"sheet": "ԱՌԱՋԱԴՐԱՆՔՆԵՐ", "header_rows": 12}, "live_integration": "INT-TASKS",
  "notes": "LIVE OPERATIONAL SOURCE: owners, deadlines and statuses are read live through INT-TASKS (retrieved_at/freshness per read) — never a static extract. The certified model binds only its STRUCTURE (sheet + header block); row edits are live data (skill.py sync), a schema change is a model change (release)."},
 {"source_id": "S10", "path": "01_Active/Operations/Open-questions.md", "title": "ՀԱՐՑԵՐ — 25 open questions to Gev (people roles, systems access, dates)",
  "domain": "MANAGEMENT", "status": "OPEN — 2 of 25 answered", "effective_date": "n/a", "date": "2026-09-10",
  "owner": "Deputy → Gev", "source_type": "md", "authority": "ACTIVE_REGISTER", "currency": "CURRENT", "conflicts": [], "notes": "Answered: #3 (churn voice = signal list request), #5 (keep Gev's system)."},
 {"source_id": "S11", "path": "03_Completed/Delivery-schedule-2026-09-09.xlsx", "title": "Գրաֆիկ — what Gev delivers when (sent to @P1 2026-09-09) + Gev's two billing positions",
  "domain": "MANAGEMENT", "status": "SENT — commitments snapshot", "effective_date": "2026-09-09", "date": "2026-09-09",
  "owner": "Gev", "source_type": "xlsx/txt", "authority": "ACTIVE_REGISTER", "currency": "CURRENT", "conflicts": ["C01"], "notes": "Also 03_Completed/Delivery-schedule-whatsapp-2026-09-09.txt (the sent text)."},
 {"source_id": "S12", "path": "05_Archive/Drafts-2026-09-09/Principal-requirements-2026-09-09.md", "title": "@P1-ի պահանջները — 44 asks in his words (09-05…09-09) + annotated xlsx",
  "domain": "MANAGEMENT", "status": "SUPERSEDED by Tasks.xlsx", "effective_date": "n/a", "date": "2026-09-09",
  "owner": "Deputy", "source_type": "md/xlsx", "authority": "HISTORICAL", "currency": "HISTORICAL", "conflicts": [], "notes": "History only; verbatim quotes remain useful as evidence."},
 {"source_id": "S13", "path": "05_Archive/Drafts-2026-09-09/Task-workbook-8-sheet-2026-09-09.xlsx", "title": "Old 8-sheet task workbook (+Schedule-questions, Whatsapp-readme)",
  "domain": "MANAGEMENT", "status": "SUPERSEDED", "effective_date": "n/a", "date": "2026-09-09",
  "owner": "Deputy", "source_type": "xlsx/md", "authority": "HISTORICAL", "currency": "HISTORICAL", "conflicts": [], "notes": "Never used for current truth."},
 {"source_id": "S14", "path": "Actions.md", "title": "ԱՆԵԼԻՔՆԵՐ — Deputy's internal to-dos on documents/system",
  "domain": "MANAGEMENT", "status": "LIVE", "effective_date": "n/a", "date": "2026-09-10",
  "owner": "Deputy", "source_type": "md", "authority": "ACTIVE_REGISTER", "currency": "CURRENT", "conflicts": [], "notes": "Open: JD+staffing single doc, ԱՁ JDs, corporate section, KPI sheet completeness, manager chain, Bitrix24 tasks not in register."},
 {"source_id": "S15", "path": ".claude/docs/Job-description.md", "title": "Deputy — Job Description & Operating Charter (53 sections): how Gev wants information, rhythm, authority",
  "domain": "MANAGEMENT", "status": "APPROVED 2026-09-10", "effective_date": "2026-09-10", "date": "2026-09-10",
  "owner": "Gev", "source_type": "md", "authority": "CHARTER", "currency": "CURRENT", "conflicts": [], "notes": "Executive output format, P1–P4 prioritization, daily/weekly/monthly rhythm, interruption rules."},
 {"source_id": "S16", "path": ".claude/integrations/registry.py", "title": "Deputy Integration Registry — declared live sources (READ-ONLY), authority per fact type, certification states",
  "domain": "MANAGEMENT", "status": "ACTIVE — Mission 4 (2026-09-11)", "effective_date": "2026-09-11", "date": "2026-09-11",
  "owner": "Gev / Deputy", "source_type": "py", "authority": "ACTIVE_REGISTER", "currency": "CURRENT", "conflicts": [], "notes": "Which systems Deputy can read and how much each is trusted (FACT_AUTHORITY tiers). A registry entry is a declaration; only certify_integrations.py evidence (certification.json, local) makes a source CONNECTED/VERIFIED_READ."},
]
