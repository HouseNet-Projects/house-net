# -*- coding: utf-8 -*-
"""Workspace validator — inspects the ACTUAL filesystem against workspace_policy.json and exits non-zero on violations.

  python .claude/policy/validate_workspace.py [--root PATH] [--json] [--quiet]
  python .claude/policy/validate_workspace.py --check-path <path> [--root PATH]     # single target (used by workspace_guard.py)

The policy file itself is validated first (structure + regex compilation); a corrupt policy fails closed.
Unknown top-level entries fail closed. All functions are importable (the guard and tests reuse them — no duplicate rule sets)."""
import sys, os, re, json, pathlib, fnmatch, argparse
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent.parent
POLICY_PATH = HERE / "workspace_policy.json"
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()        # deterministic project interpreter (<root>/.venv)
sys.path.insert(0, str(HERE)); import paths                                                            # ONE business-root resolver (workspace_policy.json -> business_root)

class PolicyError(Exception): pass

# ───────────────────────── policy ─────────────────────────
REQUIRED_TOP = ["policy_version", "business_root", "naming", "reserved_technical_names", "root", "canonical_files", "directories", "generated_exclusions", "semantics", "links", "scope_lock"]

def load_policy(path=POLICY_PATH):
    try: pol = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e: raise PolicyError(f"policy unreadable: {type(e).__name__}: {e}")
    problems = validate_policy(pol)
    if problems: raise PolicyError("policy invalid: " + "; ".join(problems))
    return pol

def validate_policy(pol):
    p = []
    if not isinstance(pol, dict): return ["policy is not an object"]
    for k in REQUIRED_TOP:
        if k not in pol: p.append(f"missing section {k}")
    if p: return p
    for key in ("business_filename_regex", "business_folder_regex", "ordered_top_level_regex", "python_module_regex", "technical_filename_regex", "date_regex", "version_regex"):
        try: re.compile(pol["naming"][key])
        except (KeyError, re.error) as e: p.append(f"naming.{key}: {e}")
    for pat in pol["naming"].get("forbidden_patterns", []):
        try: re.compile(pat)
        except re.error as e: p.append(f"forbidden_pattern {pat!r}: {e}")
    root = pol["root"]
    for k in ("allowed_files", "required_files", "allowed_dirs", "required_dirs"):
        if not isinstance(root.get(k), list): p.append(f"root.{k} must be a list")
    if root.get("unknown_entries") != "fail": p.append("root.unknown_entries must be 'fail' (fail closed)")
    if not set(root.get("required_files", [])) <= set(root.get("allowed_files", [])): p.append("root.required_files not subset of allowed_files")
    if not set(root.get("required_dirs", [])) <= set(root.get("allowed_dirs", [])): p.append("root.required_dirs not subset of allowed_dirs")
    for d in root.get("required_dirs", []):
        if d not in pol["directories"]: p.append(f"required dir {d} has no directory contract")
    p += validate_business_root(pol)
    need = {"kind", "purpose"}
    for name, d in pol["directories"].items():
        if not need <= set(d): p.append(f"directories.{name}: missing {need - set(d)}")
        for sub in d.get("fixed_subdirs", []):
            technical = name.startswith(".claude")
            ok = re.match(pol["naming"]["technical_filename_regex"] if technical else pol["naming"]["business_folder_regex"], sub) or                  (not technical and re.match(pol["naming"]["ordered_top_level_regex"], sub))          # the six ordered business areas
            if not ok and not sub.startswith("."): p.append(f"directories.{name}: fixed_subdir {sub} violates folder naming")
    p += validate_scope_policy(pol)
    return p

