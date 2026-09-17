# -*- coding: utf-8 -*-
"""RECONCILIATION — connect facts across systems WITHOUT destroying provenance and WITHOUT creating permanent truth:
  · classify_message  → ACTION · DECISION · DELEGATE · MONITOR · FYI · IGNORE (rule-based, explainable signals)
  · open_loop_candidates → CANDIDATE_OPEN_LOOP from mail, reconciled against tasks / commitments / decisions (conservative linking:
    MATCHED · ENTITY_MATCH_UNCERTAIN · NO_MATCH, duplicates by conversation) — never persisted as a commitment or fact
  · reconcile_fact → FACT_AUTHORITY tiers: same-tier disagreement = SOURCE_CONFLICT (never merged); higher tier wins, all kept
  · link_entities → exact address / exact full name only; anything weaker = ENTITY_MATCH_UNCERTAIN
  · meeting_pack → participants · purpose · related tasks · previous commitments · relevant decisions · KPI/process · missing prep · agenda"""
import re, datetime, hashlib, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills"))
import registry

STOP = set("the a an and or of to for in on at by with from is are was were be this that these those it its we you our your i my me he she they them his her their will would can could should please about into over under after before as re fw fwd ի է են ու և որ այս այն մենք դուք ես նա".split())
IGNORE_SENDER = re.compile(r"(no-?reply|noreply|donotreply|do-not-reply|notification|notifications|newsletter|mailer-daemon|postmaster|webinar|marketing|digest|alerts?@|info@|news@|updates?@|bounce)", re.I)
IGNORE_SUBJECT = re.compile(r"^(accepted|declined|tentative|automatic reply|auto(matic)?[- ]?reply|out of office|delivery status|undeliverable|read:)\b|unsubscribe|password (changed|reset)|verification code|your (order|invoice|receipt|subscription)|webinar|invited to our|access token", re.I)
DECISION = re.compile(r"\b(approve|approval|approved\?|decide|decision|sign[- ]?off|your (ok|go-ahead|confirmation)|confirm (that|the|if)|authori[sz]e|go ahead\?)\b|հաստատ(ում|ես|ի)|որոշ(ում|ի)|թույլտվ", re.I)
ACTION = re.compile(r"\?|\b(please|pls|can you|could you|would you|need (you|your)|send me|share|provide|let me know|get back|respond|reply|by (monday|tuesday|wednesday|thursday|friday|tomorrow|eod|end of (day|week)|\d{1,2}[./]\d{1,2})|deadline|urgent|asap|reminder|follow[- ]?up|waiting for your)\b|խնդրում|կարո՞ղ|անհրաժեշտ|մինչև|շտապ|հիշեցնում|սպասում", re.I)
DELEGATE = re.compile(r"\b(assign|delegate|who can|someone (from|in)|your team|have (someone|somebody)|please forward to)\b|հանձնարար|ով կարող", re.I)
MONITOR = re.compile(r"\b(in progress|will (update|send|share|follow)|status update|working on (it|this)|pending|on hold|scheduled for|eta|expected by|update:)\b|ընթացքում|կուղարկեմ|կտամ", re.I)
FYI = re.compile(r"\b(fyi|for your information|no action (needed|required)|just so you know|heads[- ]?up|for the record|as discussed)\b|ի գիտություն|տեղեկության համար", re.I)
COMMIT = re.compile(r"\b(i will|i'll|we will|we'll|will (send|call|share|prepare|deliver|finish)|by (friday|monday|tomorrow|eod))\b|կզանգեմ|կուղարկեմ|կանեմ|կպատրաստեմ", re.I)

def tokens(text):
    return {w for w in re.findall(r"[\wԱ-և']+", str(text or "").lower()) if len(w) > 3 and w not in STOP}

def overlap(a, b): return tokens(a) & tokens(b)

