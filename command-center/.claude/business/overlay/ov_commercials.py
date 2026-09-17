# -*- coding: utf-8 -*-
"""SENSITIVE OVERLAY — COMMERCIAL FIGURES (CONFIDENTIAL, local only). Cost, investment, margin and revenue projections from the
sales strategy proposal (S03) and cost items from the staffing plan (S01). Core keeps only counts/targets (INTERNAL) and
customer-facing prices (PUBLIC)."""
OVERLAY_DATA = True

COMMERCIALS = [
 {"id": "CV-01", "item": "Phase-1 monthly total cost (salaries + connection investment)", "value": 2186667, "unit": "AMD/month", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-02", "item": "Phase-1 monthly salary cost at target (with taxes, incl. D2D commission)", "value": 926667, "unit": "AMD/month", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-03", "item": "Phase-1 salary floor below plan (no D2D fix)", "value": 494533, "unit": "AMD/month", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-04", "item": "Connection cost per subscriber (equipment, installation, materials)", "value": 18000, "unit": "AMD", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-05", "item": "Customer acquisition cost per subscriber (connection + salary share)", "value": 31238, "unit": "AMD", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-06", "item": "Payback per subscriber", "value": 4.5, "unit": "months at 7,000 AMD", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-07", "item": "Phase-1 new MRR at target (70 × 7,000)", "value": 490000, "unit": "AMD/month", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-08", "item": "Branch baseline MRR (55 × 7,000)", "value": 385000, "unit": "AMD/month", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-09", "item": "Maximum cumulative exposure (end of month 4)", "value": 3846667, "unit": "AMD", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-10", "item": "Monthly positive cash from month 5; cumulative zero in month 8 (zero churn, no discount)", "value": {"positive_from_month": 5, "cumulative_zero_month": 8, "monthly_positive_amd": 263333}, "unit": "months/AMD", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-11", "item": "Baseline 55 connections require 990,000 AMD/month investment from the existing budget", "value": 990000, "unit": "AMD/month", "src": ["S03"], "status": "PROPOSED"},
 {"id": "CV-12", "item": "Critical vacancies cost if filled (fix with taxes)", "value": 1807200, "unit": "AMD/month", "src": ["S01"], "status": "APPROVED"},
]
