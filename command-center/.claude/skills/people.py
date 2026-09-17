# -*- coding: utf-8 -*-
"""PEOPLE / OWNERSHIP RESOLVER — one person, many identities: person ↔ role (Business Operating Model, overlay assignments) ↔ e-mail
(Outlook) ↔ Bitrix user ↔ Telegram user ↔ WhatsApp number. Reuses the existing Store (table `identities`, LOCAL only — never
versioned) and the existing business overlay (persons @P<n>, role assignments with confidence). Rules:
  · one external id is NEVER silently attached to two people → CONFLICT / NEEDS CONFIRMATION
  · an ambiguous name is UNKNOWN with candidates, never a guess · role ≠ person (a role can be vacant or unconfirmed)
  · every link carries source · external id · person · verification method · status · confirmed_at · confidence
  · only Gev confirms a link (method GEV_CONFIRMED); observed/derived links stay CANDIDATE and never resolve authority."""
import re, hashlib, datetime, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import business

CHANNELS = ("INT-OL-MAIL", "INT-B24", "INT-TG", "INT-WA")
METHODS = ("GEV_CONFIRMED", "DIRECTORY", "OBSERVED")
STATUSES = ("CONFIRMED", "CANDIDATE", "CONFLICT", "REJECTED")
DIVISION_BY_PREFIX = {"1": "Sales (FN-COM)", "2": "Operations / Technical", "3": "Customer service", "4": "Billing & revenue", "EXEC": "Executive"}

def _st():
    import engine; return engine._store()
def _now(): return datetime.datetime.now().isoformat(timespec="seconds")
def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())
def _digits(v): return re.sub(r"\D", "", str(v or ""))
def _ext_norm(channel, ext):
    e = str(ext or "").strip()
    if channel == "INT-OL-MAIL": return e.lower()
    if channel == "INT-WA": return _digits(e)
    return e.lstrip("@")

def link_id(channel, external_id): return "ID-" + hashlib.sha256(f"{channel}|{_ext_norm(channel, external_id)}".encode("utf-8")).hexdigest()[:12]

def persons():
    """People known to the business model overlay (tokens → names/aliases) with their role assignments and confidence. Empty when the overlay is absent."""
    m = business.load(); ov = (m or {}).get("_overlay") or {}
    out = []
    for p in ov.get("persons", []):
        roles = [{"role": a["role"], "conf": a["conf"], "src": a.get("src", []), "note": a.get("note")} for a in ov.get("assignments", []) if a["person"] == p["id"]]
        out.append({"token": p["id"], "name": p["name"], "aliases": list(p.get("aliases", [])), "roles": roles, "note": p.get("note")})
    return out

def _role_title(code):
    m = business.load() or {}
    for r in (m.get("business_model") or {}).get("roles", []):
        if r.get("code") == code: return r.get("title")
    return None

def department_for(code):
    if not code: return "UNKNOWN"
    return DIVISION_BY_PREFIX.get(code.split(".")[0], DIVISION_BY_PREFIX.get(code.split("-")[0], "UNKNOWN"))

def links(channel=None):
    rows = _st().list("identities")
    return [r for r in rows if not channel or r.get("channel") == channel]

def find_person(text):
    """Name/alias/token → persons mentioned. Exact word match on name or alias; nothing fuzzy."""
    t = _norm(text); hits = []
    for p in persons():
        names = [p["name"]] + p["aliases"] + [p["token"]]
        if any(re.search(r"(?:^|[^\w])" + re.escape(_norm(n)) + r"(?:$|[^\w])", t) for n in names if n): hits.append(p)
    return hits

