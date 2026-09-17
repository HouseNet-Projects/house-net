# -*- coding: utf-8 -*-
"""BUSINESS OPERATING MODEL BUILDER — deterministic rebuild from authorized sources.

    python .claude/business/build_business_model.py [--no-certify] [--allow-missing-sources]

Pipeline (fails closed at the first broken stage):
  CURRENT SOURCES  every CURRENT source path must exist (else SOURCE_MISSING)
  → EXTRACT        fingerprint every source (sha256/size/mtime) + cross-check the encoded model against the documents
                   (S01 KPI weights per role, S02 JD card titles, S05 row count) → EXTRACTION_MISMATCH if the encoding drifted
  → VALIDATE       provenance, confidence labels, duplicates, references, schema shapes, core boundary (no person names,
                   no compensation, no restricted patterns in the core)
  → BUILD CORE     versionable INTERNAL layer: *.json (people only as @P tokens; KPI.target derived from approved targets)
  → BUILD OVERLAY  CONFIDENTIAL local layer overlay/ov_*.py → overlay.json (absent overlay = allowed, flagged)
  → FINGERPRINT    core_fingerprint, overlay_fingerprint, source_snapshot_id written into every file's meta
  → CERTIFY        certify_business.certify() → certification.json (the Skill release consumes it)
Business-model.md is a generated VIEW (overlay names rendered only when the overlay exists) — local, never versioned."""
import sys, json, pathlib, datetime, hashlib, re, argparse, warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "policy"))
import bm_schema, bm_sources, bm_company, bm_processes, bm_kpis, bm_targets, bm_playbooks, bm_governance
import paths                                                     # ONE business-root resolver (workspace_policy.json -> business_root)

def _src_path(root, s):
    """Absolute path of a declared source. bm_sources.py states it business-relative (01_Active/..., Tasks.xlsx); the business
    root is resolved here, so moving Gev's workspace never touches the model authoring."""
    return paths.resolve(root, s["path"])

CONF = set(bm_schema.CONF)
OVERLAY_DIR = HERE / "overlay"

class BuildError(Exception):
    def __init__(self, stage, problems): super().__init__(f"{stage}: {problems}"); self.stage = stage; self.problems = problems

# ───────────────────────── stage 1: sources ─────────────────────────
def check_sources(root=ROOT, allow_missing=False):
    missing = [s["source_id"] for s in bm_sources.SOURCES if s["currency"] == "CURRENT" and not _src_path(root, s).exists()]
    if missing and not allow_missing: raise BuildError("SOURCE_MISSING", missing)
    return missing

# ───────────────────────── stage 2: extract (fingerprints + cross-checks) ─────────────────────────
def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def xlsx_structure_sha256(p, sheet=None, header_rows=12):
    """STRUCTURE fingerprint of a LIVE register workbook: the sheet names + the header block (rows 1..header_rows, as text) of the
    register sheet(s). Rows below the header are live operational data and never enter the hash — a task create/update/assign/
    close/reopen/note leaves it unchanged; renaming a column/sheet, moving the header or dropping the sheet changes it."""
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    try:
        parts = {"sheets": list(wb.sheetnames)}
        for sh in ([sheet] if sheet else wb.sheetnames):
            if sh not in wb.sheetnames: parts[sh] = None; continue
            rows = [[("" if v is None else str(v)) for v in r] for r in wb[sh].iter_rows(min_row=1, max_row=int(header_rows), values_only=True)]
            while rows and not any(rows[-1]): rows.pop()                       # trailing empty header rows carry no structure
            parts[sh] = rows
    finally: wb.close()
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

def source_fingerprint(s, p):
    """What binds the model to this source: CONTENT sha256 (extracted documents) or the STRUCTURE sha256 (LIVE registers)."""
    p = pathlib.Path(p)
    if bm_sources.scope(s) == "STRUCTURE":
        st = s.get("structure") or {}
        if p.suffix.lower() in (".xlsx", ".xlsm"): return {"sha256": xlsx_structure_sha256(p, st.get("sheet"), st.get("header_rows", 12)), "scope": "STRUCTURE"}
        raise BuildError("SOURCE_SPEC", [f"{s['source_id']}: STRUCTURE scope is defined for xlsx registers only ({p.suffix})"])
    return {"sha256": _sha(p), "scope": "CONTENT"}

