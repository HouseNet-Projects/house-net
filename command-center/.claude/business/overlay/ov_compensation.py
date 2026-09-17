# -*- coding: utf-8 -*-
"""SENSITIVE OVERLAY — COMPENSATION (CONFIDENTIAL, local only). Net monthly fixed salary per role code (S01 approved staffing
plan) and payroll aggregates. Core roles carry NO compensation; the runtime merges this at request time when authorized."""
OVERLAY_DATA = True

FIX_SALARY_NET_AMD = {
 "1.1": 350000, "1.2": 150000, "1.3": 120000, "1.4": 150000, "1.5": 100000, "1.6": 70000, "1.7": 150000, "1.8": 150000, "1.9": 150000,
 "2.1": 200000, "2.2": 150000, "2.3": 200000, "2.4": 170000, "2.5": 150000, "2.6": 250000, "2.7": 220000, "2.8": 200000, "2.9": 200000, "2.10": 180000,
 "2.11": 150000, "2.12": 150000, "2.13": 180000, "2.14": 200000, "3.1": 300000, "3.2": 150000, "3.3": 150000, "3.4": 120000, "4.1": 300000, "4.2": 150000,
 "CTR-REC": 100000, "CTR-LAW": 50000,
}
PAYROLL_AMD = {"fixed_net": 8310000, "fixed_with_taxes": 11464133, "base_scenario_100_119_with_taxes": 15695333, "filled_only_today_with_taxes": 6372000,
               "critical_vacancies_cost_with_taxes": 1807200, "floor_monthly_lt80": 11268933, "ceiling_monthly_ge120": 17392133, "annual_base": 188344000,
               "bonus_fund_base": 4231200, "bonus_fund_max": 5928000}
PAY_MODEL_PARAMS = {"model_B_avg_package_amd": 8000, "model_B_fix_amd": 70000, "tax_income_pct": 20, "tax_social_pct": 5, "net_to_gross_factor": 1.3333}
SRC = ["S01"]
