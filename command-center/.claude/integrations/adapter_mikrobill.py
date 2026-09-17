# -*- coding: utf-8 -*-
"""ADAPTER INT-MB — MikroBill billing. DECLARED only: no interface (API/DB) has been inventoried, no field or status semantics
are mapped, so every query fails closed with NOT_CONFIGURED and the exact requirement. Nothing here guesses table names,
endpoints or the meaning of the 8 subscriber statuses (U08 stays UNKNOWN until authoritative system metadata is obtained)."""
import sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from contracts import IntegrationError
import registry

OPS = ()
KNOWN_FROM_MODEL = {"system": "SYS-MB", "data_expected": ["subscriber accounts & 8 statuses (pending confirmation, U08)", "tariffs", "payments", "overdue/days", "CPE bindings"],
                    "authority": "source of truth for billing facts (S11)", "owner_role": "Բիլինգի և եկամտի ղեկավար (4.1)", "deputy_access": "NONE (Open-questions #7, U04)"}

def read(op, params=None, cfg=None):
    raise IntegrationError("NOT_CONFIGURED", "MikroBill interface not inventoried — " + (registry.get("INT-MB") or {}).get("unblock", ""))

def inventory(cfg=None):
    """What is KNOWN (from the business model) vs UNKNOWN (must come from the system itself)."""
    return {"known_from_business_model": KNOWN_FROM_MODEL, "interface": "UNKNOWN", "fields_verified": [], "statuses_verified": [],
            "requirement": (registry.get("INT-MB") or {}).get("unblock")}