def validate_business_root(pol):
    """GEV'S WORKING SURFACE is one folder. When business_root is declared, the business areas and registers must live under it
    and nowhere else: a second home for Tasks.xlsx or 01_Active is exactly how the two roots start to blur."""
    br = pol.get("business_root")
    if br is None: return []                                                   # legacy layout (areas at the repository root)
    br = str(br).strip(); rt = pol["root"]; p = []
    if not br or "/" in br or "\\" in br: return ["business_root must be a single directory name (Gev's working surface)"]
    if br not in rt.get("allowed_dirs", []) or br not in rt.get("required_dirs", []): p.append(f"business_root {br} must be a required top-level directory")
    if br not in pol.get("directories", {}): p.append(f"business_root {br} has no directory contract")
    for f in rt.get("allowed_files", []):
        if f in ("Tasks.xlsx", "Journal.md", "Actions.md"): p.append(f"root.allowed_files still carries the business register {f} - it belongs under {br}/")
    for d in rt.get("allowed_dirs", []):
        if re.match(pol["naming"]["ordered_top_level_regex"], d): p.append(f"root.allowed_dirs still carries the business area {d} - it belongs under {br}/")
    for area in pol.get("directories", {}):
        if re.match(pol["naming"]["ordered_top_level_regex"], area): p.append(f"directories.{area} is not under {br}/ - the business tree has one home")
    return p

SCOPE_REQUIRED = ("law", "default", "owner", "contract_fields", "confirmation", "self_extension", "report_only",
                  "dependency_rule", "implementation_detail", "operations", "default_operations", "subsystems", "enforcement")

def validate_scope_policy(pol):
    """HARD SCOPE LOCK - Deputy changes only what Gev's current instruction requires. Fails CLOSED: a hollowed-out section is a
    violation, because an unenforceable scope rule is the same as no scope rule. (Absence is caught by REQUIRED_TOP.)"""
    sc = pol.get("scope_lock")
    if sc is None: return []
    p = []
    if not isinstance(sc, dict) or not sc: return ["POLICY: scope_lock is empty - Deputy's execution boundary would be unenforceable"]
    for k in SCOPE_REQUIRED:
        if not sc.get(k): p.append(f"POLICY: scope_lock.{k} missing")
    if sc.get("default") != "DENY": p.append("POLICY: scope_lock.default must be 'DENY' (nothing is in scope unless Gev asked for it)")
    if "cannot give itself permission" not in (sc.get("law") or ""): p.append("POLICY: scope_lock.law must keep Deputy from granting itself permission")
    if "FORBIDDEN" not in (sc.get("self_extension") or ""): p.append("POLICY: scope_lock.self_extension must forbid Deputy widening its own scope")
    subs = sc.get("subsystems")
    if not isinstance(subs, dict) or len(subs) < 5: p.append("POLICY: scope_lock.subsystems must name the mutation surfaces")
    else:
        for name, d in subs.items():
            if not isinstance(d, dict) or not d.get("paths") or not d.get("evidence"): p.append(f"POLICY: scope_lock.subsystems.{name} needs paths + evidence")
    enf = sc.get("enforcement") or {}
    for k in ("mutation_gate", "git_gate", "tests"):
        if not enf.get(k): p.append(f"POLICY: scope_lock.enforcement.{k} missing - the rule would rest on memory")
    if not sc.get("enforcement_files"): p.append("POLICY: scope_lock.enforcement_files missing - the machinery would not be a required path")
    if not (sc.get("mirror_files") or {}).get("CLAUDE.md"): p.append("POLICY: scope_lock.mirror_files must make CLAUDE.md state the rule for the agent")
    return p

# ───────────────────────── naming checks (single source of rules) ─────────────────────────
def _rx(pol, key): return re.compile(pol["naming"][key])

def check_business_name(name, pol, is_dir=False):
    """Returns list of violations for a business-facing file/folder name."""
    v = []; n = pol["naming"]
    stem = name if is_dir else name.rsplit(".", 1)[0]
    for pat in n["forbidden_patterns"]:
        if re.search(pat, name): v.append(f"forbidden pattern {pat!r}")
    for w in n["forbidden_words"]:
        if re.search(rf"(^|[-_. ]){re.escape(w)}([-_. ]|$)", stem, re.I): v.append(f"forbidden word '{w}'")
    rx = _rx(pol, "business_folder_regex" if is_dir else "business_filename_regex")
    if not rx.match(name): v.append("does not match business naming (First-word-hyphenated[-vN.N][-YYYY-MM-DD].ext)")
    m = re.search(r"-(\d{4}-\d{2}-\d{2})", stem)
    if m:
        y, mo, d = map(int, m.group(1).split("-"))
        if not (2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31): v.append("invalid date")
        if re.search(r"-\d{4}-\d{2}-\d{2}-v\d", stem): v.append("version must come before date")
    if re.search(r"-v\d+(\.\d+){2,}", stem): v.append("version must be vN or vN.N")
    if not is_dir and "." in name and name.rsplit(".", 1)[1] != name.rsplit(".", 1)[1].lower(): v.append("extension must be lowercase")
    return sorted(set(v))