def link(person_token, channel, external_id, *, display=None, method="OBSERVED", confirmed_by=None, confidence=None, source=None):
    """Create/refresh an identity link. GEV_CONFIRMED (confirmed_by='Gev') → CONFIRMED; otherwise CANDIDATE.
    A CONFIRMED link of the same external id to ANOTHER person is never overwritten: the new link is stored as CONFLICT and needs Gev."""
    if channel not in CHANNELS: raise ValueError(f"unknown channel {channel}")
    if method not in METHODS: raise ValueError(f"unknown method {method}")
    st = _st(); lid = link_id(channel, external_id); ext = _ext_norm(channel, external_id)
    existing = st.get("identities", lid)
    status = "CONFIRMED" if (method == "GEV_CONFIRMED" and confirmed_by == "Gev") else "CANDIDATE"
    if existing and existing.get("status") == "CONFIRMED" and existing.get("person") != person_token:
        if status == "CONFIRMED":                       # Gev explicitly re-assigns: previous link is superseded, kept in history
            rec = {**existing, "history": (existing.get("history") or []) + [{k: existing.get(k) for k in ("person", "status", "method", "confirmed_at")}]}
        else:
            rec = {**existing, "conflict": {"person": person_token, "method": method, "display": display, "source": source, "at": _now(), "note": "another person claims this external id — Gev must confirm"}, "status": "CONFLICT"}
            st.upsert("identities", lid, rec); return {"status": "NEEDS_CONFIRMATION", "link": rec, "reason": f"{channel} id is already CONFIRMED for {existing.get('person')}"}
    elif existing and existing.get("status") == "CONFIRMED" and existing.get("person") == person_token and status != "CONFIRMED":
        rec = dict(existing); rec.update({"last_seen": _now(), "external_display": display or rec.get("external_display")}); st.upsert("identities", lid, rec); return {"status": "LINKED", "link": rec, "note": "already CONFIRMED by Gev — an observation never downgrades a confirmed link"}
    else: rec = dict(existing or {})
    rec.update({"op_id": lid, "channel": channel, "external_id": ext, "external_display": display or ext, "person": person_token, "method": method, "status": status, "source": source,
                "confidence": confidence if confidence is not None else (1.0 if status == "CONFIRMED" else 0.5), "confirmed_by": confirmed_by if status == "CONFIRMED" else None,
                "confirmed_at": _now() if status == "CONFIRMED" else rec.get("confirmed_at"), "updated_at": _now()})
    rec.pop("conflict", None) if status == "CONFIRMED" else None
    st.upsert("identities", lid, rec)
    return {"status": "LINKED" if status == "CONFIRMED" else "CANDIDATE", "link": rec}

def reject(channel, external_id, by="Gev"):
    st = _st(); lid = link_id(channel, external_id); ex = st.get("identities", lid)
    if not ex: return {"status": "NOT_FOUND"}
    ex.update({"status": "REJECTED", "rejected_by": by, "updated_at": _now()}); st.upsert("identities", lid, ex); return {"status": "REJECTED", "link": ex}

def resolve_external(channel, external_id, display=None):
    """External id → person. CONFIRMED link → PERSON_KNOWN; CANDIDATE/CONFLICT → NEEDS_CONFIRMATION; nothing → UNKNOWN (display name may suggest candidates, never resolve)."""
    lid = link_id(channel, external_id); ex = _st().get("identities", lid); names = {p["token"]: p["name"] for p in persons()}
    if ex and ex.get("status") == "CONFIRMED":
        return {"status": "PERSON_KNOWN", "person": ex["person"], "name": names.get(ex["person"], ex["person"]), "confidence": ex.get("confidence"), "method": ex.get("method"), "confirmed_at": ex.get("confirmed_at"), "link_id": lid}
    if ex and ex.get("status") in ("CANDIDATE", "CONFLICT"):
        cands = [{"person": ex["person"], "name": names.get(ex["person"], ex["person"]), "confidence": ex.get("confidence"), "method": ex.get("method")}]
        if ex.get("conflict"): cands.append({"person": ex["conflict"]["person"], "name": names.get(ex["conflict"]["person"]), "confidence": None, "method": ex["conflict"].get("method")})
        return {"status": "NEEDS_CONFIRMATION", "person": None, "candidates": cands, "reason": "link not confirmed by Gev" if ex["status"] == "CANDIDATE" else "two people claim this id", "link_id": lid}
    cands = [{"person": p["token"], "name": p["name"], "confidence": 0.3, "method": "NAME_MATCH"} for p in find_person(display or "")] if display else []
    return {"status": "UNKNOWN" if not cands else "NEEDS_CONFIRMATION", "person": None, "candidates": cands, "reason": "no identity link for this external id" + (" — display name matches a known person (candidate only)" if cands else ""), "link_id": lid}