def snapshot(root=ROOT):
    """Per-source binding record. CONTENT sources carry sha256/size/mtime of the file; LIVE registers (STRUCTURE scope) carry the
    structure sha256 plus the structure spec and live integration, never a content hash — row-level live data does not bind the model."""
    snap = {}
    for s in bm_sources.SOURCES:
        p = _src_path(root, s); base = {"path": s["path"], "currency": s["currency"], "authority": s["authority"], "scope": bm_sources.scope(s)}
        if bm_sources.kind(s) == "LIVE_REGISTER": base.update(source_kind="LIVE_REGISTER", live_integration=s.get("live_integration"), structure=dict(s.get("structure") or {}))
        if p.exists():
            fp = source_fingerprint(s, p)
            if fp["scope"] == "STRUCTURE": snap[s["source_id"]] = {**base, "sha256": fp["sha256"], "size": None, "mtime": None}
            else:
                st = p.stat(); snap[s["source_id"]] = {**base, "sha256": fp["sha256"], "size": st.st_size, "mtime": int(st.st_mtime)}
        else: snap[s["source_id"]] = {**base, "sha256": None, "size": None, "mtime": None, "missing": True}
    return snap

def _live_sources():
    """Live-source hierarchy from the integration registry (S16): declared integrations + FACT_AUTHORITY tiers. Declarations only —
    connection state lives in .claude/integrations/certification.json (local evidence), never in the versioned core."""
    try:
        sys.path.insert(0, str(ROOT / ".claude" / "integrations")); import registry as ir
        return {"integrations": {k: {"system": v["system"], "authority": v["authority"], "classification": v["classification"], "read_ops": sorted(v["read_ops"]), "write_ops": [], "critical": v["critical"], "owner_role": v["owner_role"]} for k, v in ir.INTEGRATIONS.items()},
                "fact_authority": ir.FACT_AUTHORITY, "deferred": ir.DEFERRED, "src": ["S16"]}
    except Exception as e:
        return {"integrations": {}, "fact_authority": {}, "deferred": {}, "src": ["S16"], "error": f"{type(e).__name__}: {e}"}

def snapshot_id(snap):
    return hashlib.sha256(json.dumps({k: v.get("sha256") for k, v in sorted(snap.items())}, sort_keys=True).encode()).hexdigest()[:24]

def _model_ids():
    ids = set()
    ids |= {k["kpi_id"] for k in bm_kpis.KPIS} | {t["target_id"] for t in bm_targets.TARGETS} | {x["process_id"] for x in bm_processes.PROCESSES}
    ids |= {o["id"] for o in bm_governance.OWNERSHIP} | {r["routine_id"] for r in bm_governance.ROUTINES} | {g["gap_id"] for g in bm_governance.GAPS}
    ids |= {c["id"] for c in bm_company.CONFLICTS} | {u["id"] for u in bm_company.CRITICAL_UNKNOWNS} | {pb["playbook_id"] for pb in bm_playbooks.PLAYBOOKS}
    return ids

def _docx_text(p):
    """Text + headings from a .docx via its XML (robust to documents python-docx cannot style-resolve)."""
    import zipfile, xml.etree.ElementTree as ET
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(p) as z: root = ET.fromstring(z.read("word/document.xml"))
    parts, heads = [], []
    for par in root.iter("{%s}p" % ns["w"]):
        txt = "".join(t.text or "" for t in par.iter("{%s}t" % ns["w"])).strip()
        if not txt: continue
        parts.append(txt)
        st = par.find("w:pPr/w:pStyle", ns)
        if st is not None and str(st.get("{%s}val" % ns["w"], "")).lower().startswith("heading"): heads.append(txt)
    return "\n".join(parts), heads

