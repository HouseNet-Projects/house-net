# -*- coding: utf-8 -*-
"""DOCUMENT BRAIN — a rebuildable catalog/index of the workspace's documents (never a second truth): path · title · sha256 · modified ·
type · authority (from the workspace contract folder: 02_Reference = CURRENT_TRUTH, 01_Active = WORKING, 03_Completed/05_Archive =
HISTORICAL, 04_Sources = RAW_EVIDENCE, .claude/business = BUSINESS_MODEL, .claude/docs = CHARTER) · current/historical · sections.
Retrieval is deterministic (token overlap, authority-weighted); Business Operating Model facts override document similarity; two
current documents on the same subject with different content are surfaced as a CONFLICT, never silently picked.
The index lives in the local state dir (documents_index.json) and is rebuilt on demand — deleting it loses nothing."""
import re, json, hashlib, datetime, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "policy")); import paths        # ONE business-root resolver

AUTHORITY = {paths.to_repo("02_Reference"): "CURRENT_TRUTH", paths.to_repo("01_Active"): "WORKING", paths.to_repo("03_Completed"): "HISTORICAL",
             paths.to_repo("05_Archive"): "HISTORICAL", paths.to_repo("04_Sources"): "RAW_EVIDENCE", ".claude/business": "BUSINESS_MODEL",
             ".claude/docs": "CHARTER", paths.root_name(): "ROOT", "": "ROOT"}
WEIGHT = {"BUSINESS_MODEL": 3.0, "CURRENT_TRUTH": 2.5, "CHARTER": 2.0, "ROOT": 1.5, "WORKING": 1.5, "RAW_EVIDENCE": 1.0, "HISTORICAL": 0.5}
TEXT_EXT = {".md", ".txt", ".csv", ".json"}
STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "or", "for", "is", "it", "we", "with", "by", "at", "as", "be", "և", "ու", "որ", "են", "է", "ա", "մասին", "համար"}

def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())
def tokens(t): return {w for w in re.findall(r"[\w\-]+", _norm(t)) if len(w) > 2 and w not in STOP}
def _index_path():
    import engine; return pathlib.Path(engine.STATE_DIR) / "documents_index.json"

def _authority(rel):
    """Authority follows the AREA a document lives in. Both namespaces (.claude and the business root) are two segments deep."""
    parts = rel.replace("\\", "/").split("/")
    if parts[0] in (".claude", paths.root_name()) and len(parts) > 1: return AUTHORITY.get(f"{parts[0]}/{parts[1]}", "TECHNICAL" if parts[0] == ".claude" else "ROOT")
    return AUTHORITY.get(parts[0] if len(parts) > 1 else "", "ROOT")

def _title_and_sections(p):
    try: txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception: return p.stem, [], ""
    heads = re.findall(r"^#{1,3}\s+(.+)$", txt, re.M)
    return (heads[0].strip() if heads else p.stem), [h.strip()[:80] for h in heads[:40]], txt

def build(root=None):
    """Scan the contract folders; write the index; return it. Content is not stored — only metadata, section names and a small token bag."""
    root = pathlib.Path(root or ROOT); docs = []
    dirs = [paths.root(root)] + [paths.biz(d, repo_root=root) for d in ("01_Active", "02_Reference", "03_Completed", "04_Sources", "05_Archive")] + [root / ".claude" / "docs", root / ".claude" / "business"]
    for d in dirs:
        if not d.exists(): continue
        it = d.glob("*") if d == paths.root(root) else d.rglob("*")     # the business root itself holds only the registers; areas are recursive
        for p in it:
            if not p.is_file() or p.name.startswith(".") or "__pycache__" in p.parts or p.suffix.lower() not in TEXT_EXT | {".docx", ".xlsx", ".pdf"}: continue
            if d == root / ".claude" / "business" and p.suffix != ".md": continue
            rel = p.relative_to(root).as_posix(); auth = _authority(rel)
            title, sections, txt = _title_and_sections(p) if p.suffix.lower() in TEXT_EXT else (p.stem, [], "")
            m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name); ver = re.search(r"-v(\d+(?:\.\d+)?)", p.name)
            docs.append({"path": rel, "title": title, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16], "modified": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"), "size": p.stat().st_size, "type": p.suffix.lower().lstrip("."),
                         "authority": auth, "current": auth in ("CURRENT_TRUTH", "BUSINESS_MODEL", "CHARTER", "ROOT", "WORKING"), "date_in_name": m.group(1) if m else None, "version": ver.group(1) if ver else None, "sections": sections,
                         "subject": _norm(re.sub(r"(-v\d+(?:\.\d+)?)?(-\d{4}-\d{2}-\d{2})?$", "", p.stem).replace("-", " ")), "tokens": sorted(tokens(title + " " + " ".join(sections) + " " + txt[:4000]))[:400]})
    idx = {"built_at": datetime.datetime.now().isoformat(timespec="seconds"), "root": str(root), "count": len(docs), "documents": docs}
    try: _index_path().parent.mkdir(parents=True, exist_ok=True); _index_path().write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    except Exception: pass
    return idx

def load(rebuild=False):
    p = _index_path()
    if rebuild or not p.exists(): return build()
    try: return json.loads(p.read_text(encoding="utf-8"))
    except ValueError: return build()

def conflicts(idx=None):
    """Two CURRENT documents with the same subject and different content → conflict (surfaced, never resolved by similarity)."""
    idx = idx or load(); by = {}
    for d in idx["documents"]:
        if d["current"] and d["authority"] in ("CURRENT_TRUTH", "WORKING"): by.setdefault(d["subject"], []).append(d)
    return [{"subject": s, "documents": [{"path": x["path"], "sha256": x["sha256"], "version": x["version"], "date": x["date_in_name"], "authority": x["authority"]} for x in v]} for s, v in by.items() if len(v) > 1 and len({x["sha256"] for x in v}) > 1]

def search(query, limit=8, idx=None):
    """Deterministic retrieval: overlap × authority weight; Business Operating Model facts (owners/KPIs/processes) come first when they match."""
    idx = idx or load(); q = tokens(query); hits = []
    for d in idx["documents"]:
        ov = q & set(d["tokens"]); tov = q & tokens(d["title"])
        if not ov: continue
        s = (len(ov) + 2 * len(tov)) * WEIGHT.get(d["authority"], 1.0)
        hits.append({"score": round(s, 2), "path": d["path"], "title": d["title"], "authority": d["authority"], "current": d["current"], "modified": d["modified"], "sections": d["sections"][:6], "matched": sorted(ov)[:8]})
    hits.sort(key=lambda h: (-h["score"], h["path"]))
    bm = []
    try:
        import business
        if business.available():
            for k in business.find_kpis(query, limit=2): bm.append({"kind": "KPI", "id": k["kpi_id"], "name": k["name"], "src": k.get("src")})
            for p in business.find_processes(query, limit=2): bm.append({"kind": "PROCESS", "id": p.get("process_id") or p.get("id"), "name": p.get("name"), "src": p.get("src")})
    except Exception: pass
    paths = {h["path"] for h in hits[:limit]}; conf = [c for c in conflicts(idx) if any(x["path"] in paths for x in c["documents"])]
    return {"query": query, "business_model_first": bm, "hits": hits[:limit], "historical_hits": [h for h in hits if not h["current"]][:3], "conflicts": conf, "index_built_at": idx.get("built_at"), "documents_indexed": idx.get("count")}