def classify_message(m, head_addresses=()):
    """Rule-based class with the signals that fired (explainable). Head's own sent mail with a promise → MONITOR (commitment candidate)."""
    subj, prev, sender = str(m.get("subject") or ""), str(m.get("preview") or ""), str(m.get("sender") or "").lower()
    text = subj + " \n " + prev; sig = []
    if IGNORE_SENDER.search(sender) or IGNORE_SUBJECT.search(subj): return {"class": "IGNORE", "signals": ["automated/notification sender or subject"]}
    if sender and any(sender == h.lower() for h in head_addresses):
        if COMMIT.search(text): return {"class": "MONITOR", "signals": ["own message with a promise → commitment candidate"], "commitment_candidate": True}
        return {"class": "FYI", "signals": ["own message"]}
    if DECISION.search(text): sig.append("decision requested")
    if DELEGATE.search(text): sig.append("delegation cue")
    if ACTION.search(text): sig.append("request/question/deadline")
    if MONITOR.search(text): sig.append("progress/pending cue")
    if FYI.search(text): sig.append("fyi cue")
    if "decision requested" in sig: cls = "DECISION"
    elif "delegation cue" in sig: cls = "DELEGATE"
    elif "request/question/deadline" in sig: cls = "ACTION"
    elif "progress/pending cue" in sig: cls = "MONITOR"
    elif "fyi cue" in sig: cls = "FYI"
    else: cls = "FYI"; sig.append("no request signal")
    if m.get("flagged") and cls in ("FYI", "MONITOR"): cls = "ACTION"; sig.append("flagged by the owner")
    return {"class": cls, "signals": sig, "commitment_candidate": bool(COMMIT.search(prev)) and cls != "IGNORE"}

def _match(text, items, key):
    """Conservative linking: ≥2 significant shared tokens = MATCHED, 1 = ENTITY_MATCH_UNCERTAIN, 0 = NO_MATCH."""
    best, best_n = None, 0
    for it in items:
        n = len(overlap(text, it.get(key, "")))
        if n > best_n: best, best_n = it, n
    if best_n >= 2: return "MATCHED", best
    if best_n == 1: return "ENTITY_MATCH_UNCERTAIN", best
    return "NO_MATCH", None

def open_loop_candidates(messages, tasks=(), commitments=(), decisions=(), today=None, head_addresses=()):
    today = today or datetime.date.today()
    if isinstance(today, str): today = datetime.date.fromisoformat(today)
    out, seen_conv = [], {}
    for m in sorted(messages, key=lambda x: str(x.get("received") or ""), reverse=True):
        c = classify_message(m, head_addresses)
        if c["class"] == "IGNORE": continue
        conv = m.get("conversation_id") or m.get("conversation_topic") or m.get("subject")
        cid = "CAND-" + hashlib.sha256(str(conv).encode("utf-8")).hexdigest()[:10]
        dup = seen_conv.get(cid)
        ms, mt = _match(m.get("subject", "") + " " + m.get("preview", "")[:200], list(tasks), "title" if tasks and "title" in (tasks[0] if isinstance(tasks, list) and tasks else {}) else "task")
        cs, cm = _match(m.get("subject", "") + " " + m.get("preview", "")[:200], list(commitments), "text")
        ds, dd = _match(m.get("subject", ""), list(decisions), "decision")
        try: age = (today - datetime.date.fromisoformat(str(m.get("received"))[:10])).days
        except Exception: age = None
        cand = {"candidate_id": cid, "kind": "CANDIDATE_OPEN_LOOP", "class": c["class"], "signals": c["signals"], "subject": m.get("subject"), "counterpart": m.get("sender_name") or m.get("sender"), "counterpart_address": m.get("sender"),
                "received": m.get("received"), "age_days": age, "unread": m.get("unread"), "commitment_candidate": c.get("commitment_candidate", False),
                "evidence": {"integration_id": "INT-OL-MAIL", "record_id": m.get("record_id"), "conversation_id": m.get("conversation_id")},
                "task_match": ms, "matched_task": ({"id": mt.get("source_record_id") or mt.get("id"), "title": mt.get("title") or mt.get("task")} if mt else None),
                "commitment_match": cs, "matched_commitment": ({"op_id": cm.get("op_id"), "text": cm.get("text")} if cm else None),
                "decision_match": ds, "matched_decision": ({"op_id": dd.get("op_id"), "decision": dd.get("decision")} if dd else None),
                "duplicate_of": dup, "permanent": False, "note": "candidate from mail — becomes a task/commitment only when Gev confirms (no automatic business fact)"}
        if not dup: seen_conv[cid] = cid
        out.append(cand)
    return out