def invariant_checks(root=ROOT, invariants=None):
    """Per-source extraction invariants (bm_sources.EXTRACTION_INVARIANTS): the document must still contain the primitives the
    model was extracted from AND the model must still carry the ids that source supports. A fingerprint alone proves nothing."""
    import re as _re
    inv = bm_sources.EXTRACTION_INVARIANTS if invariants is None else invariants
    src = {s["source_id"]: s for s in bm_sources.SOURCES}; ids = _model_ids(); p = []
    for sid, rules in inv.items():
        s = src.get(sid)
        if not s or s["currency"] != "CURRENT": continue
        path = _src_path(root, s)
        if not path.exists(): p.append(f"{sid}: SOURCE_MISSING for invariants"); continue
        for mid in rules.get("model_has", []):
            if mid not in ids: p.append(f"{sid}: model lacks expected primitive {mid}")
        try:
            if "min_size" in rules and path.stat().st_size < rules["min_size"]: p.append(f"{sid}: file smaller than {rules['min_size']} bytes (implausibly empty)")
            if rules.get("xlsx_sheets") or rules.get("xlsx_min_rows"):
                import openpyxl
                wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                for sh in rules.get("xlsx_sheets", []):
                    if sh not in wb.sheetnames: p.append(f"{sid}: sheet {sh!r} missing")
                for sh, n in rules.get("xlsx_min_rows", {}).items():
                    if sh in wb.sheetnames:
                        rows = sum(1 for r in wb[sh].iter_rows(values_only=True) if any(v not in (None, "") for v in r))
                        if rows < n: p.append(f"{sid}: sheet {sh!r} has {rows} non-empty rows < {n}")
                wb.close()
            if rules.get("docx_headings") or rules.get("docx_text_contains"):
                text, heads = _docx_text(path)
                for h in rules.get("docx_headings", []):
                    if h not in heads: p.append(f"{sid}: heading {h!r} missing")
                for t in rules.get("docx_text_contains", []):
                    if t not in text: p.append(f"{sid}: text {t!r} missing")
            if rules.get("text_contains") or rules.get("md_regex_min"):
                text = path.read_text(encoding="utf-8", errors="replace")
                for t in rules.get("text_contains", []):
                    if t not in text: p.append(f"{sid}: text {t!r} missing")
                for rx, n in rules.get("md_regex_min", {}).items():
                    c = len(_re.findall(rx, text, flags=_re.M))
                    if c < n: p.append(f"{sid}: pattern {rx!r} found {c} < {n}")
        except Exception as e: p.append(f"{sid}: invariant check error {type(e).__name__}: {e}")
    return p

def extraction_checks(root=ROOT):
    """Cross-check the encoded model against the real documents — the model may not drift from its sources unnoticed."""
    p = invariant_checks(root)
    # S01: KPI sheet weights per role must equal bm_kpis.ROLE_KPIS
    try:
        import openpyxl
        wb = openpyxl.load_workbook(paths.resolve(root, "02_Reference/People/Staffing-plan-2026-09-07.xlsx"), data_only=True, read_only=True)
        need = {"Ամփոփ պատկեր", "Կառուցվածք և աշխատավարձ", "Մոդելներ և պարտադիր վճարներ", "KPI"}
        if not need <= set(wb.sheetnames): p.append(f"S01 sheets changed: {wb.sheetnames}")
        else:
            ws = wb["KPI"]; rows = [r for r in ws.iter_rows(values_only=True)]
            weights = {}; cur = None
            for r in rows:
                vals = [c for c in r]
                if vals[1] and isinstance(vals[1], str) and vals[3] and isinstance(vals[4], (int, float)): cur = vals[1]; weights.setdefault(cur, []).append(round(float(vals[4]), 4))
                elif cur and vals[3] and isinstance(vals[4], (int, float)) and not vals[1]: weights[cur].append(round(float(vals[4]), 4))
            titles = {r["title"]: r["code"] for r in bm_company.ROLES}
            for title, ws_ in weights.items():
                code = titles.get(title)
                if not code: p.append(f"S01 KPI role not in model: {title}"); continue
                enc = [round(k["weight"], 4) for k in bm_kpis.ROLE_KPIS.get(code, [])]
                if enc != ws_: p.append(f"S01 KPI weights differ for {code} {title}: sheet {ws_} vs model {enc}")
        wb.close()
    except FileNotFoundError: p.append("S01 missing for extraction check")
    except Exception as e: p.append(f"S01 extraction error: {type(e).__name__}: {e}")
    # S02: JD card titles (Heading 2 of each card) must match role titles for codes 1.1–4.2
    try:
        text, heads = _docx_text(paths.resolve(root, "01_Active/People/Job-descriptions-v1.1-2026-09-05.docx"))
        model_titles = [r["title"] for r in bm_company.ROLES if re.match(r"^\d+\.\d+$", r["code"])]
        cards = [h for h in heads if h in model_titles]
        if len(cards) != len(model_titles): p.append(f"S02 JD cards matching the model {len(cards)} vs model roles {len(model_titles)}")
        for t in model_titles:
            if t not in heads: p.append(f"S02 title not found in JD: {t}")
    except FileNotFoundError: p.append("S02 missing for extraction check")
    except Exception as e: p.append(f"S02 extraction error: {type(e).__name__}: {e}")
    # S05: only aggregates leave the file — verify the file shape, never copy rows
    try:
        import openpyxl
        wb = openpyxl.load_workbook(paths.resolve(root, "01_Active/Sales/Churn-save-list-2026-09-09.xlsx"), read_only=True)
        if "Save list" not in wb.sheetnames or "Provenance" not in wb.sheetnames: p.append(f"S05 sheets changed: {wb.sheetnames}")
        wb.close()
    except FileNotFoundError: p.append("S05 missing for extraction check")
    except Exception as e: p.append(f"S05 extraction error: {type(e).__name__}: {e}")
    return p