def describe_external(channel, external_id, *, username=None, first_name=None, last_name=None, display=None):
    """HUMAN-READABLE presentation of an external sender (workspace_policy.json -> interaction.human_readable_identity).
    Deputy never hands Gev a bare numeric id to decode: it builds a LABEL from the provider evidence and keeps working. A label is
    enough for ordinary read/intelligence/reporting; a missing identity mapping is NOT a blocker and is never turned into a question
    to Gev by itself. This is presentation ONLY — a username or a name is never identity evidence, and the binding itself stays
    fail-closed in resolve_external(); confirmation is asked for only by confirmation_required()."""
    res = resolve_external(channel, external_id, display or first_name or username)
    parts, missing = [], []
    if username: parts.append("@" + str(username).lstrip("@"))
    else: missing.append("username")
    full = " ".join(x for x in (first_name, last_name) if x)
    if full: parts.append(full)
    if not last_name: missing.append("last_name")
    if display and display not in parts: parts.append(f"display name «{display}»")
    known = res.get("name") if res["status"] == "PERSON_KNOWN" else None
    if known: parts.insert(0, known)
    label = (("@" + str(username).lstrip("@")) if username else (full or display or ("id " + str(external_id))))
    return {"channel": channel, "external_id": str(external_id), "identity_status": res["status"], "person": res.get("person"),
            "label": known or label, "confirmation_required": False, "blocker": None,
            "confirmed_name": known, "username": (str(username).lstrip("@") if username else None),
            "first_name": first_name, "last_name": last_name, "display_name": display,
            "missing_fields": missing, "candidates": res.get("candidates", []),
            "human": " · ".join(parts) if parts else f"(մատակարարը մարդկային ոչ մի դաշտ չի տվել, միայն տեխնիկական id {external_id})",
            "reference_id": str(external_id),
            "note": ("հաստատված ինքնություն" if known else
                     "մարդկային պիտակ է, ոչ հաստատված ինքնություն — սովորական աշխատանքի համար բավական է, հաստատում պետք է միայն "
                     "role/ownership/authority/reconciliation/ambiguity գործողությունների դեպքում"),
            "provider_missing_note": ("մատակարարը չի տվել՝ " + ", ".join(missing)) if missing else None}

CONFIRMATION_OPERATIONS = ("ROLE_BINDING", "OWNERSHIP", "AUTHORITY", "CROSS_SYSTEM_RECONCILIATION", "AMBIGUOUS_NAME")

def confirmation_operations():
    """Operations that genuinely depend on a CONFIRMED identity - read from the canonical policy, with a fail-closed fallback."""
    try:
        import json as _json, pathlib as _pl
        pol = _json.loads((_pl.Path(__file__).resolve().parent.parent / "policy" / "workspace_policy.json").read_text(encoding="utf-8"))
        ops = pol["interaction"]["human_readable_identity"]["confirmation_required_only_for"]
        if isinstance(ops, dict) and ops: return tuple(sorted(ops))
    except Exception: pass
    return CONFIRMATION_OPERATIONS

def confirmation_required(operation=None):
    """True only when the OPERATION itself needs a confirmed identity. Presenting, reading, summarising or reporting never does,
    so an unmapped sender is labelled and the work continues instead of stopping on a question to Gev."""
    return str(operation or "").strip().upper() in confirmation_operations()

def describe_chat_record(rec):
    """Same presentation, taken straight from a normalized chat record."""
    return describe_external(rec.get("channel"), rec.get("sender_id"), username=rec.get("sender_username"),
                             first_name=rec.get("sender_first_name"), last_name=rec.get("sender_last_name"),
                             display=rec.get("sender_name"))

def identities_of(person_token):
    return [{k: r.get(k) for k in ("channel", "external_display", "status", "method", "confidence", "confirmed_at")} for r in links() if r.get("person") == person_token]

def card(query):
    """Person card: who, roles (with confidence), department, identities per channel, confidence. Ambiguous or unknown → UNKNOWN / NEEDS CONFIRMATION."""
    hits = find_person(query)
    if not hits: return {"status": "UNKNOWN", "reason": "no person in the business model matches this name — supply the full name or confirm who is meant", "candidates": []}
    if len(hits) > 1: return {"status": "NEEDS_CONFIRMATION", "reason": "several people match", "candidates": [{"person": p["token"], "name": p["name"]} for p in hits]}
    p = hits[0]; confirmed = [r for r in p["roles"] if r["conf"] == "CONFIRMED"]; cand = [r for r in p["roles"] if r["conf"] != "CONFIRMED"]
    dept = department_for(confirmed[0]["role"]) if confirmed else ("UNKNOWN — role assignment not confirmed" + (f" (candidates: {', '.join(r['role'] + '/' + r['conf'] for r in cand)})" if cand else ""))
    return {"status": "PERSON_KNOWN", "person": p["token"], "name": p["name"], "aliases": p["aliases"], "roles_confirmed": [{**r, "title": _role_title(r["role"])} for r in confirmed], "roles_candidate": [{**r, "title": _role_title(r["role"])} for r in cand],
            "department": dept, "identities": identities_of(p["token"]), "confidence": "CONFIRMED" if confirmed else "UNVERIFIED", "note": p.get("note")}

def role_holder(role_code):
    r = business.person_for_role(role_code)
    return {"role": role_code, "title": _role_title(role_code), "department": department_for(role_code), **r}

def conflicts():
    return [r for r in links() if r.get("status") == "CONFLICT"]