def check_technical_name(name, pol, python=False):
    if python: return [] if _rx(pol, "python_module_regex").match(name) else ["python module must be lowercase snake_case.py"]
    return [] if _rx(pol, "technical_filename_regex").match(name) else ["technical filename: ASCII letters/digits/._- only"]

def _is_ignored(name, pol):
    g = pol["generated_exclusions"]
    return name in g["ignored_dir_names"] or any(fnmatch.fnmatch(name, pat) for pat in g["ignored_file_globs"])

def _is_garbage(name, pol):
    return any(fnmatch.fnmatch(name.lower(), pat) for pat in pol["generated_exclusions"]["garbage_globs"])

def _rel(root, p): return pathlib.Path(p).resolve().relative_to(pathlib.Path(root).resolve()).as_posix()

def _area(rel, pol=None):
    parts = rel.split("/")
    namespaces = {".claude"} | ({str(pol.get("business_root"))} if pol and pol.get("business_root") else set())
    if parts[0] in namespaces and len(parts) > 1: return parts[0] + "/" + parts[1]
    return parts[0]

BUSINESS_KINDS = ("inbox", "active-work", "reference", "completed", "sources", "archive")

def _areas_by_kind(pol, *kinds):
    """Repository-relative directory keys whose contract declares one of these kinds (policy-driven, never hard-coded names)."""
    return [a for a, d in pol.get("directories", {}).items() if d.get("kind") in kinds]

def _business_parts(rel, pol):
    """(area_key, parts_relative_to_the_business_root) for a business path, else (None, None).
    Works with and without a declared business_root, so the contract itself decides where the business tree lives."""
    parts = rel.split("/"); br = (pol.get("business_root") or "").strip("/")
    if br:
        if parts[0] != br or len(parts) < 2: return None, None
        sub = parts[1:]; area = br + "/" + sub[0]
    else:
        sub = parts; area = sub[0]
    return (area, sub) if pol.get("directories", {}).get(area, {}).get("kind") in BUSINESS_KINDS else (None, None)

def _matches_any(name, patterns): return any(re.search(p, name) for p in patterns)