def link_entities(a, b):
    """a/b: {name, address}. Exact address or exact normalized full name = MATCH; partial = ENTITY_MATCH_UNCERTAIN; else NO_MATCH."""
    an, bn = " ".join(str(a.get("name") or "").lower().split()), " ".join(str(b.get("name") or "").lower().split())
    aa, ba = str(a.get("address") or "").lower(), str(b.get("address") or "").lower()
    if aa and ba and aa == ba: return {"status": "MATCH", "basis": "address"}
    if an and bn and an == bn and len(an.split()) >= 2: return {"status": "MATCH", "basis": "full name"}
    if an and bn and (set(an.split()) & set(bn.split())): return {"status": "ENTITY_MATCH_UNCERTAIN", "basis": "partial name overlap — not merged"}
    return {"status": "NO_MATCH", "basis": None}

def reconcile_fact(fact_type, observations, fact_authority=None):
    """observations: [{source, value, retrieved_at, record_id, ...}] → RESOLVED (with every observation kept and lower-tier differences listed),
    SOURCE_CONFLICT (same-tier disagreement), AUTHORITY_UNDEFINED (no configured hierarchy → no guess), NO_OBSERVATION."""
    fa = (fact_authority or registry.FACT_AUTHORITY).get(fact_type)
    if not fa: return {"status": "AUTHORITY_UNDEFINED", "fact_type": fact_type, "observations": list(observations), "reason": "no configured source hierarchy for this fact type — live ≠ correct; ask Gev which source rules" + (" (task facts are scoped: register_task_* vs crm_task_*)" if "task" in str(fact_type) else "")}
    tiers = fa["tiers"]; obs = [o for o in observations if o.get("source")]
    unknown = [o["source"] for o in obs if not any(o["source"] in t for t in tiers)]
    for i, tier in enumerate(tiers):
        here = [o for o in obs if o["source"] in tier]
        if not here: continue
        vals = {str(o.get("value")) for o in here}
        if len(vals) > 1:
            return {"status": "SOURCE_CONFLICT", "code": "SOURCE_CONFLICT", "fact_type": fact_type, "tier": i, "sources": sorted({o["source"] for o in here}), "values": sorted(vals), "observations": obs,
                    "resolution": "not chosen — same-authority sources disagree; Gev decides or a source is corrected", "label": "UNKNOWN"}
        win = here[0]; lower = [o for o in obs if o["source"] not in tier and o["source"] not in unknown and str(o.get("value")) != str(win.get("value"))]   # out-of-scope sources are ignored, not "overridden"
        return {"status": "RESOLVED", "fact_type": fact_type, "value": win.get("value"), "source": win["source"], "tier": i, "retrieved_at": win.get("retrieved_at"), "record_id": win.get("record_id"),
                "overridden": lower, "observations": obs, "unconfigured_sources_ignored": unknown, "out_of_scope_ignored": [o["source"] for o in obs if o["source"] in unknown], "scope": fa.get("scope"), "system_of_record": fa.get("system_of_record"),
                "label": "LIVE_DATA" if str(win["source"]).startswith("INT-") else "CONFIRMED", "authority_src": fa.get("src", [])}
    return {"status": "NO_OBSERVATION", "fact_type": fact_type, "observations": obs, "unconfigured_sources_ignored": unknown, "label": "UNKNOWN"}

