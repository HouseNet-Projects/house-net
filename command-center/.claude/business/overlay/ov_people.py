# -*- coding: utf-8 -*-
"""SENSITIVE OVERLAY — PEOPLE (CONFIDENTIAL, local only, never versioned).
Core refers to people only by tokens @P<n>. This file maps tokens → names and records person ↔ role ASSIGNMENTS with
confidence. Only a CONFIRMED assignment lets the runtime resolve OWNER ROLE → CURRENT PERSON; DERIVED/UNVERIFIED stay
"candidate" and the runtime reports PERSON UNKNOWN (never guessed)."""
OVERLAY_DATA = True

PERSONS = [
 {"id": "@P0", "name": "Գև", "aliases": ["Gev", "Gev Ohanyan", "Գև Օհանյան"], "note": "workspace owner — identity is PUBLIC (policy identity); listed for completeness"},
 {"id": "@P1", "name": "Գադուկյան", "aliases": ["Gadukyan"], "note": "approves staffing plan; assigns Gev's tasks; demands strategy; builds churn prediction/CRM product"},
 {"id": "@P2", "name": "Մագա", "aliases": ["Maga", "Мага"], "note": "billing tasks, ՀՎՀՀ corrections, reconciliation, functions list; author of roadmap's initial proposals"},
 {"id": "@P3", "name": "Ռիչ", "aliases": ["Rich", "Ռիչը"], "note": "sales strategy expected from him; retention flow to be closed on him"},
 {"id": "@P4", "name": "Հայկ", "aliases": ["Hayk", "Հայկը"], "note": "development — KPI calculation logic, portal, CRM-resident AI training"},
 {"id": "@P5", "name": "Անահիտ", "aliases": ["Anahit", "Անահիտի"], "note": "retention scripts given to her; save-list with @P2; receives telesales retention reports"},
 {"id": "@P6", "name": "Համո", "aliases": ["Hamo", "Համոյի"], "note": "retention flow 'was closed on' him (past)"},
 {"id": "@P7", "name": "Խչո", "aliases": ["Khcho", "Խչոն"], "note": "mentioned re: activity-drop analysis report"},
 {"id": "@P8", "name": "Խաչիկ", "aliases": ["Khachik", "Խաչիկին"], "note": "informed of Gev's absence"},
]

# role ↔ person assignments. status CONFIRMED = verified mapping usable at runtime; DERIVED/UNVERIFIED = candidate only.
ASSIGNMENTS = [
 {"role": "EXEC-SO", "person": "@P0", "conf": "CONFIRMED", "src": ["S15", "S01"], "verified_by": "policy identity (owner = Gev)", "date": "2026-09-10"},
 {"role": "EXEC-CEO", "person": "@P1", "conf": "UNVERIFIED", "src": ["S07", "S10"], "verified_by": None, "date": "2026-09-10", "note": "approves staffing, assigns tasks — likely CEO/owner; Open-questions #11 unanswered"},
 {"role": "4.1", "person": "@P2", "conf": "DERIVED", "src": ["S04", "S07", "S09"], "verified_by": None, "date": "2026-09-10", "note": "does the billing head's work; title never confirmed"},
 {"role": "1.1", "person": "@P3", "conf": "UNVERIFIED", "src": ["S07", "S08"], "verified_by": None, "date": "2026-09-10", "note": "could be 1.1 or 1.4; Open-questions #13"},
 {"role": "3.1", "person": "@P5", "conf": "UNVERIFIED", "src": ["S08", "S09"], "verified_by": None, "date": "2026-09-10", "note": "retention operations; Open-questions #15"},
 {"role": "DEV", "person": "@P4", "conf": "DERIVED", "src": ["S07"], "verified_by": None, "date": "2026-09-10", "note": "not a staffing-table role"},
]

# operating (non-canonical) person notes referenced by processes/playbooks in the core via tokens
OPERATING_NOTES = {
 "@P2": "Reconciliation is being moved off @P2 (go-live target Fri 2026-09-11); cannot deliver a technical spec (@P1 09-07); overloaded ('big load to free').",
 "@P5": "Works the save list with @P2 from Mon 2026-09-14; Gev proposed telesales senior → @P5 retention reporting.",
}