# ───────────────────────── single-path check (guard + validator share it) ─────────────────────────
def check_path(path, pol, root=DEFAULT_ROOT, is_dir=None):
    """Violations for ONE prospective or existing path inside the workspace. Used by workspace_guard before a write.
    Business rules are dispatched by the CONTRACT KIND of the directory, never by a hard-coded folder name, so the whole
    business tree can live under the business root (WORKSPACE/) without a second rule set."""
    root = pathlib.Path(root).resolve(); p = pathlib.Path(path)
    p = (root / p) if not p.is_absolute() else p
    try: rel = p.resolve().relative_to(root).as_posix()
    except ValueError: return []                                  # outside the workspace: not this policy's business
    parts = rel.split("/"); name = parts[-1]; v = []
    if is_dir is None: is_dir = p.is_dir()
    if _is_ignored(name, pol) and name != "desktop.ini": return []
    if name in pol["reserved_technical_names"]["anywhere_files"]: return []
    if _is_garbage(name, pol): v.append(f"{rel}: generated garbage name")
    top = parts[0]; rt = pol["root"]; br = (pol.get("business_root") or "").strip("/")
    if len(parts) == 1:
        if is_dir:
            if top not in rt["allowed_dirs"]: v.append(f"{rel}: unknown top-level directory (allowed: {rt['allowed_dirs']})")
        elif name not in rt["allowed_files"]: v.append(f"{rel}: unknown top-level file (allowed: {rt['allowed_files']})")
        return v
    if top not in rt["allowed_dirs"]: v.append(f"{rel}: under unknown top-level directory {top}"); return v
    sem = pol["semantics"]
    # semantic placement (repository-relative: the policy states the full canonical prefixes)
    if not is_dir:
        if _matches_any(name, sem["code_markers"]["patterns"]) and rel not in sem["code_markers"].get("root_exceptions", []) and not any(rel.startswith(a + "/") for a in sem["code_markers"]["must_live_under"]):
            v.append(f"{rel}: code may only live under {sem['code_markers']['must_live_under']}")
        if _matches_any(name, sem["runtime_markers"]["patterns"]) and not any(rel.startswith(a + "/") for a in sem["runtime_markers"]["must_live_under"]):
            v.append(f"{rel}: runtime/state file may only live under {sem['runtime_markers']['must_live_under']}")
        if _matches_any(name, sem["test_markers"]["patterns"]) and not any(rel.startswith(a + "/") for a in sem["test_markers"]["must_live_under"]):
            v.append(f"{rel}: tests may only live under {sem['test_markers']['must_live_under']}")
        raw_ok = [sem["source_markers"]["must_live_under"]] + _areas_by_kind(pol, "archive", "inbox")
        if _matches_any(name, sem["source_markers"]["patterns"]) and not any(rel.startswith(a + "/") for a in raw_ok):
            v.append(f"{rel}: raw source/media may only live under {sem['source_markers']['must_live_under']} (or the archive)")
    # ── the business root itself: only the canonical areas and the live registers ──
    if br and top == br and len(parts) == 2:
        wc = pol["directories"].get(br, {})
        if is_dir and name not in wc.get("fixed_subdirs", []): v.append(f"{rel}: only the canonical business areas live in {br}: {wc.get('fixed_subdirs', [])}")
        if not is_dir and name not in wc.get("allowed_files", []): v.append(f"{rel}: only the live registers live directly in {br}: {wc.get('allowed_files', [])}")
        return v
    area, bparts = _business_parts(rel, pol)
    if area:
        return v + _check_business(rel, bparts, name, is_dir, pol, area)
    if top == ".claude":
        a = _area(rel, pol)
        if len(parts) == 2:
            fixed = pol["directories"][".claude"].get("fixed_subdirs", []) + pol["directories"][".claude"].get("optional_subdirs", [])
            if is_dir and name not in fixed and name not in ("__pycache__",): v.append(f"{rel}: unknown .claude subdirectory (allowed {fixed})")
            if not is_dir and name not in pol["directories"][".claude"].get("allowed_files", []): v.append(f"{rel}: unknown file in .claude root (allowed {pol['directories']['.claude'].get('allowed_files')})")
            return v
        sub = pol["directories"].get(a, {})
        if is_dir:
            if sub.get("subdirs") == "forbidden" and name not in sub.get("generated_ok", []): v.append(f"{rel}: subdirectories forbidden in {a}")
            if a == ".claude/skills" and name not in sub.get("allowed_subdirs", []): v.append(f"{rel}: subdirectory not allowed in .claude/skills (allowed {sub.get('allowed_subdirs')})")
            return v
        for g in sub.get("forbidden_globs", []):
            if fnmatch.fnmatch(name, g): v.append(f"{rel}: {g} is forbidden in {a}")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        ae = sub.get("allowed_extensions", "*")
        if ae != "*" and ext not in ae and len(parts) == 3: v.append(f"{rel}: extension .{ext} not allowed in {a}")
        rule = sub.get("naming_rule", "technical")
        if rule == "python_module" and name.endswith(".py"): v += [f"{rel}: {x}" for x in check_technical_name(name, pol, python=True)]
        elif rule == "business" and len(parts) == 3: v += [f"{rel}: {x}" for x in check_business_name(name, pol)]
        elif rule in ("technical", "python_module"):
            if name.endswith(".py"): v += [f"{rel}: {x}" for x in check_technical_name(name, pol, python=True)]
            else: v += [f"{rel}: {x}" for x in check_technical_name(name, pol)]
        return v
    return v