def reconcile_task_link(register_task, crm_task, link):
    """Scope-aware cross-system task view (audit finding 3). register_task: {status, due, source:"INT-TASKS", record_id};
    crm_task: {status, deadline, source:"INT-B24", record_id}; link: result of link_entities / matching (status MATCH|ENTITY_MATCH_UNCERTAIN|NO_MATCH).
    Each system stays authoritative for ITS OWN record; nothing is overridden. A confirmed link with different states → STATUS_DIVERGENCE (a signal for Gev, not a merge)."""
    reg = {"source": "INT-TASKS", "scope": "management register", "status": (register_task or {}).get("status"), "due": (register_task or {}).get("due"), "record_id": (register_task or {}).get("record_id")} if register_task else None
    crm = {"source": "INT-B24", "scope": "Bitrix24-native task", "status": (crm_task or {}).get("status"), "deadline": (crm_task or {}).get("deadline"), "record_id": (crm_task or {}).get("record_id")} if crm_task else None
    ls = (link or {}).get("status", "NO_MATCH")
    out = {"register": reg, "crm": crm, "link": ls, "override": None, "note": "each system is the system of record for its own task; no status is copied across"}
    if not reg or not crm or ls != "MATCH":
        out["status"] = "UNLINKED" if ls == "NO_MATCH" or not (reg and crm) else "ENTITY_MATCH_UNCERTAIN"; return out
    out["status"] = "LINKED"
    if str(reg["status"]) != str(crm["status"]):
        out["code"] = "STATUS_DIVERGENCE"; out["divergent"] = True; out["label"] = "UNKNOWN"
        out["resolution_required"] = "Gev confirms which record is stale — the register is corrected by hand, Bitrix by its owner; Deputy writes nothing"
    else: out["divergent"] = False
    return out

def meeting_pack(meeting, tasks=(), commitments=(), decisions=(), business_available=False):
    title = meeting.get("title") or ""; text = title + " " + (meeting.get("description_preview") or "")
    rel = [t for t in tasks if len(overlap(text, t.get("title") or t.get("task") or "")) >= 2]
    unc = [t for t in tasks if len(overlap(text, t.get("title") or t.get("task") or "")) == 1]
    parts = meeting.get("participants") or []
    part_names = {p.get("name", "").lower() for p in parts}
    prev = [c for c in commitments if len(overlap(text, c.get("text", ""))) >= 1 or any(n and n in str(c.get("owner", "")).lower() for n in part_names)]
    decs = [d for d in decisions if len(overlap(text, d.get("decision", ""))) >= 1]
    kpis, procs = [], []
    if business_available:
        try:
            import business
            kpis = [{"id": k["kpi_id"], "name": k["name"], "target": k["target"]} for k in business.find_kpis(title, limit=4)]
            procs = [{"id": p["process_id"], "name": p["name"], "owner": p["accountable_owner"]} for p in business.find_processes(title, limit=3)]
        except Exception: pass
    missing = []
    if not (meeting.get("description_preview") or "").strip(): missing.append("purpose/agenda not in the invitation — ask the organizer or set it")
    if not rel: missing.append("no related open task in the register (nothing to close or report)")
    if not prev: missing.append("no previous commitment linked to this topic/participants")
    if not decs: missing.append("no logged decision on this topic")
    if not parts: missing.append("participants not listed in the invitation")
    if business_available and not kpis: missing.append("no KPI in the business model matches the topic — numbers will be UNKNOWN")
    agenda = [f"Status: {t.get('title') or t.get('task')} (owner {t.get('owner', '?')}, due {t.get('due') or '—'})" for t in rel[:5]]
    agenda += [f"Decision needed: {d.get('decision')}" for d in decs[:3]]
    questions = [f"What is the completion evidence for: {t.get('title') or t.get('task')}?" for t in rel[:3]]
    return {"meeting": {k: meeting.get(k) for k in ("record_id", "title", "start", "end", "location", "organizer", "online_link", "participant_count")},
            "participants": parts, "purpose": (meeting.get("description_preview") or "").strip()[:300] or "UNKNOWN — not in the invitation",
            "related_tasks": rel, "related_tasks_uncertain": unc, "previous_commitments": prev, "relevant_decisions": decs, "kpis": kpis, "processes": procs,
            "missing_preparation": missing, "recommended_agenda": agenda, "recommended_questions": questions,
            "context_found": bool(rel or prev or decs), "note": "" if (rel or prev or decs) else "no related context in the register, commitments or decisions — nothing was fabricated"}
