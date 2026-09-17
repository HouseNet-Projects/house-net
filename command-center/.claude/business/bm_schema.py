# -*- coding: utf-8 -*-
"""BUSINESS MODEL SCHEMA — versioned contract for the CORE (versionable, INTERNAL) and the SENSITIVE OVERLAY (local, CONFIDENTIAL).
The runtime (skills/business.py) rejects a model whose schema_version is not in COMPATIBLE. Bump MODEL_VERSION on every
change of encoded business facts; bump SCHEMA_VERSION only when the shape changes."""
SCHEMA_VERSION = "2.0"            # 1.x = Mission 3 mixed model (no longer accepted); 2.x = core/overlay split
COMPATIBLE = ("2.0",)
MODEL_VERSION = "2026-09-12.1"    # date.sequence of the encoded business facts (2026-09-12.1: S09 = LIVE_REGISTER, STRUCTURE-scoped)
PERSON_TOKEN = r"@P\d+"           # core may reference people only through these tokens; the overlay maps token → name

CORE_FILES = ("sources", "business_model", "processes", "ownership", "kpis", "targets", "playbooks", "routines", "gaps")
OVERLAY_FILE = "overlay"
META_KEYS = ("model_version", "schema_version", "generated_at", "source_snapshot_id", "core_fingerprint", "overlay_fingerprint", "business_effective_date", "layer")

REQUIRED = {
 "sources": {"sources": list, "authority_rank": dict},
 "business_model": {"company": dict, "functions": list, "roles": list, "principals": list, "systems": list, "sales": dict, "operations": dict, "people_model": dict, "conflicts": list, "critical_unknowns": list},
 "processes": {"processes": list, "flow_vocabulary": list},
 "ownership": {"ownership": list, "statuses": list},
 "kpis": {"kpis": list, "role_kpis": dict, "kinds": list},
 "targets": {"targets": list, "promotion_states": list, "promotion_rules": dict},
 "playbooks": {"playbooks": list, "flow": list, "executive_format": str},
 "routines": {"routines": list},
 "gaps": {"gaps": list, "gap_codes": list},
}
OVERLAY_REQUIRED = {"persons": list, "assignments": list, "compensation": dict, "commercials": list, "evidence": list, "source_payloads": dict}
ROLE_FORBIDDEN_KEYS = ("fix_salary_net_amd", "salary", "person", "name")          # never in core roles
CONF = ("CONFIRMED", "DERIVED", "UNVERIFIED", "UNKNOWN")

def check_shape(name, obj):
    """Structural validation → list of problems."""
    p = []
    req = REQUIRED.get(name) if name != OVERLAY_FILE else OVERLAY_REQUIRED
    if req is None: return [f"{name}: unknown model file"]
    meta = obj.get("meta") or {}
    for k in META_KEYS:
        if k not in meta: p.append(f"{name}: meta.{k} missing")
    if meta.get("schema_version") not in COMPATIBLE: p.append(f"{name}: schema_version {meta.get('schema_version')!r} not compatible with {COMPATIBLE}")
    for k, t in req.items():
        if k not in obj: p.append(f"{name}: key {k} missing")
        elif not isinstance(obj[k], t): p.append(f"{name}: key {k} must be {t.__name__}")
    if name == "business_model":
        for r in obj.get("roles", []):
            for fk in ROLE_FORBIDDEN_KEYS:
                if fk in r: p.append(f"business_model: role {r.get('code')} carries forbidden key {fk} (belongs to the overlay)")
    return p