def _check_business(rel, parts, name, is_dir, pol, area):
    """Rules for ONE path inside the business tree. `parts` is relative to the business root, `area` is its repository-relative
    directory key. Dispatch is by contract KIND: inbox · active-work/reference · sources · completed/archive."""
    dc = pol["directories"].get(area, {}); kind = dc.get("kind", ""); sem = pol["semantics"]; v = []
    short = area.split("/")[-1]
    if kind == "inbox":
        if is_dir: v.append(f"{rel}: subdirectories are forbidden in {short}")
        return v
    if kind in ("active-work", "reference", "sources"):
        fixed = dc.get("fixed_subdirs", [])
        if len(parts) == 2 and is_dir and name not in fixed: v.append(f"{rel}: only fixed subdomains allowed in {short}: {fixed}")
        if len(parts) == 2 and not is_dir: v.append(f"{rel}: files must live inside a subdomain of {short} {fixed}")
        if len(parts) >= 3 and parts[1] not in fixed: v.append(f"{rel}: unknown subdomain {parts[1]} (allowed {fixed})")
        if kind == "sources":
            if len(parts) == 3 and is_dir and not re.match(dc["source_naming"]["folder_regex"], name): v.append(f"{rel}: source folder must be Name-YYYY-MM-DD[-suffix]")
            if not is_dir and not (_rx(pol, "technical_filename_regex").match(name) or not check_business_name(name, pol)): v.append(f"{rel}: source file name must be technical (no spaces/parentheses) or business form")
            if not is_dir and (_matches_any(name, sem["code_markers"]["patterns"]) or _matches_any(name, sem["runtime_markers"]["patterns"])): v.append(f"{rel}: runtime code inside {short}")
            return v
        if len(parts) >= 3:
            if is_dir: v.append(f"{rel}: arbitrary subdirectories are forbidden in {short}")
            else:
                v += [f"{rel}: {x}" for x in check_business_name(name, pol)]
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if dc.get("allowed_extensions") != "*" and ext not in dc.get("allowed_extensions", []): v.append(f"{rel}: extension .{ext} not allowed in {short}")
        return v
    if kind in ("completed", "archive"):
        # sealed historical packages keep their ORIGINAL names: an archive is evidence, and renaming it destroys provenance
        if kind == "archive" and len(parts) >= 2 and parts[1] in dc.get("verbatim_subdirs", []): return v
        if is_dir: v += [f"{rel}: {x}" for x in check_business_name(name, pol, is_dir=True)]
        else:
            ok_business = not check_business_name(name, pol)
            ok_tech = kind == "archive" and not check_technical_name(name, pol) and not re.search(r"\s|[()]", name)
            if not (ok_business or ok_tech): v += [f"{rel}: {x}" for x in check_business_name(name, pol)]
            if kind == "completed":
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if ext not in dc.get("allowed_extensions", []): v.append(f"{rel}: extension .{ext} not allowed in {short}")
        return v
    return v