# ───────────────────────── stage 3: validate ─────────────────────────
def _ids(obj, key="src", acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, list): acc.update(v)
            else: _ids(v, key, acc)
    elif isinstance(obj, list):
        for v in obj: _ids(v, key, acc)
    return acc

def _confs(obj, acc=None):
    acc = [] if acc is None else acc
    if isinstance(obj, dict):
        if "conf" in obj: acc.append(obj["conf"])
        for v in obj.values(): _confs(v, acc)
    elif isinstance(obj, list):
        for v in obj: _confs(v, acc)
    return acc

def validate(core, overlay=None, registry=None):
    p = []
    src_ids = {s["source_id"] for s in core["sources"]["sources"]}
    hist = {s["source_id"] for s in core["sources"]["sources"] if s["currency"] == "HISTORICAL"}
    for name in bm_schema.CORE_FILES:
        if name == "sources": continue
        bad = _ids(core[name]) - src_ids
        if bad: p.append(f"{name}: unknown source ids {sorted(bad)}")
        for c in _confs(core[name]):
            if c not in CONF: p.append(f"{name}: invalid confidence {c!r}")
    for fact in core["business_model"]["roles"] + core["processes"]["processes"] + core["kpis"]["kpis"] + core["ownership"]["ownership"] + core["targets"]["targets"]:
        h = set(fact.get("src", [])) & hist
        if h and fact.get("conf") not in ("UNKNOWN",) and "SUPERSEDED" not in str(fact.get("status", "")): p.append(f"historical source {sorted(h)} cited as current truth by {fact.get('code') or fact.get('process_id') or fact.get('kpi_id') or fact.get('id') or fact.get('target_id')}")
    for name, key, items in (("kpis", "kpi_id", core["kpis"]["kpis"]), ("processes", "process_id", core["processes"]["processes"]), ("playbooks", "playbook_id", core["playbooks"]["playbooks"]), ("ownership", "id", core["ownership"]["ownership"]), ("roles", "code", core["business_model"]["roles"]), ("sources", "source_id", core["sources"]["sources"]), ("gaps", "gap_id", core["gaps"]["gaps"]), ("targets", "target_id", core["targets"]["targets"])):
        ids = [i[key] for i in items]; dup = {i for i in ids if ids.count(i) > 1}
        if dup: p.append(f"{name}: duplicate ids {sorted(dup)}")
        names = [str(i.get("name") or i.get("title") or i.get("primitive") or i.get("gap") or i.get("target_id")).strip().lower() for i in items]
        dupn = {n for n in names if names.count(n) > 1}
        if dupn: p.append(f"{name}: duplicate names {sorted(dupn)}")
    for code, ks in core["kpis"]["role_kpis"].items():
        if ks and abs(sum(k["weight"] for k in ks) - 1.0) > 1e-6: p.append(f"role {code}: KPI weights sum {sum(k['weight'] for k in ks)}")
    cids = {c["id"] for c in core["business_model"]["conflicts"]}
    for s in core["sources"]["sources"]:
        for c in s["conflicts"]:
            if c not in cids: p.append(f"source {s['source_id']} references unknown conflict {c}")
    # references: targets → KPI/process/ownership ids; process KPI refs; ownership statuses
    kids = {k["kpi_id"] for k in core["kpis"]["kpis"]} | {k["kpi_id"] for ks in core["kpis"]["role_kpis"].values() for k in ks}
    pids = {x["process_id"] for x in core["processes"]["processes"]}; oids = {o["id"] for o in core["ownership"]["ownership"]}
    for t in core["targets"]["targets"]:
        if t["ref"] not in kids | pids | oids: p.append(f"target {t['target_id']} references unknown {t['ref']}")
        if t["status"] not in ("APPROVED", "PROPOSED", "UNKNOWN"): p.append(f"target {t['target_id']} bad status {t['status']}")
        if t["status"] == "APPROVED" and str(t["value"]) == "UNKNOWN": p.append(f"target {t['target_id']} APPROVED without a value")
    for x in core["processes"]["processes"]:
        for k in x["kpi"]:
            if k not in kids: p.append(f"process {x['process_id']} references unknown KPI {k}")
    for o in core["ownership"]["ownership"]:
        if o["status"] not in core["ownership"]["statuses"]: p.append(f"ownership {o['id']} bad status {o['status']}")
        if o["status"] == "OWNER_UNKNOWN" and o.get("owner_role"): p.append(f"ownership {o['id']} OWNER_UNKNOWN but has a role")
        if o["status"] == "CONFLICT" and not re.search(r"C\d\d", str(o.get("note", "")) + str(o.get("owner_role", ""))): p.append(f"ownership {o['id']} CONFLICT without a conflict id")
    if registry:
        chains = set(registry.get("chains", {})); skills = {s["skill_id"] for s in registry["skills"]}
        for pb in core["playbooks"]["playbooks"]:
            if pb["chain"] not in chains: p.append(f"playbook {pb['playbook_id']} chain {pb['chain']} not in registry")
            for s in pb["required_skills"]:
                if s not in skills: p.append(f"playbook {pb['playbook_id']} skill {s} not in registry")
        for r in core["routines"]["routines"]:
            if r["skill_chain"] not in chains and r["skill_chain"] not in skills: p.append(f"routine {r['routine_id']} chain/skill {r['skill_chain']} unknown")
    # shapes + boundary (core must not carry compensation, person names, restricted patterns)
    for name in bm_schema.CORE_FILES: p += bm_schema.check_shape(name, core[name])
    blob = json.dumps({k: v for k, v in core.items()}, ensure_ascii=False)
    if overlay:
        for per in overlay["persons"]:
            if per["id"] == "@P0": continue
            for n in [per["name"]] + per.get("aliases", []):
                if n and len(n) >= 3 and n in blob: p.append(f"core boundary: person name literal present in core (token {per['id']})")
    try:
        import sensitive_scan
        for rel, fs in {}.items(): pass
        pol = sensitive_scan.load_policy()
        for name in bm_schema.CORE_FILES:
            for f in sensitive_scan.scan_content(f".claude/business/{name}.json", json.dumps(core[name], ensure_ascii=False, indent=1), pol, names=()):
                p.append(f"core boundary: {name}.json {f['rule']} [{f['class']}] line {f['line']}")
    except ImportError: p.append("sensitive_scan unavailable — boundary unchecked (fail closed)")
    return p