# ───────────────────────── whole-tree validation ─────────────────────────
def validate_tree(root=DEFAULT_ROOT, pol=None, policy_path=POLICY_PATH):
    root = pathlib.Path(root).resolve(); problems = []
    try: pol = pol or load_policy(policy_path)
    except PolicyError as e: return [f"POLICY: {e}"]
    rt = pol["root"]
    entries = list(root.iterdir())
    names = {e.name for e in entries}
    for f in rt["required_files"]:
        if f not in names: problems.append(f"missing required root file {f}")
    for d in rt["required_dirs"]:
        if not (root / d).is_dir(): problems.append(f"missing required root directory {d}")
    for area, dc in pol["directories"].items():
        base = root / area
        if dc.get("required") and not base.is_dir(): problems.append(f"missing required directory {area}"); continue
        if not base.is_dir(): continue
        for sub in dc.get("fixed_subdirs", []):
            if not (base / sub).is_dir(): problems.append(f"missing fixed subdirectory {area}/{sub}")
        for rf in dc.get("required_files", []):
            if not (base / rf).exists(): problems.append(f"missing required file {area}/{rf}")
    for cf, spec in pol["canonical_files"].items():
        if not (root / cf).exists() and (spec.get("single_canonical") or cf in rt["required_files"]): problems.append(f"missing canonical file {cf}")
    # walk
    for dirpath, dirnames, filenames in os.walk(root):
        dp = pathlib.Path(dirpath); rel_dir = _rel(root, dp) if dp != root else ""
        dirnames[:] = [d for d in dirnames if d not in pol["generated_exclusions"]["ignored_dir_names"] or d == "__pycache__"]
        for d in list(dirnames):
            rel = f"{rel_dir}/{d}" if rel_dir else d
            if d == "__pycache__":
                if not any(rel_dir == a for a in pol["generated_exclusions"]["pycache_allowed_under"]): problems.append(f"{rel}: __pycache__ outside allowed runtime directories")
                dirnames.remove(d); continue
            problems += check_path(dp / d, pol, root, is_dir=True)
        for f in filenames:
            rel = f"{rel_dir}/{f}" if rel_dir else f
            if _is_ignored(f, pol) and f != "desktop.ini": continue
            problems += check_path(dp / f, pol, root, is_dir=False)
    # inbox invariant (the inbox is whichever area the contract declares, wherever the business root puts it)
    for area in _areas_by_kind(pol, "inbox"):
        inbox = root / area
        if not inbox.is_dir(): continue
        keep = {pathlib.Path(cf).name for cf, sp in pol["canonical_files"].items() if cf.startswith(area + "/")} or {"Input.md"}
        extra = [e.name for e in inbox.iterdir() if e.name not in keep and not _is_ignored(e.name, pol)]
        if extra: problems.append(f"{area} not in steady state: unclassified items {extra}")
    # single canonical artifacts
    for cf, spec in pol["canonical_files"].items():
        if not spec.get("single_canonical"): continue
        base = pathlib.Path(cf).name
        for g in spec.get("duplicates_forbidden_globs", []) + [f"**/{base}"]:
            for hit in root.glob(g):
                if hit.is_dir(): continue
                rel = _rel(root, hit)
                if rel == cf: continue
                if any(rel.startswith(a + "/") for a in spec.get("duplicates_allowed_under", [])): continue
                if any(part in pol["generated_exclusions"]["ignored_dir_names"] for part in rel.split("/")): continue
                problems.append(f"duplicate canonical artifact for {cf}: {rel}")
    # reference vs completed: same base document in both
    anywhere = set(pol["reserved_technical_names"].get("anywhere_files", []))          # .gitkeep placeholders are not documents
    def _names(areas):
        out = {}
        for a in areas:
            base = root / a
            if base.is_dir(): out.update({p.name: a for p in base.rglob("*") if p.is_file() and p.name not in anywhere})
        return out
    ref, comp = _names(_areas_by_kind(pol, "reference")), _names(_areas_by_kind(pol, "completed"))
    for n in sorted(ref.keys() & comp.keys()): problems.append(f"{n}: exists in both {ref[n]} and {comp[n]} (one canonical location)")
    # markdown links
    for md in pol["links"]["check_markdown_links_in"]:
        p = root / md
        if not p.exists(): continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", txt):
            target = m.group(1)
            if re.match(r"^[a-z]+:", target): continue
            t = (p.parent / target)
            if not t.exists(): problems.append(f"{md}: broken link → {target}")
    # README ↔ policy consistency (structure block)
    readme = root / "README.md"
    if readme.exists():
        txt = readme.read_text(encoding="utf-8", errors="replace")
        for d in rt["required_dirs"]:
            if d not in txt: problems.append(f"README.md does not mention required directory {d}")
        for f in rt["required_files"]:
            if f not in txt: problems.append(f"README.md does not mention required file {f}")
        br = (pol.get("business_root") or "").strip("/")
        for sub in (pol["directories"].get(br, {}).get("fixed_subdirs", []) if br else []):
            if sub not in txt: problems.append(f"README.md does not mention the business area {br}/{sub}")
        for reg in (pol["directories"].get(br, {}).get("allowed_files", []) if br else []):
            if reg not in txt: problems.append(f"README.md does not mention the live register {br}/{reg}")
    problems += check_scope(root, pol)
    problems += check_identity(root, pol)
    problems += check_interaction(root, pol)
    problems += check_boundary(root)
    problems += check_tree_manifest(root, pol)
    return sorted(set(problems))

def check_tree_manifest(root, pol):
    """Canonical tree manifest (derived from this policy) must be current and every required path must physically exist."""
    try:
        import tree_manifest as tm
    except ImportError: return ["tree_manifest.py unavailable"]
    problems = []
    try:
        problems += tm.check_manifest(pathlib.Path(root) / ".claude" / "policy" / "workspace_tree_manifest.json", pol)
        miss = tm.verify(root, tm.build(pol))
        problems += [f"required canonical path missing: {m} (documentation is not enough — it must exist)" for m in miss]
    except Exception as e: problems.append(f"tree manifest check failed: {type(e).__name__}: {e}")
    return problems

def check_scope(root, pol):
    """HARD SCOPE LOCK — the rule is only real if the machinery exists: the scope engine, the tests, and the statement in
    CLAUDE.md. Missing machinery is a violation, because a scope rule that rests on the agent remembering it is not a rule."""
    sc = pol.get("scope_lock")
    if sc is None: return []
    root = pathlib.Path(root); problems = []
    for m in sc.get("enforcement_files", []):
        if not (root / m).exists(): problems.append(f"scope_lock names the enforcement file {m}, which does not exist")
    for rel, needles in (sc.get("mirror_files") or {}).items():
        f = root / rel
        if not f.exists(): problems.append(f"{rel}: scope-lock mirror file missing"); continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        for need in needles:
            if need not in txt: problems.append(f"{rel}: must state the HARD SCOPE LOCK ({need!r})")
    return problems

def check_boundary(root):
    """Sensitive-data boundary: versionable business-model core carries no CONFIDENTIAL/RESTRICTED content; the git index tracks
    no CONFIDENTIAL/RESTRICTED path; pre-commit/pre-push boundary hooks are installed (data_classification.json + sensitive_scan.py)."""
    problems = []
    try:
        import sensitive_scan as ss
    except ImportError: return ["sensitive_scan.py unavailable — boundary unchecked (fail closed)"]
    try:
        pol = ss.load_policy(); root = pathlib.Path(root)
        core = sorted((root / ".claude" / "business").glob("bm_*.py")) + [p for p in ((root / ".claude" / "business" / "build_business_model.py"), (root / ".claude" / "business" / "certify_business.py"), (root / ".claude" / "skills" / "business.py")) if p.exists()]
        bc = ss.blocking_classes(pol)
        for rel, fs in ss.scan_paths(core, root=root, pol=pol, names=ss.overlay_names(root / ".claude" / "business" / "overlay.json")).items():
            for f in fs:
                if f["class"] in bc: problems.append(f"{rel}: RESTRICTED content in the versionable core ({f['rule']})")
                elif f["rule"] == "person_name_from_overlay": problems.append(f"{rel}: person name in the CORE (people live in the overlay as @P tokens)")
        if (root / ".git").is_dir():
            import subprocess
            out = subprocess.run(["git", "ls-files"], cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.split()
            for rel in out:
                cls, why = ss.classify_path(rel, pol)
                if cls in bc: problems.append(f"{rel}: tracked by git but classified {cls} ({why}) — credentials never in plaintext")
            if not ss.hooks_installed(root): problems.append("git boundary hooks missing — python .claude/policy/sensitive_scan.py --install-hooks")
    except Exception as e: problems.append(f"boundary check failed: {type(e).__name__}: {e}")
    return problems

def check_interaction(root, pol):
    """INTERACTION CONTRACT (workspace_policy.json -> interaction): Deputy speaks to the owner in Eastern Armenian and presents
    people in human-readable form. Fails CLOSED: a missing or hollowed-out block is a violation, never a silent pass."""
    root = pathlib.Path(root); problems = []
    ix = pol.get("interaction")
    if not isinstance(ix, dict) or not ix: return ["POLICY: interaction section missing - the user-facing language contract is the policy's job"]
    enf = ix.get("enforcement")
    if not isinstance(enf, dict) or not enf: return ["POLICY: interaction.enforcement missing - the language contract would not be checkable"]
    if ix.get("user_language") != "hy-AM": problems.append("POLICY: interaction.user_language must be 'hy-AM' (Eastern Armenian)")
    for k in enf.get("required_keys", []):
        if not ix.get(k): problems.append(f"POLICY: interaction.{k} missing")
    hri = ix.get("human_readable_identity") or {}
    if not isinstance(hri, dict) or not hri: problems.append("POLICY: interaction.human_readable_identity missing")
    else:
        for k in enf.get("required_identity_keys", []):
            if not hri.get(k): problems.append(f"POLICY: interaction.human_readable_identity.{k} missing")
        # the presentation rule must never be allowed to become an identity-confirmation rule
        if "NOT confirmed identity" not in (hri.get("safety") or ""):
            problems.append("POLICY: interaction.human_readable_identity.safety must keep display name/username OUT of confirmed identity")
        # a human-readable LABEL is enough for ordinary work: an absent mapping must never become a question to the owner
        ops = hri.get("confirmation_required_only_for")
        if not isinstance(ops, dict) or not ops:
            problems.append("POLICY: interaction.human_readable_identity.confirmation_required_only_for must name the operations that truly need a confirmed identity")
        if "NOT a blocker" not in (hri.get("never_block") or ""):
            problems.append("POLICY: interaction.human_readable_identity.never_block must keep a missing identity mapping from becoming a blocker")
    for rel, needles in (enf.get("mirror_files") or {}).items():
        f = root / rel
        if not f.exists(): problems.append(f"{rel}: interaction mirror file missing"); continue
        try: txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError: continue
        for need in needles:
            if need not in txt: problems.append(f"{rel}: must state the interaction contract ({need!r})")
    return problems

def check_identity(root, pol):
    """Identity/configuration drift: active files must agree on workspace + agent names; stale canonical names fail."""
    root = pathlib.Path(root); problems = []
    ident = pol.get("identity"); enf = pol.get("identity_enforcement")
    if not ident or not enf: return ["POLICY: identity / identity_enforcement sections missing"]
    for k in ("name", "role", "workspace", "owner"):
        if not ident.get(k): problems.append(f"POLICY: identity.{k} missing")
    if ident.get("workspace") != pol.get("workspace_name"): problems.append("POLICY: identity.workspace disagrees with workspace_name")
    markers = re.compile("|".join(re.escape(m) for m in enf["historical_line_markers"]), re.I)
    stale = [(p, re.compile(re.escape(p))) for p in enf["stale_patterns"]]
    for rel in enf["active_files"]:
        p = root / rel
        if not p.exists(): continue
        try: txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError: continue
        for need in enf.get("must_mention", {}).get(rel, []):
            if need not in txt: problems.append(f"{rel}: must mention canonical identity {need!r}")
        for i, line in enumerate(txt.splitlines(), 1):
            if markers.search(line): continue
            if rel == ".claude/policy/validate_workspace.py" or rel.endswith("workspace_policy.json"): continue
            for pat, rx in stale:
                if rx.search(line): problems.append(f"{rel}:{i}: stale canonical reference {pat!r} (add a historical marker or update)")
    # settings.json hooks must point at existing scripts
    settings = root / ".claude" / "settings.json"
    if settings.exists():
        try:
            cfg = json.loads(settings.read_text(encoding="utf-8"))
            for ev, groups in cfg.get("hooks", {}).items():
                for g in groups:
                    for h in g.get("hooks", []):
                        cmd = h.get("command", "")
                        for ref in re.findall(r"\.claude/[\w/.-]+\.(?:py|sh)", cmd):
                            if not (root / ref).exists(): problems.append(f"settings.json: {ev} hook references missing script {ref}")
                        if ".claude/runtime/hook.sh" not in cmd: problems.append(f"settings.json: {ev} hook must run through .claude/runtime/hook.sh (project interpreter, not PATH python)")
                        for name in re.findall(r"hook\.sh\"?\s+([\w.-]+\.py)", cmd):
                            if not (root / ".claude" / "hooks" / name).exists(): problems.append(f"settings.json: {ev} hook references missing script .claude/hooks/{name}")
        except json.JSONDecodeError: problems.append("settings.json: invalid JSON")
    return problems

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=str(DEFAULT_ROOT)); ap.add_argument("--policy", default=str(POLICY_PATH))
    ap.add_argument("--check-path"); ap.add_argument("--json", action="store_true"); ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    try: pol = load_policy(a.policy)
    except PolicyError as e:
        print(json.dumps({"ok": False, "problems": [str(e)]}) if a.json else f"✗ {e}"); return 2
    if a.check_path:
        probs = check_path(a.check_path, pol, a.root)
    else:
        probs = validate_tree(a.root, pol, a.policy)
    if a.json: print(json.dumps({"ok": not probs, "problems": probs}, ensure_ascii=False))
    elif not a.quiet:
        print(f"workspace: {a.root}\npolicy {pol['policy_version']} · {'OK — contract satisfied' if not probs else str(len(probs)) + ' violation(s)'}")
        for p in probs: print("  ✗", p)
    return 0 if not probs else 1

if __name__ == "__main__":
    sys.exit(main())