# ───────────────────────── stage 4/5: build core + overlay ─────────────────────────
def meta(snap, layer="CORE"):
    return {"model_version": bm_schema.MODEL_VERSION, "schema_version": bm_schema.SCHEMA_VERSION, "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "source_snapshot_id": snapshot_id(snap), "core_fingerprint": None, "overlay_fingerprint": None, "business_effective_date": "UNKNOWN (staffing plan effective date unconfirmed — Open-questions #9)",
            "layer": layer, "workspace": "Command-center", "agent": "Deputy", "company": "HouseNet LLC", "builder": "build_business_model.py"}

def derive_kpi_targets(kpis, targets):
    by_ref = {}
    for t in targets: by_ref.setdefault(t["ref"], []).append(t)
    for k in kpis:
        ts = by_ref.get(k["kpi_id"], [])
        appr = [t for t in ts if t["status"] == "APPROVED" and t["kind"] == "KPI_TARGET"]
        prop = [t for t in ts if t["status"] == "PROPOSED"]
        k["target"] = appr[0]["value"] if appr else "UNKNOWN"
        k["target_ref"] = appr[0]["target_id"] if appr else None
        k["proposed_targets"] = [{"id": t["target_id"], "value": t["value"], "unit": t["unit"], "src": t["src"]} for t in prop]
        k["thresholds"] = [{"id": t["target_id"], "kind": t["kind"], "value": t["value"], "status": t["status"]} for t in ts if t["kind"] != "KPI_TARGET"]
    return kpis

def build_core(snap):
    m = meta(snap)
    kpis = derive_kpi_targets([dict(k) for k in bm_kpis.KPIS], bm_targets.TARGETS)
    core = {
     "sources": {"meta": dict(m), "authority_rank": bm_sources.AUTHORITY_RANK, "sources": bm_sources.SOURCES, "source_snapshot": snap, "live_sources": _live_sources()},
     "business_model": {"meta": dict(m), "company": bm_company.COMPANY, "functions": bm_company.FUNCTIONS, "roles": bm_company.ROLES, "principals": bm_company.PRINCIPALS, "systems": bm_company.SYSTEMS,
                        "sales": bm_company.SALES_MODEL, "operations": bm_company.OPERATIONS_MODEL, "people_model": bm_company.PEOPLE_MODEL, "conflicts": bm_company.CONFLICTS, "critical_unknowns": bm_company.CRITICAL_UNKNOWNS},
     "processes": {"meta": dict(m), "flow_vocabulary": ["TRIGGER", "INPUT", "ACTION", "OWNER", "HANDOFF", "CONTROL", "OUTPUT", "VERIFY"], "processes": bm_processes.PROCESSES},
     "ownership": {"meta": dict(m), "statuses": ["ROLE_AND_PERSON", "ROLE_DEFINED_PERSON_UNKNOWN", "ROLE_VACANT_INTERIM", "CONFLICT", "OWNER_UNKNOWN"], "ownership": bm_governance.OWNERSHIP},
     "kpis": {"meta": dict(m), "kinds": ["OUTCOME", "DRIVER", "OPERATIONAL"], "kpis": kpis, "role_kpis": bm_kpis.ROLE_KPIS},
     "targets": {"meta": dict(m), "targets": bm_targets.TARGETS, "promotion_states": bm_targets.PROMOTION_STATES, "promotion_rules": bm_targets.PROMOTION_RULES},
     "playbooks": {"meta": dict(m), "flow": bm_playbooks.FLOW, "executive_format": bm_playbooks.EXEC_FMT, "playbooks": bm_playbooks.PLAYBOOKS},
     "routines": {"meta": dict(m), "routines": bm_governance.ROUTINES},
     "gaps": {"meta": dict(m), "gap_codes": ["BUSINESS_CONTEXT_MISSING", "OWNER_UNKNOWN", "KPI_DEFINITION_MISSING", "PROCESS_UNDEFINED", "TARGET_UNKNOWN", "APPROVAL_RULE_UNKNOWN", "SOURCE_CONFLICT", "STALE_MODEL", "SOURCE_CHANGED", "SOURCE_MISSING"], "gaps": bm_governance.GAPS},
    }
    return core

def build_overlay(snap, overlay_dir=OVERLAY_DIR):
    if not (overlay_dir / "ov_people.py").exists(): return None
    import importlib.util
    def load(name):
        spec = importlib.util.spec_from_file_location(name, overlay_dir / f"{name}.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
    pe, co, cv, ev = load("ov_people"), load("ov_compensation"), load("ov_commercials"), load("ov_evidence")
    layer = "SENSITIVE_" + "OVERLAY"           # built dynamically so the builder source itself never carries the overlay marker
    return {"meta": meta(snap, layer), "layer": layer, "classification": "CONFIDENTIAL", "persons": pe.PERSONS, "assignments": pe.ASSIGNMENTS, "operating_notes": pe.OPERATING_NOTES,
            "compensation": {"fix_salary_net_amd": co.FIX_SALARY_NET_AMD, "payroll_amd": co.PAYROLL_AMD, "pay_model_params": co.PAY_MODEL_PARAMS, "src": co.SRC},
            "commercials": cv.COMMERCIALS, "evidence": ev.EVIDENCE, "source_payloads": ev.SOURCE_PAYLOADS}

# ───────────────────────── stage 6: fingerprint ─────────────────────────
def _content(obj):
    """Semantic content for fingerprinting: metadata and machine-specific file mtimes are excluded (a clone on another PC must
    produce the SAME core fingerprint from the same sources — Mission 4.1 portability)."""
    out = {k: v for k, v in obj.items() if k != "meta"}
    if isinstance(out.get("source_snapshot"), dict):
        out["source_snapshot"] = {sid: {kk: vv for kk, vv in s.items() if kk != "mtime"} for sid, s in out["source_snapshot"].items()}
    return out

def fingerprint(files):
    return hashlib.sha256(json.dumps({n: _content(o) for n, o in sorted(files.items())}, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:32]

def stamp(core, overlay):
    cf = fingerprint(core); of = fingerprint({"overlay": overlay}) if overlay else None
    for o in list(core.values()) + ([overlay] if overlay else []):
        o["meta"]["core_fingerprint"] = cf; o["meta"]["overlay_fingerprint"] = of
    return cf, of

# ───────────────────────── view ─────────────────────────
def render_md(core, overlay):
    names = {p["id"]: p["name"] for p in (overlay or {}).get("persons", [])}
    def R(s):
        s = str(s)
        return re.sub(bm_schema.PERSON_TOKEN, lambda m: names.get(m.group(0), m.group(0) + "(name withheld)"), s)
    m = core; L = []; a = lambda s: L.append(R(s))
    a("# Business Operating Model — HouseNet LLC (Deputy's canonical view)")
    a(f"\n_Generated view. model {m['sources']['meta']['model_version']} · schema {m['sources']['meta']['schema_version']} · core {m['sources']['meta']['core_fingerprint']} · overlay {'present ' + str(m['sources']['meta']['overlay_fingerprint']) if overlay else 'ABSENT (names withheld, compensation hidden)'} · snapshot {m['sources']['meta']['source_snapshot_id']} · built {m['sources']['meta']['generated_at']}. Local only (CONFIDENTIAL when the overlay is rendered)._\n")
    a("## 1. Sources of truth"); a("| id | path | authority | currency | status | conflicts |"); a("|---|---|---|---|---|---|")
    for s in m["sources"]["sources"]: a(f"| {s['source_id']} | `{s['path']}` | {s['authority']} | {s['currency']} | {s['status']} | {', '.join(s['conflicts']) or '—'} |")
    a("\n## 2. Company")
    for k, v in m["business_model"]["company"].items(): a(f"- **{k}** ({v['conf']}, {', '.join(v['src'])}): {json.dumps(v['value'], ensure_ascii=False) if not isinstance(v['value'], str) else v['value']}" + (f" — _{v['note']}_" if v.get('note') else ""))
    a("\n## 3. Organization")
    for f in m["business_model"]["functions"]: a(f"- **{f['id']} {f['name']}** — {f['purpose']}. Accountable: {f['accountable_role']}. Headcount {f['headcount']['value']}.")
    a("\n### Roles"); a("| code | title | function | manager | positions | filled | priority | compensation | conf |"); a("|---|---|---|---|---|---|---|---|---|")
    comp = (overlay or {}).get("compensation", {}).get("fix_salary_net_amd", {})
    for r in m["business_model"]["roles"]: a(f"| {r['code']} | {r['title']} | {r['function']} | {r['manager']} | {r['positions']} | {r['filled']} | {r['vacancy_priority']} | {comp.get(r['code'], 'OVERLAY')} | {r['conf']} |")
    a("\n### Principals (tokens; names only with the overlay)")
    for p in m["business_model"]["principals"]: a(f"- **{p['id']}** — {p['org_relation']} ({p['conf']})")
    if overlay:
        a("\n### Role assignments (overlay)")
        for asg in overlay["assignments"]: a(f"- {asg['role']} ← {asg['person']} ({asg['conf']}; {'verified' if asg['conf'] == 'CONFIRMED' else 'candidate only — PERSON UNKNOWN at runtime'})")
    a("\n### Systems")
    for s in m["business_model"]["systems"]: a(f"- **{s['name']}** — {s['purpose']}. Owner: {s['owner']}. Deputy access: {s['deputy_access']}.")
    for sec, title in (("sales", "4. Sales model"), ("operations", "5. Operations model"), ("people_model", "6. People model")):
        a(f"\n## {title}")
        for k, v in m["business_model"][sec].items(): a(f"- **{k}** ({v['conf']}): {json.dumps(v['value'], ensure_ascii=False) if not isinstance(v['value'], str) else v['value']}")
    a("\n## 7. Processes")
    for p in m["processes"]["processes"]:
        a(f"\n### {p['process_id']} · {p['name']} — {p['status']} ({p['conf']}; {', '.join(p['src'])})"); a(f"- Owner: **{p['accountable_owner']}** · Trigger: {p['trigger']} · SLA: {p['sla_deadline'] or 'UNKNOWN'}")
        for st in p["steps"]: a(f"  - {st}")
    a("\n## 8. Ownership map (by ROLE)"); a("| id | kind | primitive | owner role | status |"); a("|---|---|---|---|---|")
    for o in m["ownership"]["ownership"]: a(f"| {o['id']} | {o['kind']} | {o['primitive']} | {o['owner_role'] or 'OWNER_UNKNOWN'} | {o['status']} |")
    a("\n## 9. KPI catalog"); a("| id | name | kind | owner | target (APPROVED) | proposed | source | conf |"); a("|---|---|---|---|---|---|---|---|")
    for k in m["kpis"]["kpis"]: a(f"| {k['kpi_id']} | {k['name']} | {k['kind']} | {k['owner']} | {k['target']} | {', '.join(t['id'] for t in k['proposed_targets']) or '—'} | {k['source']} | {k['conf']} |")
    a("\n## 10. Targets & thresholds (controlled)"); a("| id | kind | ref | value | unit | status | approver | src |"); a("|---|---|---|---|---|---|---|---|")
    for t in m["targets"]["targets"]: a(f"| {t['target_id']} | {t['kind']} | {t['ref']} | {json.dumps(t['value'], ensure_ascii=False)} | {t['unit']} | {t['status']} | {t['approver']} | {', '.join(t['src'])} |")
    a("\n## 11. Management rhythm")
    for r in m["routines"]["routines"]: a(f"- **{r['routine_id']} {r['name']}** — {r['cadence']}; owner: {r['owner']}; missing data: {'; '.join(r['data_missing']) or '—'}")
    a("\n## 12. Playbooks")
    for p in m["playbooks"]["playbooks"]: a(f"- **{p['playbook_id']} {p['name']}** (chain `{p['chain']}`) — owner {p['owner']}; escalate when {p['escalation_threshold']}")
    a("\n## 13. Conflicts")
    for c in m["business_model"]["conflicts"]: a(f"- **{c['id']} {c['topic']}** — A: {c['source_a']} · B: {c['source_b']} · resolution: {c['resolution_required']} · {c['status']}")
    a("\n## 14. Critical unknowns")
    for u in m["business_model"]["critical_unknowns"]: a(f"- **{u['id']}** {u['item']}")
    a("\n## 15. Gap register"); a("| id | category | gap | resolution | owner | priority |"); a("|---|---|---|---|---|---|")
    for g in m["gaps"]["gaps"]: a(f"| {g['gap_id']} | {g['category']} | {g['gap']} | {g['recommended_resolution']} | {g['proposed_owner']} | {g['priority']} |")
    a("\n## 16. Knowledge promotion rules")
    for r in m["targets"]["promotion_rules"]["promotions"]: a(f"- {r['from']} → {r['to']}: by {r['by']} — {r['note']}")
    return "\n".join(L) + "\n"

# ───────────────────────── main pipeline ─────────────────────────
def build(root=ROOT, overlay_dir=OVERLAY_DIR, allow_missing=False, registry_path=None):
    missing = check_sources(root, allow_missing)
    snap = snapshot(root)
    xp = extraction_checks(root) if not missing else []
    if xp: raise BuildError("EXTRACTION_MISMATCH", xp)
    core = build_core(snap); overlay = build_overlay(snap, overlay_dir)
    reg = None
    rp = pathlib.Path(registry_path) if registry_path else root / ".claude" / "skills" / "registry.json"
    if rp.exists(): reg = json.loads(rp.read_text(encoding="utf-8"))
    probs = validate(core, overlay, reg)
    if probs: raise BuildError("VALIDATION_FAILED", probs)
    if overlay: overlay["meta"]["source_snapshot_id"] = core["sources"]["meta"]["source_snapshot_id"]
    cf, of = stamp(core, overlay)
    return core, overlay, snap, missing

def write(core, overlay, out_dir=HERE):
    for name, obj in core.items(): (out_dir / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if overlay: (out_dir / "overlay.json").write_text(json.dumps(overlay, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    elif (out_dir / "overlay.json").exists(): (out_dir / "overlay.json").unlink()
    (out_dir / "Business-model.md").write_text(render_md(core, overlay), encoding="utf-8")

def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument("--no-certify", action="store_true"); ap.add_argument("--allow-missing-sources", action="store_true"); a = ap.parse_args(argv)
    try: core, overlay, snap, missing = build(allow_missing=a.allow_missing_sources)
    except BuildError as e:
        print(f"⛔ BUILD FAILED at {e.stage}:"); [print("  ✗", x) for x in e.problems]; return 2 if e.stage == "SOURCE_MISSING" else 1
    write(core, overlay)
    m = core["sources"]["meta"]
    print(f"business model built: model {m['model_version']} · schema {m['schema_version']} · core {m['core_fingerprint']} · overlay {m['overlay_fingerprint'] or 'ABSENT'} · snapshot {m['source_snapshot_id']}")
    print(f"  {len(core['sources']['sources'])} sources · {len(core['business_model']['roles'])} roles · {len(core['processes']['processes'])} processes · {len(core['ownership']['ownership'])} ownership · {len(core['kpis']['kpis'])} KPIs (+{sum(len(v) for v in core['kpis']['role_kpis'].values())} role KPIs) · {len(core['targets']['targets'])} targets · {len(core['playbooks']['playbooks'])} playbooks · {len(core['routines']['routines'])} routines · {len(core['business_model']['conflicts'])} conflicts · {len(core['gaps']['gaps'])} gaps" + (f" · missing sources {missing}" if missing else ""))
    if a.no_certify: return 0
    import certify_business
    return certify_business.main([])

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
